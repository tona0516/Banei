import re

from .Config import Config

class ScrapeUtil:
    @classmethod
    def extract_inner_text(cls, soup, class_name, tag_name='td'):
        if soup.find(tag_name, class_=class_name) is None:
            return '-'
        inner_text = soup.find(tag_name, class_=class_name).text
        inner_text = ScrapeUtil.__newline_to_comma(inner_text)
        inner_text = ScrapeUtil.__remove_brakets(inner_text)
        return inner_text

    @classmethod
    def comma_to_list(cls, list):
        comma_splited_text = ",".join(list)
        return ScrapeUtil.__remove_empty_item(comma_splited_text.split(","))

    @classmethod
    def __newline_to_comma(cls, text):
        return ScrapeUtil.replace_by_list_text(text, ['<br>', '\n'], ',')

    @classmethod
    def __remove_brakets(cls, text):
        return ScrapeUtil.replace_by_list_text(text, ['(', ')', '（', '）', '【', '】'])

    @classmethod
    def __remove_empty_item(cls, list):
        return [item for item in list if len(item) > 0]

    @classmethod
    def replace_by_list_text(cls, text, list, new=''):
        for old in list:
            text = text.replace(old, new)
        return text
