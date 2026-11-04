#!/usr/bin/env python3
"""Refresh data/videos.json with the lab's videos from the ETRI_HROS YouTube channel.

The feed often answers 404 or 500 at random, so the request is retried.
Runs from cron on the lab PC (YouTube refuses the feed from GitHub Actions)
and commits and pushes data/videos.json when the list changes.
The channel RSS feed only lists the latest 15 uploads, so videos already in
data/videos.json are kept and new ones are merged in. Only titles tagged
"[RFM]" belong to this lab; the tag is stripped for display.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

CHANNEL_ID = 'UCyr9KjwK-02c5cT6PS4rbFg'
FEED = f'https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}'
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(REPO, 'data', 'videos.json')
# Videos left off the home page on purpose.
EXCLUDE = {'vBFTPuRpU1E'}  # Learning from Oblivion (shown on the Research page)
TAG = re.compile(r'^\s*\[RFM\]\s*', re.I)
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}


def git(*args, check=True):
    return subprocess.run(['git', '-C', REPO, *args], check=check, capture_output=True, text=True)


def fetch_feed(attempts=10):
    request = urllib.request.Request(FEED, headers={'User-Agent': 'etri-rfm-lab-site'})
    for attempt in range(attempts):
        try:
            return urllib.request.urlopen(request, timeout=30).read()
        except urllib.error.HTTPError as error:
            if attempt == attempts - 1:
                raise
            print(f'feed returned {error.code}, retrying')
            time.sleep(5)


def main():
    push = '--no-push' not in sys.argv
    if push:
        git('pull', '--ff-only', '--quiet', check=False)
    root = ET.fromstring(fetch_feed())
    try:
        with open(OUT, encoding='utf-8') as file:
            videos = {video['id']: video for video in json.load(file)['videos'] if video['id'] not in EXCLUDE}
    except (FileNotFoundError, ValueError, KeyError):
        videos = {}
    for entry in root.findall('a:entry', NS):
        title = entry.findtext('a:title', '', NS)
        if not TAG.match(title) or entry.findtext('yt:videoId', '', NS) in EXCLUDE:
            continue
        video_id = entry.findtext('yt:videoId', '', NS)
        videos[video_id] = {'id': video_id, 'title': TAG.sub('', title).strip(), 'published': entry.findtext('a:published', '', NS)[:10]}
    ordered = sorted(videos.values(), key=lambda video: video['published'], reverse=True)
    text = json.dumps({'channel': CHANNEL_ID, 'videos': ordered}, ensure_ascii=False, indent=2) + '\n'
    try:
        with open(OUT, encoding='utf-8') as file:
            if file.read() == text:
                print(f'{len(ordered)} videos, no change')
                return
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as file:
        file.write(text)
    print(f'{len(ordered)} videos, list updated')
    if push:
        git('add', OUT)
        git('commit', '--quiet', '-m', 'Update YouTube video list', '--', OUT)
        print(git('push', '--quiet', check=False).stderr.strip() or 'pushed')


if __name__ == '__main__':
    main()
