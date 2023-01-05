"""Define NovelCrawler class."""

import time
import logging
from pathlib import Path
from shutil import rmtree

import tldextract
import validators
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from scrapy.spiderloader import SpiderLoader

from getnovel.data import scrapy_settings
from getnovel.utils.file import FileConverter
from getnovel.utils.typehint import PathStr

_logger = logging.getLogger(__name__)


class NovelCrawler:
    """Download novel from website"""

    def __init__(self, url: str) -> None:
        """Initialize NovelCrawler with url, and assign path of raw
        directory.

        Parameters
        ----------
        url : str
            The link of the novel information page.
        """
        if validators.url(url) is False:
            _logger.error("The input url not valid!")
            return
        self.u: str = url
        self.spn = tldextract.extract(self.u).domain  # spider name

    def crawl(
        self,
        rm: bool,
        start_index: int,
        num_chap: int,
        clean: bool,
        result: PathStr = None,
    ) -> PathStr:
        """Download novel and store it in the raw directory.

        Parameters
        ----------
        rm : bool
            If specified, remove all existing files in raw directory.
        start_index : int
            File name will increase from this value.
        num_chap : int
            Number of chapters to crawl, input -1 to crawl\
            until the last chapter.
        clean : bool
            If specified, clean result files after crawling.
        result : PathStr, optional
            Path of result directory, by default None.

        Raises
        ------
        CrawlNovelError
            Index of start chapter need to be greater than zero.

        Returns
        -------
        PathStr
            Path the raw directory.
        """
        if start_index < 1:
            raise CrawlNovelError(
                "Index of start index need to be greater than zero"
            )
        if result is None:
            rp = Path.cwd() / self.spn / time.strftime(r"%Y_%m_%d-%H_%M_%S") / "raw"
        else:
            rp = Path(result)
        if rm is True:
            _logger.info("Remove existing files in: %s", rp.resolve())
            if rp.exists():
                rmtree(rp)
        rp.mkdir(exist_ok=True, parents=True)
        rp = rp.resolve()
        spider_class = self._get_spider()
        process = CrawlerProcess(settings=scrapy_settings.get_settings(rp))
        process.crawl(
            spider_class,
            u=self.u,
            s=start_index,
            n=num_chap,
        )
        process.start()
        _logger.info("Done crawling. View result at: %s", str(rp))
        if clean is True:
            _logger.info("Start cleaning")
            c = FileConverter(rp, rp)
            c.clean(dedup=False, rm_result=False)
        return rp

    def _get_spider(self):
        """Get spider class based on the url domain.

        Returns
        -------
        object
            The spider class object.

        Raises
        ------
        CrawlNovelError
            Spider not found.
        """
        loader = SpiderLoader.from_settings(
            Settings({"SPIDER_MODULES": ["getnovel.app.spiders"]})
        )
        if self.spn not in loader.list():
            raise CrawlNovelError(f"Spider {self.spn} not found!")
        return loader.load(self.spn)

    def get_langcode(self) -> str:
        """Return language code of novel"""
        if self.spn in ("ptwxz", "uukanshu", "69shu"):
            return "zh"
        else:
            return "vi"


class CrawlNovelError(Exception):
    """Handle NovelCrawler Exception"""
