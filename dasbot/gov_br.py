# -*- coding: utf-8 -*-

import copy
import json
import pytz

from dateutil import parser

from dasbot.corona import CoronaData, http_get, br_ufs


_gov_br_data = {}


class GovBR(CoronaData):

    @staticmethod
    def categories():
        return {
            "cases": "🦠 Confirmados",
            "deaths": "💀 Óbitos"
        }

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "Ministério da Saúde"
        self._region = region if region else "BR"
        self._gov = {}

    def get_data(self):
        """Nos dados do ministério não tem numeros de recuperados e para estados só tem confirmados"""
        return [self._gov["cases"], self._gov.get("deaths", 0), 0]

    def _update_stats(self):
        self._gov = {}
        if self._raw_data:
            region = br_ufs[self._region].get("name") if self._region in br_ufs else self._region
            if region == "BR":
                categories = {"cases": "total_confirmado", "deaths": "total_obitos"}
                item = self._raw_data["br"]
            else:
                categories = {"cases": "qtd_confirmado", "deaths": "qtd_obito"}
                item = [k for k in self._raw_data["states"] if k.get("nome") == region]

            if item and len(item) == 1:
                for k in GovBR.categories():
                    if k in categories:
                        value = str(item[0].get(categories[k], "0"))
                        self._gov[k] = int(value.replace(".", ""))
                date = parser.parse(item[0].get("updatedAt"))
                self._last_date = date.astimezone(pytz.timezone("America/Sao_Paulo"))
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
    def load_json(path, key):
        global _gov_br_data
        # esse é o id atual, mas pode mudar com o tempo
        app_id = "unAFkcaNDeXajurGB7LChj8SgQYS2ptm"
        response = http_get("https://xx9p7hp1p7.execute-api.us-east-1.amazonaws.com/prod/{}".format(path),
                             {"x-parse-application-id": app_id})
        if response:
            data = json.loads(response.read())
            _gov_br_data[key] = data["results"]

    @staticmethod
    def load():
        GovBR.load_json("PortalGeral", "br")
        GovBR.load_json("PortalMapa", "states")
