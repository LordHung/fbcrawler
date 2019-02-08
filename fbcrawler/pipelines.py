# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import re

from datetime import datetime

from scrapy.exceptions import DropItem
from fbcrawler.items import CommentItem, PostItem


class FbcrawlerPipeline(object):
    def process_item(self, item, spider):
        if isinstance(item, PostItem):
            item.setdefault('shares', 0)
            item.setdefault('likes', 0)
            item.setdefault('reactions', 0)
            item.setdefault('comments', 0)
            item.setdefault('comment_items', [])
            item.setdefault('wow', 0)
            item.setdefault('grrr', 0)
            item.setdefault('love', 0)
            item.setdefault('ahah', 0)
            item.setdefault('sigh', 0)
            # @TODO: some posts missing just only 1 cmt, need to fix
            # if (item['comments'] == len(item['comment_items']) or item['comments'] - 1 == len(item['comment_items']))\
            if (len(item['comment_items']) >= item['comments'])\
                and item['reactions'] == sum([item['likes'],
                                              item['love'],
                                              item['grrr'],
                                              item['ahah'],
                                              item['wow'],
                                              item['sigh']]):
                if spider.post_count < spider.post_limit:
                    spider.post_count += 1
                    return item
                else:
                    spider.crawler.engine.close_spider(self, reason=f'limit {spider.post_count} posts exceeded!')
            else:
                print(f'DEBUG POST {item["comments"]}, {len(item["comment_items"])}, {item["reactions"]}')
                raise DropItem(
                    f'Dropping this post, get {len(item["comment_items"])} already, wait for crawling comments and reaction complete....')
        else:
            raise DropItem('Ignore CommentItem: comments and replies')
