# -*- coding: utf-8 -*-

import copy
import json
import pytz

from dateutil import parser

from dasbot.corona import CoronaData, http_get, br_ufs


_gov_br_data = {}


class GovBR(CoronaData):

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "Ministério da Saúde"
        self._region = region if region else "BR"
        self._gov = {}

    def get_data(self):
        """Nos dados do ministério não tem numeros de recuperados e para estados só tem confirmados"""
        return [self._gov.get("cases", 0), self._gov.get("deaths", 0), self._gov.get("recovered", 0)]

    def _update_stats(self):
        self._gov = {}
        if self._raw_data:
            date = parser.parse(self._raw_data["br"].get("dt_updated"))
            self._last_date = date.astimezone(pytz.timezone("America/Sao_Paulo"))
            region = self._region
            if region == "BR":
                item = self._raw_data["br"]
                self._gov["cases"] = int(item.get("confirmados").get("total", "0"))
                self._gov["recovered"] = int(item.get("confirmados").get("recuperados", "0"))
                self._gov["deaths"] = int(item.get("obitos").get("total", "0"))
            else:
                categories = {"cases": "casosAcumulado", "deaths": "obitosAcumulado"}
                item = [k for k in self._raw_data["states"] if k.get("nome") == region]
                if item and len(item) == 1:
                    for k in categories:
                        self._gov[k] = item[0].get(categories[k], 0)
                else:
                    self._last_date = None

    def _load_data(self):
        if not _gov_br_data:
            GovBR.load()
        self._raw_data = copy.deepcopy(_gov_br_data)
        if self._raw_data:
            return True
        return False

    @staticmethod
    def load_json(path):
        # esse é o id atual, mas pode mudar com o tempo
        app_id = "unAFkcaNDeXajurGB7LChj8SgQYS2ptm"
        response = http_get("https://xx9p7hp1p7.execute-api.us-east-1.amazonaws.com/prod/{}".format(path),
                             {"x-parse-application-id": app_id})
        if response:
            return json.loads(response.read())

    @staticmethod
    def load():
        global _gov_br_data
        data = GovBR.load_json("PortalGeralApi")
        _gov_br_data["br"] = data
        data = GovBR.load_json("PortalEstado")
        _gov_br_data["states"] = data

