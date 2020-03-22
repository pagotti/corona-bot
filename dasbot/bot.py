# -*- coding: utf-8 -*-

"""
Modulo bot - Mantem as funções que gerenciam o bot
"""


import os
import logging
import locale
import pytz
from datetime import datetime

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dasbot.corona import GovBR, GovStates, BingData, br_ufs, SeriesChart


# Enable logging
logger = logging.getLogger(__name__)

corona_br = BingData()


def check_refresh_data():
    today = datetime.now().replace(tzinfo=pytz.UTC)
    if corona_br.last_date is None or corona_br.last_date.replace(tzinfo=pytz.UTC) < today:
        corona_br.refresh()


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("""Olá. Sou um bot de dados de casos de COVID-19 no Brasil.
    Eu busco dados do Ministério da Saúde (plataforma.saude.gov.br) e apresento os totais por 
    estado ou para todo o país. Digite /help para ver as opções""")


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text("""Comandos que você pode enviar:
    /start : inicia o bot
    /help : mostra essa ajuda
    /stats : mostra os números de casos confirmados, suspeitos e descartados
    Envie uma sigla de estado, por exemplo SC, SP, RJ para saber os dados por estado
    Outros comandos serão retornados de volta apenas para informar que o bot está funcionando""")


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def stats(update, context):
    logger.info('Arrive /stats command "%s"', update.effective_message)
    check_refresh_data()
    update.message.reply_markdown(corona_br.description)


def general(update, context):
    if context.match:
        logger.info('Arrive UF message "%s"', update.effective_message)
        check_refresh_data()
        uf = context.match.group(0)
        if uf == "BR":
            update.message.reply_markdown(corona_br.description)
        elif uf in br_ufs:
            corona_states = GovStates(uf)
            corona_states.refresh()
            update.message.reply_markdown(corona_states.description)
        else:
            update.message.reply_text("UF não reconhecida. Tente novamente.")
    else:
        echo(update, context)


def refresh(update, context):
    # br = GovBR()
    # br.refresh()
    # chart = SeriesChart(br)
    # image = chart.image()
    # caption = "Atualizado: {}".format(corona_br.last_date.strftime("%d-%m-%Y %H:%M"))

    # context.bot.send_photo("@corona_br", image, caption=caption)
    # image.seek(0)
    # msg = corona_br.description
    # context.bot.send_message("@corona_br", msg, parse_mode="Markdown")

    update.message.reply_photo(photo=image, caption=caption)


def channel(update, context):
    check_refresh_data()
    msg = corona_br.description
    context.bot.send_message("@corona_br", msg, parse_mode="Markdown")


def main():
    """Start the bot."""
    locale.setlocale(locale.LC_ALL, "pt_BR")

    # Certifique-se que exista uma variavel de ambiente com o nome TELEGRAM_TOKEN
    # setada com o token do seu bot
    updater = Updater(os.environ.get("TELEGRAM_TOKEN", "Get token on bot father!"), use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("refresh", refresh))
    dp.add_handler(CommandHandler("channel", channel))
    dp.add_handler(MessageHandler(Filters.regex(r"^[A-Z]{2}") & ~Filters.update.channel_post, general))

    # echo das mensagens que não são comandos
    dp.add_handler(MessageHandler(Filters.text & ~Filters.update.channel_post, echo))

    # log all errors
    dp.add_error_handler(error)

    # Inicia o Bot no modo polling
    updater.start_polling()

    # Roda até receber um Ctrl-C
    updater.idle()


