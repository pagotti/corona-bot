import logging
import datetime

from dasbot import bot

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        filemode="a",
                        filename="logs/log_{}.log".format(
                            datetime.datetime.strftime(datetime.datetime.now(), "%Y_%m_%d_%H_%M")),
                        level=logging.INFO)

    bot.main()
