# -*- coding: utf-8 -*-

"""
Modulo bot - Mantem as funções que gerenciam o bot
"""


import os
import logging
import pickle
import datetime
import re
import json

from uuid import uuid4
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode

from dasbot.corona import G1Data, BingData, GovBR, WorldOMeterData, SeriesChart
from dasbot.db import JobCacheRepo, BotLogRepo, CasesRepo


# Enable logging
logger = logging.getLogger(__name__)

use_db = os.environ.get("USE_DB", False)
# futuros comandos administrativos
admin_id = int(os.environ.get("ADMIN_ID", 0))
# ajuste para o nome do canal a receber as atualizações
channel_id = os.environ.get("CHANNEL_ID", "")

if use_db:
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        filemode="a",
                        filename="logs/log_{}.log".format(
                            datetime.datetime.strftime(datetime.datetime.now(), "%Y_%m_%d")),
                        level=logging.INFO)


def _log_message_data(message):
    result = dict()
    result["date"] = message["date"].isoformat()
    result["chat_id"] = message["chat"]["id"]
    result["username"] = message["chat"]["username"] or message["chat"]["last_name"] or message["chat"]["first_name"]
    result["text"] = message["text"]
    return json.dumps(result).replace("\"", "\'")


class JobsInfo(object):
    def __init__(self, file_name):
        self._jobs = dict()
        self.file_name = file_name
        self._props = ["interval", "repeat", "context"]

    @property
    def jobs(self):
        return self._jobs

    def save(self):
        with open(self.file_name, 'wb') as f:
            data = {key: {var: getattr(job, var) for var in self._props} for key, job in self._jobs.items()}
            pickle.dump(data, f)

    def load(self):
        if os.path.exists(self.file_name):
            with open(self.file_name, 'rb') as f:
                return pickle.load(f)
        return {}

    def push(self, key, data):
        self._jobs[key] = data

    def pop(self, key):
        result = self._jobs[key]
        del self._jobs[key]
        return result

    def exists(self, key):
        return key in self._jobs


class JobsDBInfo(JobsInfo):
    def __init__(self):
        super().__init__("")

    def save(self):
        repo = JobCacheRepo()
        for key, job in self.jobs.items():
            data = dict()
            data["job_id"] = key
            for prop in ["interval", "repeat"]:
                data[prop] = getattr(job, prop)
            for prop in ["region", "chat_id", "new"]:
                data[prop] = job.context.get(prop)
            for prop, i in {"cases": 0, "deaths": 1, "recovery": 2}.items():
                data[prop] = job.context.get("last")[i]
            repo.add(data)
        repo.save()

    def load(self):
        jobs = dict()
        repo = JobCacheRepo()
        repo.load()
        for row in repo.rows:
            data = dict()
            data["interval"] = row["interval"]
            data["repeat"] = row["repeat"]
            data["context"] = {"region": row["region"],
                               "chat_id": row["chat_id"],
                               "new": row["new"],
                               "last": [row["cases"], row["deaths"], row["recovery"]]}
            jobs[row["job_id"]] = data
        return jobs


class DBLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()

    def emit(self, record):
        message = record.getMessage()
        command = re.findall(r'Arrive ([/\w]+) (?:command|message) "([^"]+)"', message)
        if command:
            command_string = command[0][1]
            args = json.loads(command_string.replace("\'", "\""))
            repo = BotLogRepo()
            data = dict()
            data["chat_id"] = args["chat_id"]
            data["username"] = args["username"]
            data["command"] = command[0][0]
            data["args"] = args["text"]
            repo.add(data)
            repo.save()


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("""Olá. Sou um bot de dados de casos de COVID-19 no Brasil.
    Digite /help para ver as opções""")


