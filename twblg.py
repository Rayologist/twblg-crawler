import requests
from bs4 import BeautifulSoup
from collections import namedtuple
from typing import NamedTuple, Dict
from urllib import parse as urllib_parse
import re


class Soup:
    def __init__(self, url: str) -> None:
        self._response = requests.get(url, headers=self.headers)
        if self._response.status_code != 200:
            raise TimeoutError("Error status code: {self._response.status_codes}")

    @property
    def headers(self) -> Dict[str:str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
        }

    @property
    def soup(self) -> BeautifulSoup:
        return BeautifulSoup(self._response.text, "html.parser")


class WordContents:
    def __init__(self, url: str) -> None:
        self._soup = Soup(url).soup

    @property
    def _Word(self) -> NamedTuple:
        return namedtuple("Word", ["tone", "word", "pronunciation", "meaning"])

    def get_contents(self):
        tone = self._soup.find(href=re.compile(".*?shengdiao")).string.strip()
        word = self._soup.table.find(itemprop="name").string.strip()
        pronunciation = self._soup.table.find("font", class_="tlsound").string.strip()
        meaning = self._soup.table.find(itemprop="description")
        if not meaning:
            return self._Word(tone, word, pronunciation, None)
        meaning = meaning.get_text().strip()
        return self._Word(tone, word, pronunciation, meaning)


class ATag:
    def __init__(self, url):
        self._soup = Soup(url).soup

    @property
    def a_tag_list(self):
        return self._soup.table.find_all("a")


class Pages:
    _parent_url = "https://twblg.dict.edu.tw/holodict_new/"

    def __init__(self, url):
        self._soup = Soup(url).soup
        self._current_a_tag_list = self._soup.table.find_all("a")
        self._pages = self._soup.find_all(href=re.compile(r"result_page\.jsp"))
        self._get_page_a_tag()

    @property
    def _page_urls(self):
        if self._pages:
            for page in self._pages:
                if re.findall(r"\d+", page.string):
                    yield urllib_parse.urljoin(self._parent_url, page["href"])

    def _get_page_a_tag(self):
        for url in self._page_urls:
            self._current_a_tag_list += ATag(url).a_tag_list

    @property
    def a_tag_list(self):
        return self._current_a_tag_list


class WordList:
    _parent_url = "https://twblg.dict.edu.tw/holodict_new/"

    def __init__(self, url: str, length_limit: int = 2):
        self._a_tag_list = Pages(url).a_tag_list
        self._length_limit = length_limit

    def _get_a_tag_value(self, a_tag):
        word = a_tag.string
        url = urllib_parse.urljoin(self._parent_url, a_tag["href"])
        return word, url

    def __iter__(self):
        result = map(self._get_a_tag_value, self._a_tag_list)
        for word, url in result:
            print(word, end="")
            if len(word) == self._length_limit:
                print(f"\tFetched")
                yield WordContents(url).get_contents()
            else:
                print("\tSkipped")


class ShengmuIndex:
    def __init__(self, url):
        self._url = url
        self._soup = Soup(url).soup

    @property
    def _raw_html_list(self):
        return self._soup.table.find_all(href=re.compile("\.\./result\.jsp"))

    def __iter__(self):
        urls = map(
            lambda x: urllib_parse.urljoin(self._url, x["href"]), self._raw_html_list
        )
        for url in urls:
            yield url


if __name__ == "__main__":
    from functools import reduce
    import operator
    import pandas as pd

    shengmu = ShengmuIndex(
        "https://twblg.dict.edu.tw/holodict_new/index/shengmu_level4.jsp?shengmu=b&yunmu=0&shengdiao=0&in_idx=0"
    )
    res = map(lambda x: [*WordList(x)], shengmu)
    pd.DataFrame(reduce(operator.add, res, [])).to_excel("b_shengmu.xlsx", index=False)
