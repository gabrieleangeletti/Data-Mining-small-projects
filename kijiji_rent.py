from __future__ import print_function

import sys
import time
import requests
import json

from bs4 import BeautifulSoup

def clean_html(html):
    # remove newlines and tabs in the html
    return html.replace('\n', '').replace('\t', '')

def collect_data(content):
    title =     (lambda x: x.encode('utf-8') if x else 'no-title')    (content.find(class_='title').text)
    desc =      (lambda x: x.encode('utf-8') if x else 'no-desc')     (content.find(class_='description').text)
    location =  (lambda x: x.encode('utf-8') if x else 'no-location') (content.find(class_='locale').text)
    price =     (lambda x: x.encode('utf-8') if x else 'no-price')    (content.find(class_='price').text[:-2])
    timestamp = (lambda x: x.encode('utf-8') if x else 'no-timestamp')(content.find(class_='timestamp').text)
    return title, desc, location, price, timestamp

def is_float(x):
    try:
        float(x)
        return True
    except ValueError:
        return False

if __name__ == '__main__':

    # collect data
    if sys.argv[1] == 'collect':
        base_url = 'http://www.kijiji.it/case/affitto/roma-annunci-roma/?entryPoint=sb'
        if len(sys.argv) > 2:
            outfile = sys.argv[2]
        else:
            # default value
            outfile = 'kijiji_data_{}.txt'.format(time.ctime()[4:7] + '_' + time.ctime()[8:10] + '_' + time.ctime()[-4:])

        top_ads = {}  # Dictionary containing the top ads, used to avoiding duplicates
        page_count = 2
        posts_count = 0
        with open(outfile, 'a') as o:
            # get the first page
            resp = requests.get(base_url)
            html = clean_html(resp.text)
            while page_count == 2 or 'p=' in resp.url:
                soup = BeautifulSoup(html, 'html.parser', from_encoding=resp.encoding)
                # top posts
                top_posts = soup.find_all(class_='item topad result')
                for top_post in top_posts:
                    top_content = top_post.find(class_='item-content')
                    title, desc, location, price, timestamp = collect_data(top_content)
                    # replace dot in the price
                    price = price.replace('.', '')
                    url = top_post.find('a')['href']
                    # append to file only if there is a price on the post
                    if price != 'no-price' and not top_ads.has_key(top_post.find('a')['name']):
                        o.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(title, desc, location, price, timestamp, url))
                        posts_count += 1
                    # the id of the ad is used to avoid duplicates
                    top_ads[top_post.find('a')['name']] = True
                # standard posts
                posts = soup.find_all(class_='item result')
                for post in posts:
                    content = post.find(class_='item-content')
                    title, desc, location, price, timestamp = collect_data(content)
                    # replace dot in the price
                    price = price.replace('.', '')
                    url = post.find('a')['href']
                    # append to file only if there is a price on the post, and if the post is not a duplicate of a top post
                    if price != 'no-price' and not top_ads.has_key(post['id'].split('-')[1]):
                        o.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(title, desc, location, price, timestamp, url))
                        posts_count += 1
                # go to the next page
                resp = requests.get('http://www.kijiji.it/case/affitto/roma-annunci-roma/?p={}&entryPoint=sb'.format(page_count))
                html = clean_html(resp.text)
                page_count += 1
                # every 10 calls to the site wait few seconds to avoid being blocked
                if page_count % 10 == 0:
                    print('{} pages saved ({} posts)...'.format(page_count, posts_count))
                    time.sleep(3)
    # analyze data
    elif sys.argv[1] == 'analyze':
        if len(sys.argv) > 2:
            infile = sys.argv[2]
            outfile = sys.argv[3]
        else:
            # default value
            infile = 'kijiji_data_{}.txt'.format(time.ctime()[4:7] + '_' + time.ctime()[8:10] + '_' + time.ctime()[-4:])
            outfile = 'kijiji_analysis_{}.json'.format(time.ctime()[4:7] + '_' + time.ctime()[8:10] + '_' + time.ctime()[-4:])

        print('Analysis started...')
        locations_avg_price = {}
        locations_num_posts = {}
        with open(infile, 'r') as i:
            for line in i:
                apartment = line.split('\t')
                location, price = apartment[2], apartment[3]

                if is_float(price):
                    if locations_avg_price.has_key(location):
                        locations_avg_price[location] += float(price)
                        locations_num_posts[location] += 1
                    else:
                        locations_avg_price[location] = float(price)
                        locations_num_posts[location] = 1

        for location in locations_avg_price:
            locations_avg_price[location] /= float(locations_num_posts[location])

        print('Saving results to outfile...')
        with open(outfile, 'w') as o:
            o.write(json.dumps({'average_price_per_location': locations_avg_price,
                                'number_posts_per_location': locations_num_posts}))
