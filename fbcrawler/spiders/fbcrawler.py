import scrapy
import re
import os

from scrapy.loader import ItemLoader
from scrapy.http import FormRequest
from fbcrawler.items import PostItem, CommentItem


class FacebookSpider(scrapy.Spider):
    '''
    Parse FB pages (needs credentials)
    '''
    name = 'fb'

    def __init__(self, email='', password='', page='', **kwargs):
        super()

        if not email or not password:
            raise ValueError('You need to provide valid email and password!')
        else:
            self.email = email
            self.password = password

        if not page:
            raise ValueError('You need to provide a valid page name to crawl!')
        else:
            self.page = page
        self.post_count = 0
        self.post_limit = 5
        self.start_urls = ['https://m.facebook.com/login/?ref=dbl&fl']
        self.root_url = 'https://m.facebook.com'

    def parse(self, response):
        self.log('PARSE HERE')
        return FormRequest.from_response(
            response,
            formxpath="//form[contains(@action, 'login')]",
            formdata={'email': self.email, 'pass': self.password},
            callback=self.parse_home
        )

    def parse_home(self, response):
        '''Parse user news feed page'''
        # Handle 'Approvals Code' checkpoint (ask user to enter code).
        if response.css('#approvals_code'):
            if not self.code:
                # Show facebook messages via logs
                # and request user for approval code.
                message = response.css('._50f4::text').extract()[0]
                self.log(message)
                message = response.css(
                    '._3-8y._50f4').xpath('string()').extract()[0]
                self.log(message)
                self.code = input('Enter the code: ')
            self.code = str(self.code)
            if not (self.code and self.code.isdigit()):
                self.log('Bad approvals code detected.')
                return
            return FormRequest.from_response(
                response,
                formdata={'approvals_code': self.code},
                callback=self.parse_home,
            )
        # Handle 'Save Browser' checkpoint.
        elif response.xpath("//div/input[@value='Ok' and @type='submit']"):
            return FormRequest.from_response(
                response,
                formdata={'name_action_selected': 'dont_save'},
                callback=self.parse_home,
                dont_filter=True,
            )
        # Handle 'Someone tried to log into your account' warning.
        elif response.css('button#checkpointSubmitButton'):
            return FormRequest.from_response(
                response, callback=self.parse_home, dont_filter=True,)

        # Else go to the user profile.
        href = response.urljoin(self.page)
        self.logger.info('Parse function called on %s', href)
        return scrapy.Request(
            url=href,
            callback=self.parse_page,
        )

    def parse_page(self, response):
        for post in response.xpath("//div[contains(@data-ft, 'top_level_post_id')]"):
            new = ItemLoader(item=PostItem(), selector=post)
            new.add_xpath('comments', ".//div/a[contains(text(), 'Comments')]/text()")
            new.add_xpath('url', ".//a[contains(text(), 'Full Story')]/@href")
            # #Cannot get shares because the body doesnot contains it
            # new.add_xpath('shares', ".//*[contains(text(), 'Shares')]/text()")

            post = post.xpath(".//a[contains(text(), 'Full Story')]/@href").extract()
            post_link = response.urljoin(post[0])
            yield scrapy.Request(post_link, self.parse_post, dont_filter=True, meta={'item': new})

        next_page = response.xpath("//div/a[contains(text(), 'Show more')]/@href")
        if len(next_page) > 0:
            next_page = response.urljoin(next_page[0].extract())
            yield scrapy.Request(next_page, callback=self.parse_page)
        else:
            next_page = response.xpath("//div/a[contains(text(), '2017')]/@href")
            if len(next_page) > 0:
                next_page = response.urljoin(next_page[0].extract())
                yield scrapy.Request(next_page, callback=self.parse_page)

    def parse_post(self, response):
        new = ItemLoader(item=PostItem(),
                         response=response,
                         parent=response.meta['item'])
        new.add_xpath(
            'source',
            "//td/div/h3/strong/a/text() | //span/strong/a/text() | //div/div/div/a[contains(@href, 'post_id')]/strong/text()")
        new.add_xpath('date', '//div/div/abbr/text()')
        new.add_xpath('text', '//div[@data-ft]//p//text() | //div[@data-ft]/div[@class]/div[@class]/text()')
        new.add_xpath('reactions', "//a[contains(@href, 'reaction/profile')]/div/div/text()")
        if new.get_output_value('comments'):
            yield scrapy.Request(response.urljoin(response.meta['item'].get_output_value('url')),
                                 callback=self.parse_comments, dont_filter=True, meta={'item': new})

        reactions = response.xpath("//div[contains(@id, 'sentence')]/a[contains(@href, 'reaction/profile')]/@href")
        reactions = response.urljoin(reactions[0].extract())
        yield scrapy.Request(reactions, callback=self.parse_reactions, dont_filter=True, meta={'item': new})

    def parse_reactions(self, response):
        new = ItemLoader(item=PostItem(),
                         response=response,
                         parent=response.meta['item'])
        new.add_xpath('likes', "//a[contains(@href, 'reaction_type=1')]/span/text()")
        new.add_xpath('love', "//a[contains(@href, 'reaction_type=2')]/span/text()")
        new.add_xpath('wow', "//a[contains(@href, 'reaction_type=3')]/span/text()")
        new.add_xpath('ahah', "//a[contains(@href, 'reaction_type=4')]/span/text()")
        new.add_xpath('sigh', "//a[contains(@href, 'reaction_type=7')]/span/text()")
        new.add_xpath('grrr', "//a[contains(@href, 'reaction_type=8')]/span/text()")
        yield new.load_item()

    def parse_comments(self, response):
        root = ItemLoader(item=PostItem(), parent=response.meta['item'])
        coms = []
        # next_page = response.xpath("//div[contains(@id, 'see_next')]/a/@href")

        # next_page = response.xpath("//div[contains(@id, 'see_next')]/a/@data-ajaxify-href")
        # prev_page = response.xpath("//div[contains(@id, 'see_prev')]/a/@data-ajaxify-href")
        # if len(next_page) > 0:
        #     # next_page = response.urljoin(next_page[0].extract())
        #     # yield scrapy.Request(next_page, callback=self.parse_comments, meta={'item': root})
        #     next_page = next_page[0].extract()
        #     yield response.follow(next_page, callback=self.parse_comments, meta={'item': root})

        for com in response.xpath('//div[@id="root"]/div/div/div/div/div'):
            new = ItemLoader(item=CommentItem(), selector=com)
            new.add_xpath('source', "./div/h3/a/text() | ./div/div/h3/a/text()")
            new.add_xpath('text', "./div/div/span[not(contains(text(),' · '))]/text() | ./div/div/text()")
            replies = com.xpath('./div/div/div/div/a[contains(text(), "repli")]/text()').extract()
            rep_link = com.xpath('./div/div/div/div/a[contains(text(), "repli")]/@href').extract()

            if replies and len(replies):
                found = re.search('(\d+) replies', replies[0])
                if found:
                    num_reps = found.group(1)
                    rep = response.urljoin(rep_link[0])
                    yield scrapy.Request(rep, callback=self.parse_replies, meta={'com': new, 'item': root})
            coms.append(new.load_item())

        prev_page = response.xpath("//div[contains(@id, 'see_prev')]/a/@href")
        if len(prev_page) > 0:
            # yield scrapy.Request(prev_page, callback=self.parse_comments, meta={'item': root})
            # prev_page = response.urljoin(prev_page[0].extract())
            prev_page = prev_page[0].extract()
            yield response.follow(prev_page, callback=self.parse_comments, meta={'item': root})
        root.add_value('comment_items', [c for c in coms if c])
        yield root.load_item()

    def parse_replies(self, response):
        com = ItemLoader(item=CommentItem(), parent=response.meta['com'])
        root = ItemLoader(item=PostItem(), parent=response.meta['item'])
        reps = []
        for rep in response.xpath("//div[@id='root']/div/div/div/div"):
            new = ItemLoader(item=CommentItem(), selector=rep)
            new.add_xpath('source', ".//h3/a/text()")
            new.add_xpath('text', ".//span[not(contains(text(), ' · ')) and not(contains(text(), 'View more'))]/text() | .//div/text()")
            reps.append(new.load_item())
        com.add_value('replies', [r for r in reps if r])
        yield com.load_item()
