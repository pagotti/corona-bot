# -*- coding: utf-8 -*-

import copy
import re
import pytz

from datetime import datetime
from dateutil import parser
from bs4 import BeautifulSoup

from dasbot.corona import CoronaData, http_get


_world_data = {}


class WorldOMeterData(CoronaData):

    @staticmethod
    def categories(): return {
        "cases": "🦠 Confirmados",
        "deaths": "💀 Óbitos",
        "recovery": "🙂 Recuperados"
    }

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "World-o-meter"
        self._region = region if region else "BR"
        self._data = {}

    def get_data(self):
        return [self._data.get(k, 0) or 0 for k in WorldOMeterData.categories().keys()]

    def _update_stats(self):
        if self._region == "BR":
            for k in WorldOMeterData.categories():
                self._data[k] = int(self._raw_data[k].replace(",", ""))
            self._version = parser.parse(self._raw_data["lastUpdated"]).timestamp()
            self._last_date = datetime.fromtimestamp(self._version, pytz.timezone("America/Sao_Paulo"))

    def _load_data(self):
        if not _world_data:
            WorldOMeterData.load()
        self._raw_data = copy.deepcopy(_world_data)
        if self._raw_data:
            return True
        return False

    @staticmethod
    def _last_update_matcher(tag):
        return tag.name == 'div' and \
               tag.text.startswith("Last updated")

    @staticmethod
    def _brazil_matcher(tag):
        return tag.name == 'a' and \
               tag.has_attr('href') and \
               tag['href'] == 'country/brazil/'

    @staticmethod
    def load():
        global _world_data
        response = http_get("https://www.worldometers.info/coronavirus/")
        if response:
            main_page = BeautifulSoup(response, 'html.parser')
            last_date_tag = main_page.find(WorldOMeterData._last_update_matcher)
            if last_date_tag:
                match = re.findall(r"(\w+\s\d+,\s\d+,\s\d+:\d+\sGMT)$", last_date_tag.text)
                if match:
                    _world_data["lastUpdated"] = match[0]
            data_tag = main_page.find(WorldOMeterData._brazil_matcher)
            cols = []
            for el in data_tag.parent.find_next_siblings("td"):
                cols.append(el.text)
            if cols:
                _world_data["cases"] = cols[0]
                _world_data["deaths"] = cols[2]
                _world_data["recovery"] = cols[4]
