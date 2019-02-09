# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import re
import json

from datetime import datetime

from scrapy.exceptions import DropItem, CloseSpider
from fbcrawler.fbcrawler.items import CommentItem, PostItem
from app import sess, vocab, predictions, input_x, dropout
from serve import predict_one_sentence_v2


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
            if (len(item['comment_items']) >= item['comments'])\
                and item['reactions'] == sum([item['likes'],
                                              item['love'],
                                              item['grrr'],
                                              item['ahah'],
                                              item['wow'],
                                              item['sigh']]):
                if spider.post_count < spider.post_limit:
                    item['date'] = str(item['date'])
                    spider.post_count += 1
                    for i in item['comment_items']:
                        i['is_positive'] = predict_one_sentence_v2(sess, vocab, predictions, input_x, dropout, i)
                        if i.get('replies'):
                            for rep in i['replies']:
                                rep['is_positive'] = predict_one_sentence_v2(sess, vocab, predictions,
                                                                             input_x, dropout, rep)
                    return item
                else:
                    spider.crawler.engine.close_spider(self, reason=f'limit {spider.post_count} posts exceeded!')
            else:
                print(f'DEBUG POST {item["comments"]}, {len(item["comment_items"])}, {item["reactions"]}')
                raise DropItem(
                    f'Dropping this post, get {len(item["comment_items"])} already, wait for crawling comments and reaction complete....')
        else:
            raise DropItem('Ignore CommentItem: comments and replies')
