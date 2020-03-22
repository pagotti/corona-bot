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
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from PIL import Image

_br_ufs = {
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


def _http_get(url):
    """return a request object from a url using http get
    """
    hdr = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}

    req = Request(url, headers=hdr)
    return urlopen(req)


def _database_script_matcher(tag):
    """tag filter for match database.js
    """
    return tag.name == 'script' and \
           tag.parent.name == 'body' and \
           tag.has_attr('src') and \
           tag['src'].startswith('http://plataforma.saude.gov.br/novocoronavirus/resources/scripts/database.js')


class BrazilData(object):
    def __init__(self, data):
        self._data = data

    def _total(self, key):
        total = [v.get(key, 0) for k, v in self._data.items()]
        return sum(total)

    @property
    def confirmed(self):
        return self._total("cases")

    @property
    def suspect(self):
        return self._total("suspects")

    @property
    def refused(self):
        return self._total("refuses")

    @property
    def death(self):
        return self._total("deaths")


class BrazilStatesData(BrazilData):

    def __init__(self, data, state):
        super().__init__(data)
        value = _br_ufs.get(state, None)
        self.uid = value.get("uid") if value else None

    def _total(self, key):
        if self.uid:
            return self._data.get(self.uid).get(key, 0)
        return 0


class BrazilChart(object):

    def __init__(self, data):
        self.data = data

    def image(self):
        x_axis = []
        y_axis = {}

        for k in CoronaData.categories():
            y_axis[k] = []
        for date in self.data:
            x_axis.append(date)
            for k in CoronaData.categories():
                y_axis[k].append(sum([s.get(k, 0) for s in self.data[date]]))

        fig = plt.figure(figsize=(10, 5))
        plt.plot(x_axis, y_axis["suspects"], label="Suspeitos")
        plt.plot(x_axis, y_axis["refuses"], label="Descartados")
        plt.plot(x_axis, y_axis["cases"], label="Confirmados")
        plt.plot(x_axis, y_axis["deaths"], label="Mortes")
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))

        plt.xlabel('Data')
        plt.ylabel('Quantidade')
        plt.title('Contaminação pelo COVID-19')
        plt.legend()

        file = io.BytesIO()
        fig.savefig(file, bbox_inches='tight', dpi=150, format="png")
        image = Image.open(file)

        bio = io.BytesIO()
        bio.name = 'series.png'
        image.save(bio, 'PNG')
        bio.seek(0)
        return bio


class CoronaData(object):

    @staticmethod
    def categories(): return ["suspects", "refuses", "cases", "deaths"]

    def __init__(self):
        self.url = "http://plataforma.saude.gov.br/novocoronavirus"
        self._raw_data = {"world": [], "brazil": []}
        self._br = {}
        self._version = 0
        self._has_new_data = True
        self._last_br_date = None
        self.refresh()

    @property
    def version(self):
        ms = float(self._version)
        time = datetime.fromtimestamp(ms, pytz.timezone("America/Sao_Paulo"))
        return time.strftime("%d-%m-%Y %H:%M")

    @property
    def last_br_date(self):
        if self._last_br_date:
            return self._last_br_date.strftime("%d-%m-%Y %H:%M")
        else:
            return None

    @property
    def brazil(self):
        return self._br

    def world(self):
        pass

    def brazil_series(self):
        result = {}
        data = self._raw_data.get('brazil')
        for item in data:
            date = datetime.strptime("{}".format(item.get("date")), "%d/%m/%Y")
            result[date] = []
            for v in item.get("values"):
                uf = {"uid": v.get("uid")}
                for k in CoronaData.categories():
                    uf[k] = v.get(k, 0)
                result[date].append(uf)
        return result

    def refresh(self):
        self._load_data()
        if self._has_new_data:
            self._br = {v.get("uid"): dict() for k, v in _br_ufs.items()}
            self._update_stats_br()
            return True
        return True

    def _update_stats_br(self):
        items = self._raw_data.get('brazil')
        if items:
            item = items[-1]
            self._last_br_date = datetime.strptime("{} {}".format(item.get("date"), item.get("time")), "%d/%m/%Y %H:%M")
            for v in item.get("values"):
                uf = self._br.get(str(v.get("uid")))
                for k in CoronaData.categories():
                    uf[k] = uf.get(k, 0) + v.get(k, 0)

    def _load_data(self):
        """ get corona virus data from BR gov site
        and return as object
        """
        main_page = BeautifulSoup(_http_get(self.url), 'html.parser')
        script_tag = main_page.find(_database_script_matcher)
        if script_tag:
            script_url = script_tag['src']
            if script_url:
                version = re.findall(r"[?]v=(\d+)", script_url)[0]
                if version != self._version:
                    with _http_get(script_url) as f:
                        data = f.read().decode('utf-8')
                    p = re.compile(r"\{.+", re.MULTILINE)
                    self._raw_data = json.loads(p.findall(data)[0])
                    self._version = version
                    self._has_new_data = True
        else:
            with open('casos.json', 'r', encoding='utf-8') as f:
                self._raw_data = json.load(f)
