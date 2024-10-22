# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
import re

from scrapy.loader.processors import TakeFirst, Join, MapCompose
from datetime import datetime, timedelta


def parse_date(date):
    months = dict(
        january=1,
        february=2,
        march=3,
        april=4,
        may=5,
        june=6,
        july=7,
        august=8,
        september=9,
        october=10,
        november=11,
        december=12
    )

    months_short = dict(
        jan=1,
        feb=2,
        mar=3,
        apr=4,
        may=5,
        jun=6,
        jul=7,
        aug=8,
        sep=9,
        oct=10,
        nov=11,
        dec=12
    )

    days = dict(
        sunday=0,
        saturday=1,
        monday=2,
        tuesday=3,
        wednesday=4,
        thursday=5,
        friday=6
    )

    date = date[0].split()
    year, month, day = [int(i) for i in str(datetime.now().date()).split(sep='-')]  # default is today

    # things to match:
    #Yesterday at 2:10
    #Now
    #5 hrs/ 5 hr
    #3 mins
    #just now
    #21 dec
    #29 may at 13:21
    #12 july 2018
    #17 december at 17:31
    #21 december 2011 at 17:31
    #Monday at 10:01

    #sanity check
    date = [i.lower() for i in date if i]
    try:
        if len(date) == 0:
            return 'Error: no data'

        #no check for today
        #elif len(date) == 1 or date[1] == 'h':
            #pass

        #yesterday
        elif date[0] == 'yesterday':
            day = int(str(datetime.now().date() - timedelta(days=1)).split(sep='-')[2])
        elif date[1] in ['hrs', 'hr', 'mins', 'min', 'secs', 'sec', 'now']:
            day = int(str(datetime.now().date() - timedelta(days=1)).split(sep='-')[2])

        #day with 3 month length of this year
        elif (len(date) == 2 and len(date[1]) == 3) or (len(date) == 4 and len(date[1]) == 3):
            day = int(date[0])
            month = months_short[date[1]]

        #day of this year
        elif date[0].isdigit() and date[2] == 'at':
            day = int(date[0])
            month = months[date[1]]

        #usual dates, with regular length month
        elif date[0].isdigit() and date[2].isdigit():
            day = int(date[0])
            month = months[date[1]]
            year = int(date[2])

        #dates with weekdays (this function assumes that the month is the same)
        elif not date[0].isdigit() and not date[1].isdigit():
            today = datetime.now().weekday()  # today as a weekday
            weekday = days[date[0]]  # day to be match as number weekday
            #weekday is chronologically always lower than day
            if weekday < today:
                day -= today - weekday
            elif weekday > today:
                weekday += 7
                day -= today - weekday
        elif len(date) == 5:  # 21 december 2011 at 17:31
            day = int(date[1])
            month = months[date[0]]
            # hour = date[4]
            # minute = date
        else:
            #date item parser fail. datetime format unknown, check xpath selector or change the language of the interface'
            # return f'Error date:{date}'
            return f'{date}'
    except:
        return f'{date}'
    print(f'DEBUG DATE {year} {month} {day}')
    date = datetime(year, month, day)
    return date.date()


def comments_strip(string):
    if len(string):
        return int(string[0].rstrip(' Comments').replace(',', ''))


def shares_strip(string):
    if len(string):
        return int(string[0].rstrip(' Shares'))


def simplify_url(string):
    return re.sub(r'&refid.*$', '', string[0])


def cast_to_int(string):
    if len(string):
        # if type(string) == list:
        #     return len(string)
        result = string[0]
        thousand = result.split('K')[0] if 'K' in result else 0
        you_and_others = re.match('You and (\\d+) others', result)
        if you_and_others:
            result = int(you_and_others.group(1)) + 1
        elif thousand:
            result = float(thousand) * 1000.0
        else:
            result = string[0]
        return int(result)


class PostItem(scrapy.Item):
    # page name
    source = scrapy.Field(output_processor=TakeFirst())

    date = scrapy.Field(
        input_processor=TakeFirst(),
        output_processor=parse_date
    )

    text = scrapy.Field(output_processor=Join(separator=u''))

    comments = scrapy.Field(output_processor=comments_strip)
    comment_items = scrapy.Field()
    commentators = scrapy.Field(output_processor=Join(separator=u'\n'))

    reactions = scrapy.Field(output_processor=cast_to_int)

    likes = scrapy.Field(output_processor=cast_to_int)
    ahah = scrapy.Field(output_processor=cast_to_int)
    love = scrapy.Field(output_processor=cast_to_int)
    wow = scrapy.Field(output_processor=cast_to_int)
    sigh = scrapy.Field(output_processor=cast_to_int)
    grrr = scrapy.Field(output_processor=cast_to_int)
    shares = scrapy.Field(output_processor=shares_strip)
    url = scrapy.Field(output_processor=simplify_url)


class CommentItem(scrapy.Item):
    source = scrapy.Field(output_processor=TakeFirst())

    text = scrapy.Field(output_processor=Join(separator=u''))
    # replies = scrapy.Field(output_processor=cast_to_int)
    replies = scrapy.Field()
    reply_items = scrapy.Field()
