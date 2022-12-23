"""Get novel on domain truyenchu.

.. _Web site:
   https://truyenchu.vn/

"""

from scrapy import Spider, Selector
from scrapy.http import Response, FormRequest
from scrapy.http.response.text import TextResponse
from scrapy.exceptions import CloseSpider

from getnovel.app.items import Info, Chapter
from getnovel.app.itemloaders import InfoLoader, ChapterLoader


class TruyenChuSpider(Spider):
    """Define spider for domain: truyenchu"""

    name = "truyenchu"

    def __init__(
        self,
        url: str,
        start_chap: int,
        stop_chap: int,
        *args,
        **kwargs,
    ):
        """Initialize attributes.

        Parameters
        ----------
        url : str
            Url of the novel information page.
        start_chap : int
            Start crawling from this chapter.
        stop_chap : int
            Stop crawling at this chapter, input -1 to get all chapters.
        """
        super().__init__(*args, **kwargs)
        self.start_urls = [url]
        self.start_chap = start_chap
        self.stop_chap = stop_chap

    def parse(self, response: Response):
        """Extract info and send request to table of content.

        Parameters
        ----------
        response : Response
            The response to parse.

        Yields
        ------
        Info
            Info item.
        Request
            Request to table of content.
        """
        yield get_info(response)
        # calculate the position of start_chap in menu list
        total_chap = 50
        start_chap = self.start_chap - 1
        menu_page_have_start_chap = start_chap // total_chap + 1
        pos_of_start_chap_in_menu = start_chap % total_chap
        yield FormRequest(
            method="GET",
            url="https://truyenchu.vn/api/services/list-chapter",
            meta={"pos_start": pos_of_start_chap_in_menu},
            callback=self.parse_start,
            formdata={
                "type": "list_chapter",
                "tid": response.xpath('//input[@id="truyen-id"]/@value').get(),
                "tascii": response.xpath('//input[@id="truyen-ascii"]/@value').get(),
                "page": str(menu_page_have_start_chap),
            },
        )

    def parse_start(self, response: TextResponse):
        """Extract link of the start chapter.

        Parameters
        ----------
        response : Response
            The response to parse.

        Yields
        ------
        Request
            Request to the start chapter.
        """
        jsonr = response.json()
        if jsonr["chap_list"] == "":
            raise CloseSpider(reason="start chapter is not exists")
        mini_toc = Selector(text=["chap_list"]).xpath("//li//a/@href").getall()
        yield response.follow(
            url=mini_toc[response.meta["pos_start"]],
            callback=self.parse_content,
            meta={"id": self.start_chap},
        )

    def parse_content(self, response: Response):
        """Extract content.

        Parameters
        ----------
        response : Response
            The response to parse.

        Yields
        ------
        Chapter
            Chapter item.
        Request
            Request to the next chapter.
        """
        yield get_content(response)
        next_url = response.xpath('//a[@id="next_chap"]/@href').get()
        if (next_url == "#") or (response.meta["id"] == self.stop_chap):
            raise CloseSpider(reason="Done")
        yield response.follow(
            url=next_url,
            meta={"id": response.meta["id"] + 1},
            callback=self.parse_content,
        )


def get_info(response: Response) -> Info:
    """Get novel information.

    Parameters
    ----------
    response : Response
        The response to parse.

    Returns
    -------
    Info
        Populated Info item.
    """
    imgurl = response.xpath('//div[@class="book"]/img/@src').get()
    r = InfoLoader(item=Info(), response=response)
    r.add_xpath("title", '//h1[@class="story-title"]/a/text()')
    r.add_xpath("author", '//*[@itemprop="author"]//span/text()')
    r.add_xpath("types", '//*[@id="truyen"]//div[1]//div[1]/div[3]/a/text()')
    r.add_xpath("foreword", '//*[@id="truyen"]/div[1]/div[2]/div[2]/div[2]//text()')
    r.add_value("image_urls", response.urljoin(imgurl))
    r.add_value("url", response.request.url)
    return r.load_item()


def get_content(response: Response) -> Chapter:
    """Get chapter content.

    Parameters
    ----------
    response : Response
        The response to parse.

    Returns
    -------
    Chapter
        Populated Chapter item.
    """
    r = ChapterLoader(item=Chapter(), response=response)
    r.add_xpath("title", '//a[@class="chapter-title"]//text()')
    r.add_xpath("content", '//div[@id="chapter-c"]//text()[not(parent::script)]')
    r.add_value("id", str(response.meta["id"]))
    return r.load_item()
