from time import sleep
import asyncio
from selenium import webdriver
from async_property import async_property, async_cached_property
import requests
from pyvirtualdisplay import Display
from bs4 import BeautifulSoup
from model import BookInput, BookToFind, SoupElement, ETypeBS, logger, SiteSchema
from config import selenium_options
from db import DB
import aiohttp

from logging import getLogger


class BaseParser:
    s: SiteSchema
    name: str = "base"
    logger = logger

    def __init__(self):
        self.ids: [int] = []
        self.db = DB()
        self.worker: BeautifulSoup | None = None
        self.need_second: bool = False
        self.works: bool = False

    @async_property
    async def books_to_find(self) -> [BookToFind]:
        return await self.db.get_books(1)

    def get_groups(self) -> [SoupElement]:
        C=1
        results = self.worker.find_all(**self.s.group.d)
        if not len(results):
            self.logger.error(f"no ann {self.name}")
        return results

    def get_value(self, announcement, elem_data: SoupElement):
        if elem_data.e_type == ETypeBS.t:
            element = announcement.find(elem_data.element)
        else:
            element = announcement.find(**elem_data.d)
        if element and elem_data.atr:
            element = element[elem_data.atr]
        return element

    def get_id(self, announcement) -> str:
        return self.get_value(announcement, self.s.b_id)

    def get_link(self, announcement) -> str:
        return self.get_value(announcement, self.s.link)

    def get_image(self, announcement) -> str:
        image = self.get_value(announcement, self.s.image)

        if not image or "no_thumbnail" in image:
            image = (
                "https://www.freeiconspng.com/thumbs/no-image-icon/no-image-icon-6.png"
            )
            if self.name == "OLX":
                c = 1
        return image

    def get_title(self, announcement) -> str:
        title = self.get_value(announcement, self.s.title)
        if not isinstance(title, str):
            title = title.text
        title = title.replace(',','').replace('.','').replace('«','').replace('»','').replace('›','').lower()
        return title

    def get_price(self, announcement) -> str:
        return self.get_value(announcement, self.s.price).text

    @staticmethod
    def have_exclude(book: BookInput, btf: BookToFind) -> bool:
        if btf.exclude:
            for i in btf.exclude.split():
                if i in book.title:
                    return True
        return False

    @staticmethod
    def have_in_title(book: BookInput, btf: BookToFind) -> bool:
        correct = [i.lower() in book.title.lower() for i in btf.title.split()]
        if all(correct):
            if len(btf.title.split()) < 2:
                correct = [
                    i.lower() in book.title.lower().split() for i in btf.title.split()
                ]
                if not all(correct):
                    return False
            return True
        return False

    def have_in_title_v2(self, book: BookInput, btf:BookToFind):
        if btf.title.lower() in book.full.lower():
            if len(btf.title.split()) < 2:
                correct = [
                    i.lower() in book.full.lower().split() for i in btf.title.split()
                ]
                if not all(correct):
                    return False

            return True

        return False

    async def check_books(self, books) -> [bool, [BookInput]]:
        site_id = await self.site_id
        processed = await self.db.get_processed(self.site_id)
        need_second = False
        books_is_in_base = [b.book_id not in processed for b in books]
        if all(books_is_in_base):
            need_second = True
        cleaned_books = []
        self.logger.debug(
            f"new, {self.name}, {len([i for i in books_is_in_base if i])}"
        )
        books_to_find = await self.books_to_find
        books_to_base = []
        new_books = [book for book in books if book.book_id not in processed]
        # new_books = [self.get_full_text(book) for book in new_books]
        # new_books = await asyncio.gather(*new_books)
        c=1
        for book in new_books:
            for b_t_f in books_to_find:
                if self.have_in_title(book, b_t_f) and not self.have_exclude(
                    book, b_t_f
                ):
                    self.logger.error(f"{b_t_f.title}, {book.link}")
                    book.parent = b_t_f
                    cleaned_books.append(book)
                    break
            books_to_base.append(book)
        if books_to_base:
            await self.db.add_processed(books_to_base, self.site_id)
        return need_second, cleaned_books

    def get_url(self, second=None) -> str:
        url = self.s.s_url
        if second and self.s.s_url_2:
            url = self.s.s_url_2
        return url

    async def get_full_text(self, book: BookInput) -> BookInput:
        full_text = book.title
        if self.s.full:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"}
                async with session.get(book.link, headers=headers) as response:
                    if response.status == 200:
                        html = BeautifulSoup(await response.text())
                        text_part = self.get_value(html, self.s.full)
                        if text_part:
                            text = text_part.text.strip().replace("\n", " ")
                            # print(self.name, len(text))
                            full_text += ' ' + text
                    else:
                        logger.exception('can`t get full text')
        for i in ['"', "'", '(', ')', '/', '-', '[', ']',':',';', '|', '\\']:
            full_text = full_text.replace(i, '')
        book.full = full_text
        return book

    def check_announs_fill(self, announcement: SoupElement) -> bool:
        text = announcement.text.strip()
        if not text or text.startswith("Top") or text.startswith("ТОП"):
            return False
        return True

    # def get_selenium_data(self, driver: selenium_async.WebDriver):
    def get_selenium_data(self):
        # display = Display(visible=False, size=(800, 900))
        # display.start()
        with webdriver.Chrome(options=selenium_options) as driver:
            # driver = webdriver.Chrome(options=selenium_options)

            driver.get(self.get_url(self.need_second))
            self.need_second = False
            last_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(10):
                if i == 0:
                    continue
                y = int(i * last_height / 10)
                driver.execute_script(f"window.scrollTo(0,  {y});")
                sleep(0.2)
            driver.execute_script('document.body.style.zoom = "1%"')
            sleep(3)
            text = driver.page_source
            driver.close()
            # try:
            #     driver.quit()
            #     # driver.stop_client()
            # except Exception as e:
            #     print(e)
        return text

    async def open_worker(self):
        if self.worker:
            self.worker.decompose()
        # driver = webdriver.Chrome(options=selenium_options)
        # text = self.get_selenium_data
        text = await asyncio.to_thread(self.get_selenium_data)
        self.worker = BeautifulSoup(text, "html.parser")

    @async_cached_property
    async def site_id(self) -> int:
        return await self.db.get_or_add_site(self.name)

    def close_worker(self):
        self.worker.decompose()
        self.worker = None

    async def parse(self):
        await self.open_worker()
        announcements = self.get_groups()
        if len(announcements) == 0:
            announcements = self.get_groups()
        books = []
        for announcement in announcements:
            if not self.check_announs_fill(announcement):
                continue
            book_id = self.get_id(announcement)
            link = self.get_link(announcement)
            try:
                image = self.get_image(announcement)
            except Exception:
                image = "https://upload.wikimedia.org/wikipedia/commons/1/14/No_Image_Available.jpg?20200913095930"
            title = self.get_title(announcement)
            price = self.get_price(announcement)
            book = BookInput(
                book_id=book_id.strip(),
                link=self.s.link_prefix + link.strip(),
                image=image,
                title=title.lower().strip(),
                price=price.strip(),
            )
            books.append(book)
        self.close_worker()
        if books:
            self.works = True
        else:
            self.works = False
        self.logger.info(f"Find books: {self.name} {len(books)}")

        need_second, cleaned_books = await self.check_books(books)
        return need_second, cleaned_books

    async def run(self) -> [BookInput]:
        # await asyncio.sleep(5)
        need_second, books = await self.parse()
        if need_second and self.s.s_url_2:
            self.need_second = True
            need_second, second_books = await self.parse()
            self.need_second = False
            books += second_books
        return books
