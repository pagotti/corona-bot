# -*- coding: utf-8 -*-

"""
Modulo bot - Mantem as funções que gerenciam o bot
"""


import os
import logging
import locale

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dasbot.corona import CoronaData, BrazilData, BrazilStatesData, BrazilChart

# Enable logging
logger = logging.getLogger(__name__)
corona = CoronaData()


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


def _stat_message(br: BrazilData):
    if corona.last_br_date:
        return "Mortes: *{:n}*, Confirmados: *{:n}*, Suspeitos: *{:n}*, Descartados: *{:n}* - em _{}_".\
            format(br.death, br.confirmed, br.suspect, br.refused, corona.last_br_date)
    else:
        return "Não há dados disponíveis"


def stats(update, context):
    logger.info('Arrive /stats command "%s"', update.effective_message)
    update.message.reply_markdown(_stat_message(BrazilData(corona.brazil)))


def general(update, context):
    if context.match:
        logger.info('Arrive UF message "%s"', update.effective_message)
        if context.match.group(0) == "BR":
            msg = _stat_message(BrazilData(corona.brazil))
            update.message.reply_markdown(msg)
        else:
            msg = _stat_message(BrazilStatesData(corona.brazil, context.match.group(0)))
            update.message.reply_markdown(msg)
    else:
        echo(update, context)


def refresh(update, context):
    chart = BrazilChart(corona.brazil_series())
    if corona.refresh():
        image = chart.image()
        caption = "Atualizado: {}".format(corona.last_br_date)
        context.bot.send_photo("@corona_br", image, caption=caption)
        image.seek(0)
        msg = _stat_message(BrazilData(corona.brazil))
        context.bot.send_message("@corona_br", msg, parse_mode="Markdown")
        update.message.reply_photo(photo=image, caption=caption)
    else:
        update.message.reply_message("Não há atualizações")


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
    dp.add_handler(MessageHandler(Filters.regex(r"[A-Z]{2}") & ~Filters.update.channel_post, general))

    # echo das mensagens que não são comandos
    dp.add_handler(MessageHandler(Filters.text & ~Filters.update.channel_post, echo))

    # log all errors
    dp.add_error_handler(error)

    # Inicia o Bot no modo polling
    updater.start_polling()

    # Roda até receber um Ctrl-C
    updater.idle()


