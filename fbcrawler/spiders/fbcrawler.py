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
        # select all posts
        for post in response.xpath("//div[contains(@data-ft, 'top_level_post_id')]"):
            new = ItemLoader(item=PostItem(), selector=post)
            new.add_xpath('comments', ".//div/a[contains(text(), 'Comments')]/text()")
            new.add_xpath('url', ".//a[contains(text(), 'Full Story')]/@href")

            # returns full post-link in a list
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
        import os.path
        if not os.path.isfile('apost.html'):
            with open('apost.html', 'wb') as f:
                f.write(response.body)
        new = ItemLoader(item=PostItem(),
                         response=response,
                         parent=response.meta['item'])
        new.add_xpath(
            'source',
            "//td/div/h3/strong/a/text() | //span/strong/a/text() | //div/div/div/a[contains(@href, 'post_id')]/strong/text()")
        new.add_xpath('date', '//div/div/abbr/text()')
        new.add_xpath('text', '//div[@data-ft]//p//text() | //div[@data-ft]/div[@class]/div[@class]/text()')
        new.add_xpath('reactions', "//a[contains(@href, 'reaction/profile')]/div/div/text()")
        new.add_xpath('shares', "//*[contains(text(), 'Shares')]/text()")
        comments = new.get_output_value('comments') or 0
        if comments:
            comments_url = self.root_url + re.sub(r'&refid.*$', '', response.meta['item'].get_output_value('url'))
            yield scrapy.Request(comments_url, callback=self.parse_comments_link, dont_filter=True, meta={'item': new})

        reactions = response.xpath("//div[contains(@id, 'sentence')]/a[contains(@href, 'reaction/profile')]/@href")
        reactions = response.urljoin(reactions[0].extract())
        yield scrapy.Request(reactions, callback=self.parse_reactions, dont_filter=True, meta={'item': new})

    def parse_reactions(self, response):
        new = ItemLoader(item=PostItem(),
                         response=response,
                         parent=response.meta['item'])
        new.add_xpath('likes', "//a[contains(@href, 'reaction_type=1')]/span/text()")
        new.add_xpath('ahah', "//a[contains(@href, 'reaction_type=4')]/span/text()")
        new.add_xpath('love', "//a[contains(@href, 'reaction_type=2')]/span/text()")
        new.add_xpath('wow', "//a[contains(@href, 'reaction_type=3')]/span/text()")
        new.add_xpath('sigh', "//a[contains(@href, 'reaction_type=7')]/span/text()")
        new.add_xpath('grrr', "//a[contains(@href, 'reaction_type=8')]/span/text()")
        yield new.load_item()

    def parse_comments_link_fuck(self, response):
        if not os.path.isfile('check.html'):
            with open('check.html', 'wb') as f:
                f.write(response.body)
        root = response.meta['item']
        coms = []
        if not os.path.isfile('check2.html'):  # maybe passed ady
            if root.get_output_value('url') == '/story.php?story_fbid=2023103414649762&id=1655541704739270':
                with open('check2.html', 'wb') as f:
                    f.write(response.body)
        if not os.path.isfile('check22.html'):
            if root.get_output_value('url') == '/story.php?story_fbid=2016549255305178&id=1655541704739270':
                with open('check22.html', 'wb') as f:
                    f.write(response.body)
        if not os.path.isfile('check23.html'):
            if root.get_output_value('url') == '/story.php?story_fbid=2019397411687029&id=1655541704739270':
                with open('check23.html', 'wb') as f:
                    f.write(response.body)
        # for com in response.xpath('//div[@id="root"]/div/div[2]/div/div[5]/div/div'):
        # for com in response.xpath('//div[@id="root"]/div/div/div/div/div | //div[@id="root"]/div/div/div/div'):
        # for com in response.xpath('//div[@id="root"]/div/div/div/div/div[not(contains(@id, "see"))]'):
        for com in response.xpath('//div[@id="root"]/div/div/div/div/div'):
            new = ItemLoader(item=CommentItem(), selector=com)
            new.add_xpath('source', "./div/h3/a/text() | ./div/div/h3/a/text()")
            new.add_xpath('text', "./div/div/span[not(contains(text(),' · '))]/text() | ./div/div/text()")
            if not new.get_collected_values('source') and not new.get_collected_values('text'):
                continue
            self.log(f'HAHA {new.load_item()}')
            # replies = com.xpath('./div/div/div/a[contains(text(), "repli")]/text()').extract()
            # rep_link = com.xpath('./div/div/div/div/div/a[contains(text(), "repli")]/@href').extract()
            replies = com.xpath('./*/a[contains(text(), "repli")]/text()').extract()
            rep_link = com.xpath('./*/a[contains(text(), "repli")]/@href').extract()
            self.log(f'FUCK {replies} {rep_link}')
            if replies:
                num_reps = [int(s) for s in replies.split(' ') if s.isdigit()][0]
            # # for i in range(len(replies)):
                rep = response.urljoin(rep_link)
                yield scrapy.Request(rep, callback=self.parse_replies, meta={'com': new})
            coms.append(new.load_item())
        # if root.get_output_value('comment_items'):
        #     root['comment_items'] += coms
        # else:

        root.add_value('comment_items', [c for c in coms if c])
        # # @TODO: later
        # replies = response.xpath('//div/a[contains(text(), "repli")]/@href')
        # for i in range(len(replies)):
        #     rep = response.urljoin(replies[i].extract())
        #     yield scrapy.Request(rep, callback=self.parse_replies)

        next_page = response.xpath("//div[contains(@id, 'see_next')]/a/@href")
        if len(next_page) > 0:
            next_page = response.urljoin(next_page[0].extract())
            yield scrapy.Request(next_page, callback=self.parse_comments_link, meta={'item': root})

    def parse_comments_link(self, response):
        root = response.meta['item']
        coms = []
        for com in response.xpath('//div[@id="root"]/div/div/div/div/div'):
            new = ItemLoader(item=CommentItem(), selector=com)
            new.add_xpath('source', "./div/h3/a/text() | ./div/div/h3/a/text()")
            new.add_xpath('text', "./div/div/span[not(contains(text(),' · '))]/text() | ./div/div/text()")
            if not new.get_collected_values('source') and not new.get_collected_values('text'):
                continue
            self.log(f'HAHA {new.load_item()}')
            replies = com.xpath('./div/div/div/a[contains(text(), "repli")]/text()').extract()
            rep_link = com.xpath('./div/div/div/a[contains(text(), "repli")]/@href').extract()
            self.log(f'FUCK {replies} {rep_link}')

            # if replies:
            #     num_reps = [int(s) for s in replies.split(' ') if s.isdigit()][0]
            #     rep = response.urljoin(rep_link)
            #     yield scrapy.Request(rep, callback=self.parse_replies, meta={'com': new})
            coms.append(new.load_item())
        root.add_value('comment_items', [c for c in coms if c])

        next_page = response.xpath("//div[contains(@id, 'see_next')]/a/@href")
        if len(next_page) > 0:
            next_page = response.urljoin(next_page[0].extract())
            yield scrapy.Request(next_page, callback=self.parse_comments_link, meta={'item': root})

    def parse_replies(self, response):
        com = response.meta['com']
        reps = []
        if not os.path.isfile('check3.html'):
            with open('check3.html', 'wb') as f:
                f.write(response.body)
        for rep in response.xpath("//div[contains(@id, 'root')]/div/div/div"):
            new = ItemLoader(item=CommentItem(), selector=rep)
            new.add_xpath('source', ".//h3/a/text()")
            new.add_xpath('text', ".//span[not(contains(text(), ' · ')) and not(contains(text(), 'View more'))]/text() | .//div/text()")
            reps.append(new.load_item())
            # yield new.load_item()
        com.add_value('replies', [r for r in reps if r])