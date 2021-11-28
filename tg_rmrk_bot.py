import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job
from tg_rmrk_datatools import *
from tg_rmrk_send_message import *
from tg_rmrk_updates import *
from tg_rmrk_parse_message import *
from tg_rmrk_config import *


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)

updater = Updater(token=tg_token, use_context=False)
dispatcher = updater.dispatcher

if __name__ == '__main__':
    parse_message_handler = MessageHandler(Filters.all, parse_message)
    dispatcher.add_handler(parse_message_handler)
    updater.job_queue.run_repeating(check_update, 30)
    updater.job_queue.run_repeating(update_ksm_exchange_rate, 300.0)
    updater.job_queue.run_repeating(send_messages, 3.0)
    updater.start_polling(drop_pending_updates=True)
    updater.idle()
