"""
Modulo corona
Pega dados do site: http://plataforma.saude.gov.br/novocoronavirus

"""

import json
import re
import pytz
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from datetime import datetime
from dateutil import parser
from urllib.request import urlopen, Request
from urllib.error import URLError
from bs4 import BeautifulSoup
from PIL import Image


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


def _http_get(url, expected=200):
    """return a request object from a url using http get
    """
    hdr = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8'}

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
        self._has_new_data = False
        if self._load_data():
            self._has_new_data = True
            self._update_stats()
        return self._has_new_data

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


class BingData(CoronaData):

    @staticmethod
    def categories(): return {
        "totalConfirmed": "Confirmados",
        "totalDeaths": "Mortes",
        "totalRecovered": "Recuperados"
    }

    def __init__(self):
        super().__init__()
        self._data_source = "Bing.com"
        self._region = "Brasil"

    def get_data(self):
        data_keys = ["totalConfirmed", "totalDeaths", "totalRecovered"]
        return [self._bing.get(k, 0) for k in data_keys]

    def _get_cases(self):
        cases = []
        for k, v in BingData.categories().items():
            cases.append("{}: *{:n}*".format(v, self._bing.get(k)))
        return ", ".join(cases)

    def _update_stats(self):
        self._last_date = datetime.fromtimestamp(self._version, pytz.timezone("America/Sao_Paulo"))
        self._bing = [k for k in self._raw_data["areas"] if k["id"] == "brazil"][0]

    def _load_data(self):
        response = _http_get("https://bing.com/covid/data")
        if response:
            data = json.loads(response.read())
            version = parser.parse(data["lastUpdated"]).timestamp()
            if version != self._version:
                self._version = version
                self._raw_data = data
                return True
            return False

        with open('bing_cases.json', 'r', encoding='utf-8') as f:
            self._raw_data = json.load(f)
        return self._last_date is None


class GovBR(CoronaData):

    @staticmethod
    def categories(): return {
        "cases": "Confirmados",
        "deaths": "Mortos",
        "suspects": "Suspeitos",
        "refuses": "Descartados",
    }

    def __init__(self):
        super().__init__()
        self._data_source = "Ministério da Saúde"
        self._region = "Brasil"
        self._br = {}
        self._uid = None

    def get_series(self):
        result = {}
        for item in self._raw_data["brazil"]:
            date = datetime.strptime("{}".format(item.get("date")), "%d/%m/%Y")
            br = {}
            for v in item.get("values"):
                if self._uid is None or v.get("uid") == self._uid:
                    for k in GovBR.categories():
                        br[k] = br.get(k, 0) + v.get(k, 0)
            result[date] = [br["cases"], br["deaths"], 0]
        return result

    def get_data(self):
        """Nos dados do ministério não tem numeros de recuperados"""
        return [self._br["cases"], self._br["deaths"], 0]

    def _get_cases(self):
        cases = []
        for k, v in GovBR.categories().items():
            cases.append("{}: *{:n}*".format(v, self._br.get(k, 0)))
        return ", ".join(cases)

    def _update_stats(self):
        """Nos dados do MS os valores corretos do brasil estão no último item somando todos os estados"""
        self._br = {}
        if self._raw_data:
            item = self._raw_data["brazil"][-1]
            self._last_date = datetime.strptime("{} {}".format(item.get("date"), item.get("time")), "%d/%m/%Y %H:%M")
            for v in item.get("values"):
                if self._uid is None or v.get("uid") == self._uid:
                    for k in GovBR.categories():
                        self._br[k] = self._br.get(k, 0) + v.get(k, 0)

    def _load_data(self):
        response = _http_get("http://plataforma.saude.gov.br/novocoronavirus")
        if response:
            main_page = BeautifulSoup(response, 'html.parser')
            script_tag = main_page.find(_database_script_matcher)
            if script_tag:
                script_url = script_tag['src']
                if script_url:
                    version = re.findall(r"[?]v=(\d+)", script_url)[0]
                    if version != self._version:
                        with _http_get(script_url) as f:
                            data = f.read().decode('utf-8')
                        p = re.compile(r"\{.+", re.MULTILINE)
                        data = json.loads(p.findall(data)[0])
                        self._raw_data = data
                        self._version = version
                        return True
                    return False

        with open('br_cases.json', 'r', encoding='utf-8') as f:
            self._raw_data = json.load(f)
        return self._last_date is None


class GovStates(GovBR):

    def __init__(self, state):
        super().__init__()
        self.state = br_ufs.get(state, None)
        if self.state:
            self._region = self.state.get("name")
            self._uid = int(self.state.get("uid"))


class SeriesChart(object):

    def __init__(self, corona_data: CoronaData):
        self.source = corona_data

    def image(self):
        categories = {
            0: "Confirmados",
            1: "Mortos",
            2: "Recuperados"
        }

        x_axis = []
        y_axis = {}
        for k in categories:
            y_axis[k] = []

        for date, values in self.source.get_series().items():
            x_axis.append(date)
            for k in categories:
                y_axis[k].append(values[k])

        fig = plt.figure(figsize=(10, 5))
        for k, v in categories.items():
            plt.plot(x_axis, y_axis[k], label=v)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))

        plt.xlabel('Data')
        plt.ylabel('Quantidade')
        plt.title("Contaminação pelo COVID-19 : {}".format(self.source.region))
        plt.legend()

        file = io.BytesIO()
        fig.savefig(file, bbox_inches='tight', dpi=150, format="png")
        image = Image.open(file)

        bio = io.BytesIO()
        bio.name = 'series.png'
        image.save(bio, 'PNG')
        bio.seek(0)
        return bio
