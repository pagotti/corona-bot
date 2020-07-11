# -*- coding: utf-8 -*-

import copy
import json
import re

from dateutil import parser
from datetime import datetime

from dasbot.corona import CoronaData, http_get, case_less_eq


_raw_data = []


class BrasilIOData(CoronaData):

    @staticmethod
    def categories():
        return ["confirmed", "deaths"]

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "brasil.io"
        self._region = region if region else "BR"
        self._data = {}
        self._match_complete = re.findall(r"([A-zÀ-ú\s]+)[-:\s]*([A-Z]{2})", self._region)
        self._match_uf = re.findall(r"^[A-Z]{2}$", self._region)

    def get_data(self):
        return [self._data.get("confirmed", 0), self._data.get("deaths", 0), 0]

    def get_series(self):
        series = []
        if self._region != "BR":
            for case in self._raw_data:
                if self._match_region(case):
                    region_code = case.get("city_ibge_code", 0)
                    series = BrasilIOData.load_region_series(region_code)
                    break
        else:
            series = BrasilIOData.load_series()

        cases = {}
        for case in series:
            try:
                date = parser.parse(case["date"])
                if date <= datetime.today():
                    cases[date] = cases.get(date, 0) + (case.get("confirmed", 0) or 0)
            except ValueError:
                pass

        result = {}
        dates = [k for k in cases.keys()]
        dates.sort()
        for d in dates:
            result[d] = [cases.get(d, 0), 0, 0]

        return result

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
            self._last_date = parser.parse(self._raw_data[0]["date"])

    def _load_data(self):
        if not _raw_data:
            BrasilIOData.load()
        self._raw_data = copy.deepcopy(_raw_data)
        if self._raw_data:
            return True
        return False

    @staticmethod
    def load_region_series(region_code):
        result_data = []
        next_page = "https://brasil.io/api/dataset/covid19/caso/data?city_ibge_code={}".format(region_code)
        while next_page:
            response = http_get(next_page)
            if response:
                data = json.loads(response.read())
                result_data.extend(data["results"])
                next_page = data.get("next")
            else:
                break
        return result_data

    @staticmethod
    def load_series():
        result_data = []
        next_page = "https://brasil.io/api/dataset/covid19/caso/data?place_type=state"
        while next_page:
            response = http_get(next_page)
            if response:
                data = json.loads(response.read())
                result_data.extend(data["results"])
                next_page = data.get("next")
            else:
                break
        return result_data

    @staticmethod
    def load():
        global _raw_data
        raw_data = []
        next_page = "https://brasil.io/api/dataset/covid19/caso/data?is_last=True"
        while next_page:
            response = http_get(next_page)
            if response:
                data = json.loads(response.read())
                raw_data.extend(data["results"])
                next_page = data.get("next")
            else:
                break
        _raw_data = raw_data
