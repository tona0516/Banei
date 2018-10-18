from urllib import request
from urllib import error
from socket import timeout
from bs4 import BeautifulSoup

from .exception import APIClientException

class APIClient:
    @classmethod
    def get_soup(cls, url, timeout_seconds=10):
        try:
            f = request.urlopen(url, timeout=timeout_seconds)
            html = f.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
        except Exception:
            raise APIClientException('Failed to fetch soup.')
        else:
            if soup.find('p', class_='leadNoData'):
                raise APIClientException('No data in the soup')
            return soup