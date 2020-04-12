# -*- coding: utf-8 -*-

import copy
import json
import re
import pytz

from dateutil import parser

from dasbot.corona import CoronaData, http_get, case_less_eq


_raw_data = {}


class BrasilIOData(CoronaData):

    @staticmethod
    def categories():
        return {
            "confirmed": "🦠 Confirmados",
            "deaths": "💀 Óbitos"
        }

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "brasil.io"
        self._region = region if region else "BR"
        self._data = {}
        self._match_complete = re.findall(r"([A-zÀ-ú\s]+)[-:\s]*([A-Z]{2})", self._region)
        self._match_uf = re.findall(r"^[A-Z]{2}$", self._region)

    def get_data(self):
        return [self._data.get("confirmed", 0), self._data.get("deaths", 0), 0]

    def _match_region(self, rec):
        if self._region == "BR":
            return rec["city"] is None
        elif self._match_uf:
            return rec["city"] is None and rec["state"] == self._match_uf[0]
        elif self._match_complete:
            return rec["state"] == self._match_complete[0][1] and \
                   case_less_eq(rec["city"], self._match_complete[0][0].strip())
        else:
            return rec["place_type"] == "city" and case_less_eq(rec["city"], self._region)

    def _update_stats(self):
        self._data = {}
        for case in self._raw_data:
            if self._match_region(case):
                for k in BrasilIOData.categories():
                    self._data[k] = case.get(k, 0) + self._data.get(k, 0)
        if self._data:
            date = parser.parse(self._raw_data[0]["date"])
            self._last_date = date.astimezone(pytz.timezone("America/Sao_Paulo"))

    def _load_data(self):
        if not _raw_data:
            BrasilIOData.load()
        self._raw_data = copy.deepcopy(_raw_data)
        if self._raw_data:
            return True
        return False

    @staticmethod
    def load():
        global _raw_data
        response = http_get("https://brasil.io/api/dataset/covid19/caso/data?is_last=true")
        if response:
            data = json.loads(response.read())
            _raw_data = data["results"]
