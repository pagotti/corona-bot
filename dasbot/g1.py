# -*- coding: utf-8 -*-

import copy
import json
import re
import pytz

from datetime import datetime
from dateutil import parser

from dasbot.corona import CoronaData, http_get, case_less_eq


_g1_data = {}


class G1Data(CoronaData):

    @staticmethod
    def categories(): return {
        "cases": "🦠 Confirmados"
    }

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "G1"
        self._region = region if region else "BR"
        self._data = None
        self._match_complete = re.findall(r"([A-zÀ-ú\s]+)[-:\s]*([A-Z]{2})", self._region)
        self._match_uf = re.findall(r"^[A-Z]{2}$", self._region)

    def _match_region(self, city, state):
        if self._region == "BR":
            return True
        elif self._match_uf:
            return state == self._match_uf[0]
        elif self._match_complete:
            return state == self._match_complete[0][1] and case_less_eq(city, self._match_complete[0][0].strip())
        else:
            return case_less_eq(city,  self._region)

    def get_data(self):
        return [self._data.get("cases", 0) or 0, 0, 0]

    def get_series(self):
        cases = {}
        for case in self._raw_data["docs"]:
            if self._match_region(case["city_name"], case["state"]):
                try:
                    date = datetime.strptime("{}".format(case.get("date")), "%Y-%m-%d")
                    if date <= datetime.today():
                        cases[date] = cases.get(date, 0) + case.get("cases", 0)
                except ValueError:
                    pass

        dates = [k for k in cases.keys()]
        dates.sort()
        result = {}
        acc = 0
        for d in dates:
            acc = cases.get(d, 0) + acc
            result[d] = [acc, 0, 0]

        return result

    def _update_stats(self):
        self._data = {}
        for case in [k for k in self._raw_data["docs"]]:
            if self._match_region(case["city_name"], case["state"]):
                for k in G1Data.categories():
                    self._data[k] = self._data.get(k, 0) + case.get(k, 0)
        self._last_date = datetime.fromtimestamp(self._version, pytz.timezone("America/Sao_Paulo")) \
            if self._data else None

    def _load_data(self):
        if not _g1_data:
            G1Data().load()
        data = copy.deepcopy(_g1_data)
        if data:
            date = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4}), às (\d{1,2}:\d{1,2})", data["updated_at"])[0]
            self._version = parser.parse("{}-{}-{}T{}:00-0300".format(date[2], date[1], date[0], date[3])).timestamp()
            self._raw_data = data
            return True
        return False

    @staticmethod
    def load():
        global _g1_data
        url = "https://s3.glbimg.com/v1/AUTH_f4000752a75040fdb48c79179f03325f/public/coronavirus/brazil-cases.json"
        response = http_get(url)
        if response:
            _g1_data = json.loads(response.read())