def help(update, context):
    """Send a message when the command /help is issued."""
    logger.info('Arrive /help command "%s"', _log_message_data(update.effective_message))
    update.message.reply_text("""Comandos que você pode enviar
    /start : inicia o bot
    /help : mostra a ajuda
    /stats : mostra os números de casos mais atualizados do Brasil
    /chart : desenha um gráfico com a região informada, ex: /chart SP
    /listen : observa os dados de uma região a cada X minutos (experimental)
    /mute : para de observar a região programada com o /listen
Envie uma sigla de estado ou nome de cidade, para saber os confirmados nessa região
Você pode invocar os dados pelo bot em outros chats:  
    inicie a mensagem lá com @corona_br_bot e a região na sequência""")


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def stats(update, context):
    logger.info('Arrive /stats command "%s"', _log_message_data(update.effective_message))
    sources = [G1Data(), BingData(), GovBR(), WorldOMeterData()]
    result = []
    for corona in sources:
        corona.refresh()
        if corona.last_date:
            result.append(corona.description)
    if result:
        update.message.reply_markdown("\n".join(result))
    else:
        update.message.reply_text("Dados não disponíveis. Tente mais tarde")


def general(update, context):
    logger.info('Arrive text message "%s"', _log_message_data(update.effective_message))
    region = update.message.text
    result = []
    sources = [G1Data(region), BingData(region), GovBR(region), WorldOMeterData(region)]
    for corona in sources:
        corona.refresh()
        if corona.last_date:
            result.append(corona.description)

    if result:
        update.message.reply_markdown("\n".join(result))
    else:
        update.message.reply_text("""Região não reconhecida ou sem dados. 
Envie a sigla do estado em maiúsculas, nomes de cidade com acentos. 
Envie /help para ver a ajuda.""")


def _get_chart(regions):
    sources = []
    if regions:
        for region in regions:
            corona = G1Data(region.strip())
            corona.refresh()
            sources.append(corona)

        chart_br = SeriesChart(*sources)
        if chart_br.validate():
            image = chart_br.image()
            caption = "Atualizado: {}".format(sources[0].last_date.strftime("%d-%m-%Y %H:%M"))
            return image, caption
    return None


def chart(update, context):
    logger.info('Arrive /chart command "%s"', _log_message_data(update.effective_message))
    regions = " ".join(context.args).split(",")
    chart_data = _get_chart(regions)
    if chart_data:
        update.message.reply_photo(photo=chart_data[0], caption=chart_data[1])
    else:
        update.message.reply_text("""A lista de regiões não foi reconhecida. 
Envie a sigla de estado em maiúsculas, nomes de cidade com acentos.
Exemplos: /chart SP, RJ - /chart São Paulo, Belo Horizonte 
Envie /help para ver a ajuda.""")


def inline_query(update, context):
    """Handle the inline query."""
    query = update.inline_query.query
    if not query:
        return

    logger.info('Query inline "%s"', update.inline_query)

    sources = [G1Data(query), BingData(query), GovBR(query), WorldOMeterData(query)]
    results = []

    for corona in sources:
        corona.refresh()
        if corona.last_date:
            results.append(InlineQueryResultArticle(
                id=uuid4(),
                title="{} por {} em {}".format(query, corona.data_source, corona.last_date.strftime("%d-%m")),
                input_message_content=InputTextMessageContent(
                    corona.description,
                    parse_mode=ParseMode.MARKDOWN)))

    update.inline_query.answer(results, cache_time=60)


def unknown(update, context):
    update.message.reply_text("Não entendi esse comando")


def on_change_notifier(context):
    region = context.job.context["region"]
    sources = [BingData(region)]
    for corona in sources:
        corona.refresh()
        if corona.last_date:
            last = context.job.context["last"]
            if not context.job.context.get("new", True):
                changes = True
            else:
                changes = [1 for i, j in zip(corona.get_data(), last) if i > j]
            if changes or not last:
                context.job.context["last"] = corona.get_data()
                context.bot.send_message(context.job.context["chat_id"], text=corona.description,
                                         parse_mode=ParseMode.MARKDOWN)


