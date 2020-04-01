"""
Modulo corona
Classes que fornecem dados sobre o corona virus

"""

import copy
import json
import re
import pytz
import io
import unicodedata
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from matplotlib.ticker import MaxNLocator
from datetime import datetime
from dateutil import parser
from urllib.request import urlopen, Request
from urllib.error import URLError
from PIL import Image
from bs4 import BeautifulSoup


br_ufs = {
 'RO': {'uid': '11', 'name': 'Rondônia'},
 'AC': {'uid': '12', 'name': 'Acre'},
 'AM': {'uid': '13', 'name': 'Amazonas'},
 'RR': {'uid': '14', 'name': 'Roraima'},
 'PA': {'uid': '15', 'name': 'Pará'},
 'AP': {'uid': '16', 'name': 'Amapá'},
 'TO': {'uid': '17', 'name': 'Tocantins'},
 'MA': {'uid': '21', 'name': 'Maranhão'},
 'PI': {'uid': '22', 'name': 'Piauí'},
 'CE': {'uid': '23', 'name': 'Ceará'},
 'RN': {'uid': '24', 'name': 'Rio Grande do Norte'},
 'PB': {'uid': '25', 'name': 'Paraíba'},
 'PE': {'uid': '26', 'name': 'Pernambuco'},
 'AL': {'uid': '27', 'name': 'Alagoas'},
 'SE': {'uid': '28', 'name': 'Sergipe'},
 'BA': {'uid': '29', 'name': 'Bahia'},
 'MG': {'uid': '31', 'name': 'Minas Gerais'},
 'ES': {'uid': '32', 'name': 'Espírito Santo'},
 'RJ': {'uid': '33', 'name': 'Rio de Janeiro'},
 'SP': {'uid': '35', 'name': 'São Paulo'},
 'PR': {'uid': '41', 'name': 'Paraná'},
 'SC': {'uid': '42', 'name': 'Santa Catarina'},
 'RS': {'uid': '43', 'name': 'Rio Grande do Sul'},
 'MS': {'uid': '50', 'name': 'Mato Grosso do Sul'},
 'MT': {'uid': '51', 'name': 'Mato Grosso'},
 'GO': {'uid': '52', 'name': 'Goiás'},
 'DF': {'uid': '53', 'name': 'Distrito Federal'}
}


def _normalize_case(text):
    return unicodedata.normalize("NFKD", text.casefold())


def case_less_eq(left, right):
    return _normalize_case(left) == _normalize_case(right)


def _http_get(url, headers={}, expected=200):
    """return a request object from a url using http get
    """
    hdr = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8'}
    hdr.update(headers)

    try:
        req = Request(url, headers=hdr)
        response = urlopen(req)
        return response if response.getcode() == expected else None
    except URLError:
        return None


def _database_script_matcher(tag):
    """tag filter for match database.js
    """
    return tag.name == 'script' and \
           tag.parent.name == 'body' and \
           tag.has_attr('src') and \
           tag['src'].startswith('http://plataforma.saude.gov.br/novocoronavirus/resources/scripts/database.js')


class CoronaData(object):

    def __init__(self):
        self._raw_data = {}
        self._version = 0
        self._has_new_data = False
        self._last_date = None
        self._data_source = ""
        self._region = ""

    @property
    def data_source(self):
        return self._data_source

    @property
    def description(self):
        if self._last_date:
            return "{}: {} - Fonte: {} em {}".\
                format(self.region, self._get_cases(), self.data_source, self.last_date.strftime("%d-%m-%Y %H:%M"))
        else:
            return "{}: Fonte: {} - Não há dados disponíveis".format(self.region, self.data_source)

    @property
    def last_date(self):
        return self._last_date

    @property
    def region(self):
        return self._region

    def refresh(self):
        if self._load_data():
            self._update_stats()

    def get_data(self):
        """Implementado na subclasse para retornar os dados em um array
        com os seguintes valores nessa ordem: [confirmados, mortes, recuperados]
        A data é informada pela propriedade last_date
        """
        return None

    def get_series(self):
        """Implementado na subclasse para retornar a series de dados padrão por data
        A serie é um dicionario com a chave sendo a data e o valor sendo um
        array no padrão do _get_data
        """
        return None

    def _get_cases(self):
        """Implementado na subclasse para retornar os dados da fonte"""
        return None

    def _update_stats(self):
        """processa os dados coletados"""
        pass

    def _load_data(self):
        """Carrega os dados e retorna True se houver uma nova versão disponível"""
        pass


