from urllib import request
from urllib import error
from socket import timeout
from bs4 import BeautifulSoup

from .exception import ScraperException

class APIClient:
    @classmethod
    def get_soup(cls, url, timeout_seconds=10):
        try:
            f = request.urlopen(url, timeout=timeout_seconds)
            html = f.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
        except Exception:
            raise ScraperException('message=\"Failed to fetch soup.\", url=\"' + url + '\"')
        else:
            if soup.find('p', class_='leadNoData'):
                raise ScraperException('message=\"No data in the soup.\", url=\"' + url + '\"')
            return soup