def refresh_data(context):
    BingData.load()
    G1Data.load()
    GovBR.load()
    WorldOMeterData.load()

    job_context = context.job.context

    # busca atualizações de dados nos data sources para informar no canal
    # e para guardar na tabela de casos, se o banco estiver ativo
    region = job_context["region"]
    sources = [G1Data(region), BingData(region), GovBR(region), WorldOMeterData(region)]
    for corona in sources:
        corona.refresh()
        if corona.last_date:
            corona_data = corona.get_data()
            if corona.data_source not in job_context:
                job_context[corona.data_source] = {"last": corona_data}
            else:
                last = job_context[corona.data_source]["last"]
                changes = [1 for i, j in zip(corona_data, last) if i > j]
                if changes:
                    job_context[corona.data_source]["last"] = corona_data
                    if job_context["chat_id"]:
                        context.bot.send_message(job_context["chat_id"], text=corona.description,
                                                 parse_mode=ParseMode.MARKDOWN)
                    if use_db:
                        repo = CasesRepo()
                        data = {
                            "source": corona.data_source,
                            "region": region,
                            "cases": corona_data[0],
                            "deaths": corona_data[1],
                            "recovery": corona_data[2],
                            "date": corona.last_date
                        }
                        repo.add(data)
                        repo.save()


if use_db:
    logger.addHandler(DBLogHandler())
    _jobs = JobsDBInfo()
else:
    _jobs = JobsInfo("logs/jobs.pickle")


def set_timer(update, context):
    """Adiciona uma região na lista de jobs"""
    logger.info('Arrive /listen command "%s"', _log_message_data(update.effective_message))
    chat_id = update.message.chat_id
    try:
        region = context.args[0]
        minutes = int(context.args[1]) if len(context.args) > 1 else 5
        only_new = context.args[2] == "--new" if len(context.args) > 2 else False

        if not region or minutes < 1:
            raise ValueError

        # Add job to queue
        job = context.job_queue.run_repeating(on_change_notifier, minutes * 60, first=5,
                                              context={"chat_id": str(chat_id), "region": region,
                                                       "new": only_new, "last": [0, 0, 0]})
        _jobs.push(str(chat_id), job)
        _jobs.save()

        update.message.reply_text('Monitoramento ativado!')

    except (IndexError, ValueError):
        update.message.reply_text("Use: /listen <região> <minutos>\nUse: /mute para parar de observar")


def unset_timer(update, context):
    """Remove o job programado"""
    logger.info('Arrive /mute command "%s"', _log_message_data(update.effective_message))
    chat_id = str(update.message.chat_id)

    if not _jobs.exists(chat_id):
        update.message.reply_text('Nenhum monitoramento ativo')
        return

    job = _jobs.pop(chat_id)
    job.schedule_removal()
    _jobs.save()

    update.message.reply_text('Monitoramento desativado')


def main():
    """Start the bot."""
    # Certifique-se que exista uma variavel de ambiente com o nome TELEGRAM_TOKEN
    # setada com o token do seu bot
    updater = Updater(os.environ.get("TELEGRAM_TOKEN", "Get token on bot father!"), use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("chart", chart))
    dp.add_handler(CommandHandler("listen", set_timer, pass_args=True, pass_job_queue=True))
    dp.add_handler(CommandHandler("mute", unset_timer))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.update.channel_post, general))
    dp.add_handler(InlineQueryHandler(inline_query))
    dp.add_handler(MessageHandler(Filters.command, unknown))

    # job para atualizar os dados das fontes e atualizar o canal caso haja novos casos
    refresh_time = int(os.environ.get("REFRESH_TIME", "600"))
    dp.job_queue.run_repeating(refresh_data, refresh_time, first=5, context={"chat_id": channel_id, "region": "BR"})

    # carrega a lista de jobs que estavam programados

    jobs = _jobs.load()
    for key, data in jobs.items():
        if data.get("repeat", True):
            _jobs.push(key, dp.job_queue.run_repeating(on_change_notifier,
                                                       data.get("interval", 300), context=data.get("context")))
        else:
            _jobs.push(key, dp.job_queue.run_once(on_change_notifier,
                                                  data.get("interval", 300), context=data.get("context")))

    # log all errors
    dp.add_error_handler(error)

    # Inicia o Bot no modo polling
    updater.start_polling()

    # Roda até receber um Ctrl-C
    updater.idle()

    _jobs.save()
