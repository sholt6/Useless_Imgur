#!/usr/bin/python3
# A script which scrapes the top 5 imgur posts and posts them to Twitter

import bs4
import requests
import tweepy as tp
import datetime as dt
import re
from PIL import Image
import configparser

def twitter_login():
    # Login and return api variable for future use
    config = configparser.ConfigParser()
    config.read('config.ini')

    consumer_key = config['Twitter Access']['consumer_key']
    consumer_secret = config['Twitter Access']['consumer_secret']
    access_token = config['Twitter Access']['access_token']
    access_secret = config['Twitter Access']['access_secret']

    auth = tp.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)
    api = tp.API(auth)

    return api

def posted_today(api):
    # Check date of last post
    statuses = api.user_timeline('useless_imgur')

    current_date = dt.datetime.now().date()
    tweet_date = statuses[0].created_at.date()

    return (current_date == tweet_date)

def get_posts():
    # Get list of all post urls
    res = requests.get('https://imgur.com')
    res.raise_for_status()

    soup = bs4.BeautifulSoup(res.text, 'lxml')

    post_tags = soup.select('.post a')

    url_list = []

    for tag in post_tags:
        post_ID = tag.get('href')
        post_url = ('https://imgur.com' + post_ID)
        url_list.append(post_url)

    return url_list

def img_too_big(filename):
    # Check the size of a file is suitable for Twitter posting
    with Image.open(filename) as image:
        x = image.size[0]
        y = image.size[1]

    if ((x < 4) | (y < 4) | (x > 8192) | (y > 8192)):
        return True
    else:
        return False

def get_content(url, i):
    # Get content of posts
    res = requests.get(url)
    soup = bs4.BeautifulSoup(res.text, 'lxml')
    
    type_check = soup.find_all(attrs={'itemtype':
                                      'http://schema.org/ImageObject'})

    # If <1 post is gif, if >1 post is album
    if (len(type_check) != 1):
        return False

    title = soup.select('.post-title')
    title = title[0].text

    img = soup.select('.post-image img')
    address = 'https:' + img[0].get('src')

    source = requests.get(address)
    extension = ''

    if (re.search('\.jpg', address)):
        extension = '.jpg'
    elif (re.search('\.png', address)):
        extension = '.png'
    else:
        print("ERROR: an unknown image type has been encountered")
        quit()

    filename = 'pic' + str(i) + extension

    with (open(filename, 'wb')) as file:
        file.write(source.content)

    if (img_too_big(filename)):
        return False

    return (title, url, filename)    

def twitter_post(i, content, api):
    num = str(i + 1)
    title = content[0]
    url = content[1]
    filename = content[2]
    date = str(dt.datetime.now().date())

    message = ("No. " + num + " post on imgur " + date + ": "
               + url + "\n\"" + title + "\"")

    if (len(message) > 280):
        message = message[0:276] + "...\""

    pic_post = api.media_upload(filename)
    api.update_status(status=message, media_ids = [pic_post.media_id_string])


def __main__():
    # Set Twitter login info
    api = twitter_login()

    # Check no posts have been made today
    print("Checking no post has been made today")
    if posted_today(api):
        print("Useless_imgur has already posted today: quitting")
        quit()
        print("You left the quit() command commented out you idiot")
    else:
        print("No post made today, proceeding")

    # Collect URLs of all posts on imgur front page
    print("Scraping top 5 images from imgur.com")
    url_list = get_posts()

    # Collect content for top 5 non-gif, non-multi-image posts
    i = 0
    content_lists = []

    while (i < 5):
        try:
            content = get_content(url_list[i], (i+1))
        except IndexError as err:
            print("Insufficient single-image posts on front page")
            print("This should never have happened")
            break

        if (content):
            content_lists.append(content)
            i += 1
        else:
            print("Unusable post encountered, skipping")
            url_list.pop(i)

    # Post images to Twitter with message
    for i in range(0, len(content_lists)):
        twitter_post(i, content_lists[i], api)

if (__name__ == '__main__'):
    __main__()
