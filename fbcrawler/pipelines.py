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
        if not isinstance(item, CommentItem):
            item.setdefault('shares', 0)
            item.setdefault('likes', 0)
            item.setdefault('reactions', 0)
            item.setdefault('comments', 0)
            item.setdefault('wow', 0)
            item.setdefault('grrr', 0)
            item.setdefault('love', 0)
            item.setdefault('ahah', 0)
            item.setdefault('sigh', 0)
            # if item['date'] < datetime(2017, 1, 1).date():
            #     raise DropItem("Dropping element because it's older than 01/01/2017")
            # elif item['date'] > datetime(2018, 3, 4).date():
            #     raise DropItem("Dropping element because it's newer than 04/03/2018")
        else:
            pass

        return item
