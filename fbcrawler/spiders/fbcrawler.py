import scrapy

from scrapy.loader import ItemLoader
from scrapy.http import FormRequest
from fbcrawler.items import FbPostItem


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
        with open('fb.txt', 'a') as out:
            out.write(str(response.body))

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
        with open('fb2.txt', 'a') as out:
            out.write(str(response.body))

        # select all posts
        for post in response.xpath("//div[contains(@data-ft, 'top_level_post_id')]"):
            new = ItemLoader(item=FbPostItem(), selector=post)
            new.add_xpath('comments', ".//div/a[contains(text(), 'Comments')]/text()")
            new.add_xpath('url', ".//a[contains(text(),'Full Story')]/@href")

            # returns full post-link in a list
            post = post.xpath(".//a[contains(text(), 'Full Story')]/@href").extract()
            temp_post = response.urljoin(post[0])
            yield scrapy.Request(temp_post, self.parse_post, dont_filter=True, meta={'item': new})

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
        new = ItemLoader(item=FbPostItem(),
                         response=response,
                         parent=response.meta['item'])
        new.add_xpath(
            'source',
            "//td/div/h3/strong/a/text() | //span/strong/a/text() | //div/div/div/a[contains(@href, 'post_id')]/strong/text()")
        new.add_xpath('date', '//div/div/abbr/text()')
        new.add_xpath('text', '//div[@data-ft]//p//text() | //div[@data-ft]/div[@class]/div[@class]/text()')
        new.add_xpath('reactions', "//a[contains(@href, 'reaction/profile')]/div/div/text()")

        reactions = response.xpath("//div[contains(@id,'sentence')]/a[contains(@href, 'reaction/profile')]/@href")
        reactions = response.urljoin(reactions[0].extract())
        yield scrapy.Request(reactions, callback=self.parse_reactions, dont_filter=True, meta={'item': new})

    def parse_reactions(self, response):
        new = ItemLoader(item=FbPostItem(),
                         response=response,
                         parent=response.meta['item'])
        new.add_xpath('likes', "//a[contains(@href, 'reaction_type=1')]/span/text()")
        new.add_xpath('ahah', "//a[contains(@href, 'reaction_type=4')]/span/text()")
        new.add_xpath('love', "//a[contains(@href, 'reaction_type=2')]/span/text()")
        new.add_xpath('wow', "//a[contains(@href, 'reaction_type=3')]/span/text()")
        new.add_xpath('sigh', "//a[contains(@href, 'reaction_type=7')]/span/text()")
        new.add_xpath('grrr', "//a[contains(@href, 'reaction_type=8')]/span/text()")
        yield new.load_item()
