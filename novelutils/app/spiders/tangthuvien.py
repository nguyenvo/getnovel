"""Get novel from domain tangthuvien.

.. _Web site:
   https://truyen.tangthuvien.vn

"""
from pathlib import Path

import scrapy


class TangThuVienSpider(scrapy.Spider):
    """Define spider for domain: tangthuvien."""
    name = 'tangthuvien'

    def __init__(self, url: str, save_path: Path, start_chap: int, stop_chap: int, *args, **kwargs):
        """Initialize the attributes for this spider.

        Args:
          url: full web site to novel info page
          save_path: path to raw directory
          start_chap: start chapter index
          stop_chap: stop chapter index, input -1 to get all chapters
          *args: variable length argument list
          **kwargs: arbitrary keyword arguments

        """
        super().__init__(*args, **kwargs)
        self.start_urls = [url]
        self.save_path = save_path
        self.start_chap = start_chap
        self.stop_chap = stop_chap
        self.menu = []

    def parse(self, response: scrapy.http.Response, **kwargs):
        """Extract info of the novel and get the link of the menu.

        Args:
          response: the response to parse
          **kwargs: arbitrary keyword arguments

        Yields:
          scrapy.Request: request to the menu of novel

        """
        # download cover
        yield scrapy.Request(
            url=response.xpath('//*[@id="bookImg"]/img/@src').get(),
            callback=self.parse_cover)
        get_info(response, self.save_path)
        menu_link = 'https://truyen.tangthuvien.vn/story/chapters?story_id=' + \
                    response.xpath('//*[@name="book_detail"]/@content').get()
        yield scrapy.Request(url=menu_link, callback=self.parse_link)

    def parse_cover(self, response: scrapy.http.Response):
        """Download the cover of novel.

        Args:
          response: the response contains a binary image

        Returns:
          None

        """
        (self.save_path / 'cover.jpg').write_bytes(response.body)

    def parse_link(self, response: scrapy.http.Response):
        """Extract link of the start chapter.

        Args:
          response: the response to parse

        Yields:
          scrapy.Request: request to the start chapter

        """
        self.menu.extend([
            x.strip() for x in response.xpath(
                '//a[contains(@class,"link-chap-")]/@href').getall()
        ])
        yield scrapy.Request(url=self.menu[self.start_chap - 1],
                             meta={'id': self.start_chap},
                             callback=self.parse_content)

    def parse_content(self, response: scrapy.http.Response):
        """Extract the content of chapter.

        Args:
          response: the response to parse

        Yields:
          scrapy.Request: request to the next chapter

        """
        get_content(response, self.save_path)
        if (response.meta['id'] == len(self.menu)) or response.meta['id'] == self.stop_chap:
            raise scrapy.exceptions.CloseSpider(reason='Done')
        response.request.headers[b'Referer'] = [str.encode(response.url)]
        yield scrapy.Request(url=self.menu[response.meta['id']],
                             headers=response.request.headers,
                             meta={'id': response.meta['id'] + 1},
                             callback=self.parse_content)


def get_info(response: scrapy.http.Response, save_path: Path):
    """Get info of this novel.

    Args:
      response: the response to parse
      save_path: path to raw data folder

    Returns:
      None

    """
    # get title
    title = response.xpath('/html/body/div[5]/div[1]/div[2]/h1/text()').get()
    author = response.xpath('/html/body/div[5]/div[1]/div[2]/p[1]/a[1]/text()').get()
    types = response.xpath('/html/body/div[5]/div[1]/div[2]/p[1]/a[2]/text()').get()
    foreword = response.xpath('/html/body/div[5]/div[4]/div[1]/div[1]/div[1]/p/text()').getall()
    info = list()
    info.append(title)
    info.append(author)
    info.append(response.request.url)
    info.append(types)
    info.extend(foreword)
    (save_path / 'foreword.txt').write_text(
        '\n'.join(info),
        encoding='utf-8'
    )


def get_content(response: scrapy.http.Response, save_path: Path):
    """Get title and content of chapter.

    Args:
      response: the response to parse
      save_path: path to raw directory

    Returns:
      None

    """
    # get chapter
    chapter = response.xpath('//div[contains(@class,"chapter")]/h2/text()').get().replace( u'\xa0', ' ')
    # get content
    content = response.xpath('//div[contains(@class,"box-chap")]//text()[not(parent::a)]').getall()
    content.insert(0, chapter)
    (save_path / f'{str(response.meta["id"])}.txt').write_text(
        '\n'.join([x.strip() for x in content if x.strip() != '']),
        encoding='utf-8'
    )