_bing_data = {}


class BingData(CoronaData):

    @staticmethod
    def categories(): return {
        "totalConfirmed": "Confirmados",
        "totalDeaths": "Mortes",
        "totalRecovered": "Recuperados"
    }

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "Bing.com"
        self._region = region if region else "BR"

    def get_data(self):
        data_keys = ["totalConfirmed", "totalDeaths", "totalRecovered"]
        return [self._bing.get(k, 0) or 0 for k in data_keys]

    def _get_cases(self):
        cases = []
        for k, v in BingData.categories().items():
            cases.append("{}: *{:n}*".format(v, self._bing.get(k, 0) or 0))
        if (self._bing.get("totalConfirmed", 0) or 0) > 0:
            death_rate = (self._bing.get("totalDeaths", 0) or 0) / self._bing.get("totalConfirmed", 0)
            cases.append("Mortalidade: *{:2.1%}*".format(death_rate))
        return ", ".join(cases)

    def _update_stats(self):
        self._bing = [k for k in self._raw_data.get("areas") if k["id"] == "brazil"]
        if self._region != "BR" and self._bing:
            region = br_ufs.get(self._region)["name"] if self._region in br_ufs else self._region
            self._bing = [k for k in self._bing[0].get("areas") if case_less_eq(k["displayName"], region)]
        if self._bing:
            self._last_date = datetime.fromtimestamp(self._version, pytz.timezone("America/Sao_Paulo"))
            self._bing = self._bing[0]

    def _load_data(self):
        if not _bing_data:
            BingData.load()
        data = copy.deepcopy(_bing_data)
        if data:
            version = parser.parse(data["lastUpdated"]).timestamp()
            self._version = version
            self._raw_data = data
            return True
        return False

    @staticmethod
    def load():
        global _bing_data
        response = _http_get("https://bing.com/covid/data")
        if response:
            _bing_data = json.loads(response.read())


_g1_data = {}


