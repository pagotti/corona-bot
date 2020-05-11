# -*- coding: utf-8 -*-

"""
Modulo corona
Classes que fornecem dados sobre o corona virus

"""

import io
import unicodedata
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from matplotlib.ticker import MaxNLocator
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError
from PIL import Image, ImageDraw, ImageFont


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
    if isinstance(text, str):
        return unicodedata.normalize("NFKD", text.casefold())
    else:
        return None


def case_less_eq(left, right):
    return _normalize_case(left) == _normalize_case(right)


def http_get(url, headers={}, expected=200):
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
        return self.get_description()

    def get_description(self, changes=None):
        if self._last_date:
            categories = {
                0: "🦠 Confirmados",
                1: "💀 Óbitos",
                2: "🙂 Recuperados"
            }
            data = self.get_data()
            cases = []
            for k, v in categories.items():
                if data[k]:
                    description = "{}: *{:d}*".format(v, data[k])
                    if changes and changes[k] > 0:
                        description = "{} 🔺 +{:d}".format(description, changes[k])
                    cases.append(description)
            if data[0] > 0 and data[1] > 0:
                death_rate = data[1] / data[0]
                cases.append("📈 Letalidade: *{:2.1%}*".format(death_rate))
            result = "{} em {}\n{}\n".format(self.data_source,
                                             self.last_date.strftime("%d-%m-%Y %H:%M"),
                                             "\n".join(cases))
        else:
            result = "Fonte: {} - Não há dados disponíveis\n".format(self.region, self.data_source)
        return result

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


class DataPanel(object):

    def __init__(self, *args):
        self._series = args
        self._font = ImageFont.truetype('res/RobotoMono-Bold.ttf', size=18)
        self._font_lg = ImageFont.truetype('res/RobotoMono-Bold.ttf', size=24)
        self._font_sm = ImageFont.truetype('res/RobotoMono-Bold.ttf', size=14)

    def _draw_header(self, draw):
        header = ["{:^10}".format(h) for h in ["Confirmados", "Mortes", "Recuperados"]]
        header.insert(0, "{:16}".format("Fonte"))
        draw.text((70, 100), "".join(header), fill="rgb(49,0,196)", font=self._font_lg)

    def _draw_data(self, draw, corona, row):
        draw.text((70, 165 + 72 * row), "{:20}".format(corona.data_source), fill="rgb(0,0,0)", font=self._font)
        data = corona.get_data()
        values = ["{:^10}".format("{:d}".format(v)) for v in data]
        draw.text((310, 160 + 72 * row), "".join(values), fill="rgb(0,0,0)", font=self._font_lg)
        text = "{}".format(datetime.strftime(corona.last_date, "%d-%m-%Y %H:%M"))
        if data[0] and data[1]:
            death_rate = (data[1] or 0) / data[0]
            text = "{} - Letalidade: {:2.1%}".format(text, death_rate)
        draw.text((70, 200 + 72 * row), text, fill="rgb(0,0,0)", font=self._font_sm)

    def _draw_region(self, draw, region):
        draw.text((70, 480), "Região: {}".format(region), fill="rgb(0,0,0)", font=self._font_lg)

    def image(self):
        image = Image.open('res/panel.png')
        draw = ImageDraw.Draw(image)
        self._draw_header(draw)
        for i, corona in enumerate(self._series):
            if i == 0:
                self._draw_region(draw, corona.region)
            self._draw_data(draw, corona, i)

        bio = io.BytesIO()
        bio.name = 'series.png'
        image.save(bio, 'PNG')
        bio.seek(0)
        return bio


