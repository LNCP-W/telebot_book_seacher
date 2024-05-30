from base_parser import BaseParser
from schema import (
    izi_schem,
    bespl_schem,
    olx_schem,
    shafa_schem,
    liberby_schem,
    SoupElement,
)
import asyncio


class IziParser(BaseParser):
    s = izi_schem
    name = "IZI"

    def get_groups(self) -> [SoupElement]:
        parts = self.worker.find_all("main")
        results = []
        if len(parts):
            results = (
                self.worker.find_all("main")[0]
                .findChildren(recursive=False)[1]
                .findChildren(recursive=False)
            )
        if not len(results):
            self.logger.error(f"no ann {self.name}")
        return results

    def check_announs_fill(self, announcement: SoupElement) -> bool:
        top_mark = announcement.find_all(class_="ek-text_color_brand-blue")
        if not top_mark or top_mark[0].text == "ТОП":
            return False
        return True

    def get_id(self, announcement) -> str:
        link = self.get_link(announcement)
        _id = link.split("/")[-1].split("-")[1]
        return _id


class ShafaParser(BaseParser):
    s = shafa_schem
    name = "Shafa"

    def get_id(self, announcement) -> str:
        link = self.get_link(announcement)
        _id = link.split("/")[-1].split("-")[0]
        return _id

    def get_price(self, announcement) -> str:
        price = super().get_price(announcement)
        return price.split('грн')[0] + 'грн'


class BesplParser(BaseParser):
    s = bespl_schem
    name = "Besplatka"

    # def get_title(self, announcement):
    #     return super().get_title(announcement).text


class LiberbyParser(BaseParser):
    s = liberby_schem
    name = "Liberby"

    def get_id(self, announcement):
        link = self.get_link(announcement)
        link_text = link.split("/")[-1]
        import hashlib
        book_id = hashlib.sha224(link_text.encode()).hexdigest()
        return book_id

    def get_title(self, announcement):
        author = self.get_author(announcement)
        title = super().get_title(announcement)
        return author + " " + title

    def get_author(self, announcement):
        a = self.get_value(announcement, self.s.author)
        return a if a else ""


class OLXParser(BaseParser):
    s = olx_schem
    name = "OLX"

    def get_id(self, announcement):
        return announcement["id"]

    # def get_title(self, announcement):
    #     return super().get_title(announcement).text



parsers = [
    # IziParser(),
    OLXParser(),
    BesplParser(),
    LiberbyParser(),
    ShafaParser(),
]

async def run_all():
    for parser in parsers:
        await parser.run()


if __name__ == "__main__":
    asyncio.run(run_all())