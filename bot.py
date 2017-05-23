#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging, sqlite3, pytz, re
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, \
    InlineQueryHandler, RegexHandler, ConversationHandler
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, \
    InputTextMessageContent, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardHide
from datetime import datetime
from uuid import uuid4

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

"""
### MAIN
"""
def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater('INSERT YOUR TOKEN HERE')
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == "__main__":
    main()