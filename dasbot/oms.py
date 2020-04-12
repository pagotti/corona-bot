# -*- coding: utf-8 -*-

import copy
import json
import pytz

from datetime import datetime
from gzip import decompress

from dasbot.corona import CoronaData, http_get


_oms_data = {}


class OMSData(CoronaData):

    @staticmethod
    def categories():
        return {
            "cases": "🦠 Confirmados",
            "deaths": "💀 Óbitos"
        }

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "OMS"
        self._region = region if region else "BR"
        self._oms = {}

    def get_data(self):
        return [self._oms.get("cases", 0), self._oms.get("deaths", 0), 0]

    def get_series(self):
        cases = {}
        if self._raw_data and self._region == "BR":
            for data in self._raw_data:
                date = datetime.fromtimestamp(data[0] / 1000).astimezone(pytz.timezone("America/Sao_Paulo")).date()
                if date <= datetime.today():
                    cases[date] = {"c": data[6], "d": data[4]}

        dates = [k for k in cases.keys()]
        dates.sort()
        result = {}
        for d in dates:
            result[d] = [cases[d].get("c", 0), cases[d].get("d", 0), 0]

        return result

    def _update_stats(self):
        self._oms = {}
        if self._raw_data and self._region == "BR":
            categories = {"cases": 6, "deaths": 4}
            for k, v in categories.items():
                self._oms[k] = self._raw_data[-1][v]
            date = datetime.fromtimestamp(self._raw_data[-1][0] / 1000)
            self._last_date = date.astimezone(pytz.timezone("America/Sao_Paulo"))
        else:
            self._last_date = None

    def _load_data(self):
        if not _oms_data:
            OMSData.load()
        self._raw_data = copy.deepcopy(_oms_data)
        if self._raw_data:
            return True
        return False

    @staticmethod
    def load():
        global _oms_data
        response = http_get("https://dashboards-dev.sprinklr.com/data/9043/global-covid19-who-gis.json",
                             {"Accept-Encoding": "gzip"})
        if response:
            response_data = decompress(response.read())
            data = json.loads(response_data.decode("utf-8"))
            _oms_data = [d for d in data["rows"] if d[1] == "BR"]
