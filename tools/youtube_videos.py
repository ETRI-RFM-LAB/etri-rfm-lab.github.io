#!/usr/bin/env python3
"""Refresh data/videos.json with the lab's videos from the ETRI_HROS YouTube channel.

The channel RSS feed only lists the latest 15 uploads, so videos already in
data/videos.json are kept and new ones are merged in. Only titles tagged
"[RFM]" belong to this lab; the tag is stripped for display.
"""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

CHANNEL_ID = 'UCyr9KjwK-02c5cT6PS4rbFg'
FEED = f'https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'videos.json')
TAG = re.compile(r'^\s*\[RFM\]\s*', re.I)
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}


def main():
    request = urllib.request.Request(FEED, headers={'User-Agent': 'etri-rfm-lab-site'})
    root = ET.fromstring(urllib.request.urlopen(request, timeout=30).read())
    try:
        with open(OUT, encoding='utf-8') as file:
            videos = {video['id']: video for video in json.load(file)['videos']}
    except (FileNotFoundError, ValueError, KeyError):
        videos = {}
    for entry in root.findall('a:entry', NS):
        title = entry.findtext('a:title', '', NS)
        if not TAG.match(title):
            continue
        video_id = entry.findtext('yt:videoId', '', NS)
        videos[video_id] = {'id': video_id, 'title': TAG.sub('', title).strip(), 'published': entry.findtext('a:published', '', NS)[:10]}
    ordered = sorted(videos.values(), key=lambda video: video['published'], reverse=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as file:
        json.dump({'channel': CHANNEL_ID, 'videos': ordered}, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print(f'{len(ordered)} videos')


if __name__ == '__main__':
    main()
