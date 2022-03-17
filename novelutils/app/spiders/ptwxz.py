"""Get novel from domain ptwxz.

.. _Web site:
   https://www.ptwxz.com

"""
from pathlib import Path

import scrapy
from bs4 import BeautifulSoup
from scrapy.selector import Selector


class PtwxzSpider(scrapy.Spider):
    """Define spider for domain: ptwxz."""
    name = 'ptwxz'

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

    def parse(self, response: scrapy.http.Response, **kwargs):
        """Extract info of the novel and get the link of the menu.

        Args:
          response: the response to parse
          **kwargs: arbitrary keyword arguments

        Yields:
          scrapy.Request: request to the menu of novel

        """
        # download cover
        cover_link = response.xpath('//*[@id="content"]/table//td/a/img[@height="125"]/@src').get()
        if self.name not in cover_link:
            cover_link = response.url.split('bookinfo')[0] + cover_link
        yield scrapy.Request(cover_link, callback=self.parse_cover)
        get_info(response, self.save_path)
        # Make a request to start_chap
        url = response.xpath('//a[contains(@title,"点击阅读")]/@href').get()
        if self.name not in url:
            url = response.url.split('bookinfo')[0][:-1] + response.xpath('//a[contains(@title,"点击阅读")]/@href').get()
        yield scrapy.Request(url=url, callback=self.parse_start_chapter)

    def parse_cover(self, response: scrapy.http.Response):
        """Download the cover of novel.

        Args:
          response: The response contains a binary image.

        Returns:
          None

        """
        (self.save_path / 'cover.jpg').write_bytes(response.body)

    def parse_start_chapter(self, response: scrapy.http.Response):
        """Download the cover of novel.

        Args:
          response: the response contains a binary image

        Returns:
          None

        """
        chapter = response.xpath('//div[@class="centent"]/ul/li/a/@href').getall()[self.start_chap - 1]
        yield scrapy.Request(
            url=response.url + chapter,
            meta={
                'id': self.start_chap,
                'base_url': response.url
            },
            callback=self.parse_content,
        )

    def parse_content(self, response: scrapy.http.Response):
        """Extract the content of chapter.

        Args:
          response: the response to parse

        Yields:
          scrapy.Request: request to the next chapter

        """
        get_content(response, self.save_path)

        t = response.xpath('//div[@class="toplink"]/a/@href').getall()

        if t[2] == 'index.html' or response.meta['id'] == self.stop_chap:
            raise scrapy.exceptions.CloseSpider(reason='Done')
        response.request.headers[b'Referer'] = [str.encode(response.url)]
        yield scrapy.Request(
            url=response.meta['base_url'] + t[2],
            headers=response.request.headers,
            meta={
                'id': response.meta['id'] + 1,
                'base_url': response.meta['base_url']
            },
            callback=self.parse_content,
        )


def get_info(response: scrapy.http.Response, save_path: Path):
    """Get info of this novel.

    Args:
      response: the response to parse
      save_path: path to raw data folder

    Returns:
      None

    """
    # extract info
    # pylint: disable=inconsistent-quotes
    title = response.xpath('//*[@id="centerm"]//td[@align="center"]//h1/text()').get()
    author = response.xpath('//div[@id="content"]//td/text()')[5].get().replace("\xa0", "")
    types = response.xpath('//div[@id="content"]//td/text()')[4].get().replace("\xa0", "")
    foreword = response.xpath(
        '//*[@id="content"]/table//td[@valign="top"]/div[contains(@style,"left")]//text()').getall()
    info = list()
    info.append(title)
    info.append(author)
    info.append(response.request.url)
    info.append(types)
    info.extend(foreword)
    # write info to file
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
    # extract chapter title
    chapter = response.xpath('//h1/text()').get().strip()
    soup = BeautifulSoup(response.text, 'html.parser')
    data = Selector(text=str(soup)).xpath('//body/text()').getall()
    data.insert(0, chapter)
    content = '\n'.join([x.strip() for x in data if x.strip() != ''])
    (save_path / f'{str(response.meta["id"])}.txt').write_text(
        content,
        encoding='utf-8'
    )
