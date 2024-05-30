import logging

from pydantic import BaseModel
from typing import Optional
from enum import Enum, EnumMeta
from selenium.webdriver.common.by import By

# from logging import getLogger
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()




class BookToFind(BaseModel):
    id: int | None = None
    user_id: int
    title: str
    exclude: str | None = None

    def __str__(self):
        excludes = (
            f" (Виключення: {', '.join(self.exclude.split())})" if self.exclude else ""
        )
        return f"{self.title.capitalize()}{excludes}"

    @property
    def to_text(self):
        exclude_string = (", " + self.exclude) if self.exclude else ""
        result = self.title + exclude_string
        return result

    class Config:
        from_attributes = True

class BookInput(BaseModel):
    book_id: str
    link: str
    image: Optional[str] = None
    title: str
    price: Optional[str] = None
    full: str | None = None
    parent: BookToFind|None = None

class ETypeBS(Enum):
    c = "class_"
    t = "tag"


class ETypeSel(Enum):
    c = By.CLASS_NAME
    t = By.TAG_NAME


class SoupElement(BaseModel):
    e_type: ETypeBS
    element: str | None = None
    atr: str | None = None

    @property
    def d(self):
        return {self.e_type.value: self.element}


class SelElement(SoupElement):
    e_type: ETypeSel


class BSClass(BaseModel):
    class_: str


class BSTag(BaseModel):
    tag: str


class BSElement(BaseModel):
    el: BSTag | BSClass
    atr: str | None = None

    class Config:
        from_attributes = True


class SiteSchema(BaseModel):
    s_url: str
    s_url_2: str | None = None
    group: SoupElement
    b_id: SoupElement | None = None
    link: SoupElement
    image: SoupElement
    title: SoupElement
    price: SoupElement
    full: SoupElement| None = None
    link_prefix: str
    author: SoupElement | None = None


class User(BaseModel):
    id: int | None = None
    chat_id: int
    name: str

    class Config:
        from_attributes = True


class Site(BaseModel):
    id: int | None = None
    name: str


class ProcessedBooks(BaseModel):
    id: int | None = None
    book_id: str
    site_id: int
    parent_book: int|None = None
    link: str|None = None

