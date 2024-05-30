from time import sleep

from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from model import logger

from base_parser import BaseParser
from config import selenium_options


class BaseSelenParser(BaseParser):
    def open_worker(self, url):
        if self.worker:
            self.worker.close()
        self.worker = webdriver.Chrome(options=options)
        self.worker.get(url)

    def close_worker(self):
        self.worker.stop_client()
        self.worker = None

    def get_groups(self):
        try:
            announcements = self.worker.find_elements(
                self.s.group.e_type.value, self.s.group.element
            ).click()
        except TimeoutException:
            logger.error(f"ERROR, {self.name}, driver timeout")
            return []
        return announcements

    def check_announs_fill(self, announcement):
        announcement.location_once_scrolled_into_view
        return True

    def get_value(self, announcement, elem_data):
        try:
            announcement.location_once_scrolled_into_view
            element = announcement.find_element(
                elem_data.e_type.value, elem_data.element
            )
        except Exception:
            sleep(0.5)
            element = announcement.find_element(
                elem_data.e_type.value, elem_data.element
            )
        if elem_data.atr:
            element = element.get_attribute(elem_data.atr)
        return element

    def get_id(self, announcement):
        return self.get_value(announcement, self.s.b_id)

    def get_link(self, announcement):
        return self.get_value(announcement, self.s.link)

    def get_image(self, announcement):
        return self.get_value(announcement, self.s.image)

    def get_title(self, announcement):
        return self.get_value(announcement, self.s.title)

    def get_price(self, announcement):
        return self.get_value(announcement, self.s.price).text