class G1Data(CoronaData):

    @staticmethod
    def categories(): return {
        "cases": "Confirmados"
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
        cases = []
        for case in self._raw_data["docs"]:
            if self._match_region(case["city_name"], case["state"]):
                try:
                    date = datetime.strptime("{}".format(case.get("date")), "%Y-%m-%d")
                    acc = cases[-1]["cases"] if len(cases) > 0 else 0
                    if len(cases) > 0:
                        acc = cases[-1]["cases"]
                        if cases[-1]["date"] < date:
                            cases.append({"date": date, "cases": case.get("cases", 0) + acc})
                        else:
                            cases[-1]["cases"] = case.get("cases", 0) + acc
                    else:
                        cases.append({"date": date, "cases": case.get("cases", 0)})
                except ValueError:
                    pass

        return {c["date"]: [c["cases"], 0, 0] for c in cases}

    def _get_cases(self):
        cases = []
        for k, v in G1Data.categories().items():
            cases.append("{}: *{:n}*".format(v, self._data.get(k, 0) or 0))
        return ", ".join(cases)

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
        response = _http_get("https://especiais.g1.globo.com/bemestar/coronavirus/mapa-coronavirus/data/brazil-cases.json")
        if response:
            _g1_data = json.loads(response.read())


_gov_br_data = {}


class GovBR(CoronaData):

    @staticmethod
    def categories():
        return {
            "cases": "Confirmados",
            "deaths": "Mortos"
        }

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "Ministério da Saúde"
        self._region = region if region else "BR"
        self._gov = {}

    def get_data(self):
        """Nos dados do ministério não tem numeros de recuperados e para estados só tem confirmados"""
        return [self._gov["cases"], self._gov.get("deaths", 0), 0]

    def _get_cases(self):
        cases = []
        for k, v in GovBR.categories().items():
            if k in self._gov:
                cases.append("{}: *{:n}*".format(v, self._gov.get(k, 0)))
        if self._gov.get("cases", 0) > 0:
            death_rate = self._gov.get("deaths", 0) / self._gov.get("cases", 0)
            cases.append("Mortalidade: *{:2.1%}*".format(death_rate))
        return ", ".join(cases)

    def _update_stats(self):
        self._gov = {}
        if self._raw_data:
            region = br_ufs[self._region].get("name") if self._region in br_ufs else self._region
            if region == "BR":
                categories = {"cases": "total_confirmado", "deaths": "total_obitos"}
                item = self._raw_data["br"]
            else:
                categories = {"cases": "qtd_confirmado"}
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
        response = _http_get("https://xx9p7hp1p7.execute-api.us-east-1.amazonaws.com/prod/{}".format(path),
                             {"x-parse-application-id": app_id})
        if response:
            data = json.loads(response.read())
            _gov_br_data[key] = data["results"]

    @staticmethod
    def load():
        GovBR.load_json("PortalGeral", "br")
        GovBR.load_json("PortalMapa", "states")


_world_data = {}


class WorldOMeterData(CoronaData):

    @staticmethod
    def categories(): return {
        "cases": "Confirmados",
        "deaths": "Mortes",
        "recovery": "Recuperados"
    }

    def __init__(self, region=None):
        super().__init__()
        self._data_source = "World-o-meter"
        self._region = region if region else "BR"
        self._data = {}

    def get_data(self):
        return [self._data.get(k, 0) or 0 for k in WorldOMeterData.categories().keys()]

    def _get_cases(self):
        cases = []
        for k, v in WorldOMeterData.categories().items():
            if k in self._data:
                cases.append("{}: *{:n}*".format(v, self._data.get(k, 0)))
        if self._data.get("cases", 0) > 0:
            death_rate = self._data.get("deaths", 0) / self._data.get("cases", 0)
            cases.append("Mortalidade: *{:2.1%}*".format(death_rate))
        return ", ".join(cases)

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
        response = _http_get("https://www.worldometers.info/coronavirus/")
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


class SeriesChart(object):

    def __init__(self, *args):
        self.series = []
        self.regions = []
        self.source = args[0].data_source
        for corona in args:
            self.series.append(corona.get_series())
            self.regions.append(corona.region)

    def validate(self):
        for series in self.series:
            if not series:
                return False
        return True

    def image(self):
        x_axis = []
        y_axis = {}

        fig = plt.figure(figsize=(10, 5))

        if len(self.series) == 1:
            categories = {
                0: "Confirmados"
                # 1: "Mortos",
                # 2: "Recuperados"
            }
            for k in categories:
                y_axis[k] = []
            series = self.series[0]
            for date, values in series.items():
                x_axis.append(date)
                for k in categories:
                    y_axis[k].append(values[k])
            for k, v in categories.items():
                plt.plot(x_axis, y_axis[k], label=v)
            plt.title("Contaminação pelo COVID-19 : {} - Fonte: {}".format(self.regions[0], self.source))
        else:
            dates = {}
            for i, series in enumerate(self.series):
                y_axis[i] = []
                for date in series:
                    dates[date] = None
            x_axis = [k for k in dates.keys()]
            x_axis.sort()
            for i, series in enumerate(self.series):
                for date in x_axis:
                    if date in series:
                        y_axis[i].append(series[date][0])
                    else:
                        if len(y_axis[i]) > 0:
                            y_axis[i].append(y_axis[i][-1])
                        else:
                            y_axis[i].append(0)
                plt.plot(x_axis, y_axis[i], label=self.regions[i])
            plt.title("Contaminação pelo COVID-19 : Confirmados - Fonte: {}".format(self.source))

        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        plt.xlabel('Data')
        plt.ylabel('Quantidade')
        plt.legend()

        file = io.BytesIO()
        fig.savefig(file, bbox_inches='tight', dpi=150, format="png")
        image = Image.open(file)

        bio = io.BytesIO()
        bio.name = 'series.png'
        image.save(bio, 'PNG')
        bio.seek(0)
        return bio
