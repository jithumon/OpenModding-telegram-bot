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
### CLASSES
"""
class DBHandler:
    def __init__(self, path):
        self._dbpath = path

    def get_links(self, device_id):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        result = ()
        db_query = cursor.execute("SELECT link,name FROM roms WHERE device_id=?", (device_id,)).fetchall()
        if db_query:
            for query in db_query:
                result += ({"name": query["name"],
                            "link": query["link"],
                            },)
        else:
            result = {"error": "not_found"}
        return result

    def get_privs(self, telegram_id):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query = cursor.execute("SELECT privs FROM users WHERE id=?", (telegram_id,)).fetchone()
        if not query:
            result = -2
        else:
            result = query["privs"]
        return result

    def update_user(self, from_user): # Update the user list (db)
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        check = cursor.execute("SELECT id,time_used FROM users WHERE id=?", (from_user.id,)).fetchone()
        used = 0
        if check:
            if check["time_used"]:
                used = check["time_used"]
        query = (from_user.first_name,
                 from_user.last_name,
                 from_user.username,
                 datetime.now(pytz.timezone('Europe/Rome')),
                 used + 1,
                 from_user.id)
        if check:
            cursor.execute("UPDATE users SET name_first=?,name_last=?,username=?,last_use=?,time_used=? WHERE id=?",
                           query)
        else:
            cursor.execute("INSERT INTO users(name_first,name_last,username,last_use,time_used,id) VALUES(?,?,?,?,?,?)",
                           query)
        handle.commit()

    def add_link(self, device_id, link, name):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query = (device_id,
                 link,
                 name)
        cursor.execute("INSERT INTO roms(device_id,link,name) VALUES(?,?,?)", query)
        handle.commit()

    def get_device(self, name):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query = cursor.execute("SELECT id,name,codename FROM devices WHERE name=?", (name + "_roms",)).fetchone()
        if not query:
            query = cursor.execute("SELECT id,name,codename FROM devices WHERE codename=?", (name,)).fetchone()
            if not query:
                result = {"error": "not_found"}
                return result
        result = {"id": query["id"],
                  "db_name": query["name"][:-6],
                  "name": query["codename"], }
        return result

    def get_all_devices_roms(self):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        result = ()
        query_db = cursor.execute("SELECT id,name,codename FROM devices WHERE name LIKE '%_roms'")
        for query in query_db:
            result += ({"id": query["id"],
                        "db_name": query["name"][:-5],
                        "name": query["codename"], },)
        return result

    def link_search(self, name, dicted=False):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query_db = cursor.execute(
            "SELECT devices.codename,roms.link,roms.name FROM roms JOIN devices ON devices.id=roms.device_id "
            "WHERE roms.name LIKE ?",
            ("%%%s%%" % name,)).fetchall()
        if dicted:
            result = {}
            for query in query_db:
                if query["codename"][:-1] not in result:
                    result[query["codename"][:-1]] = ()
                result[query["codename"][:-1]] += ({"name": query["name"],
                                                    "link": query["link"], },)
        else:
            result = ()
            for query in query_db:
                result += ({"name": query["name"],
                            "link": query["link"],
                            "type": query["codename"], },)
        return (result)

    def feedback_submit(self, user_id, feedback):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query_db = cursor.execute("INSERT INTO feedback(user_id,text) VALUES(?,?)", (user_id, feedback))
        print(query_db, user_id, feedback)
        handle.commit()

    def feedback_get(self, id):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        feedback = cursor.execute(
            "SELECT users.id,feedback.text,users.name_first,users.name_last,users.username FROM feedback JOIN users "
            "ON feedback.user_id=users.id WHERE feedback.id=?",
            (id,)).fetchone()
        result = {"feedback": feedback["text"],
                  "first_name": feedback["name_first"],
                  "last_name": feedback["name_last"],
                  "username": feedback["username"],
                  "user_id": feedback["id"]}
        return (result)

    def feedback_get_unread(self, all=False): # Set unread feedbacks
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        result = ()
        if all == True:
            query = cursor.execute("SELECT * FROM feedback").fetchall()
        else:
            query = cursor.execute("SELECT * FROM feedback WHERE read=0").fetchall()
        for feedback in query:
            result += ({"id": feedback["id"],
                        "text": feedback["text"]},)
        return (result)

    def feedback_set_read(self, id): # Set read feedbacks
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query = cursor.execute("UPDATE feedback SET read=1 WHERE id=?", (id,))
        print(query)
        handle.commit()

"""
### UTILITY
"""
def group(lst, n):
    result = ()
    temp = ()
    x = 1
    for i, item in enumerate(lst):
        temp += (item,)
        if x % n == 0:
            x = 1
            result += (temp,)
            temp = ()
        else:
            x += 1
        if i == len(lst) - 1 and temp:
            result += (temp,)
    return (result)

def group_links(links, name):
    text = "<b>%s:</b>\n" % (name)
    for link in links:
        text += "  <a href=\"%s\">%s</a>\n" % (link["link"], link["name"])
    return text

def do_keyboard(lst):
    keyboard = []
    temp = []
    groups = group(lst, 2)
    for grouped in groups:
        for device in grouped:
            temp += [KeyboardButton(device["name"])]
        keyboard += [temp]
        temp = []
    keyboard += [[KeyboardButton("Leave a Feedback!")]]
    keyboard += [[KeyboardButton("Close Keyboard")]]
    return (keyboard)

"""
### GLOBALS
"""
def setGlobals():
    global db
    db = DBHandler("modding.sqlite")

"""
### INLINE QUERY
"""
def inline_query(bot, update):
    query = update.inline_query
    db.update_user(query.from_user)
    results = list()
    if query.query == "":
        devices = db.get_all_devices_roms()
    else:
        devices = (db.get_device(query.query),)
        links_db = db.link_search(query.query, True)
        if links_db:
            text = "Here are all links containing \"%s\" word.\n\n" % (query.query)
            for key in links_db.keys():
                text += "<b>%ss</b>\n" % (key)
                for rom in links_db[key]:
                    text += "<a href=\"%s\">%s</a>\n" % (rom["link"], rom["name"])
                text += "\n"
            results.append(InlineQueryResultArticle(id=uuid4(),
                                                    title="All links containing \"%s\" word." % (query.query),
                                                    input_message_content=InputTextMessageContent(text,
                                                                                    parse_mode=ParseMode.HTML,
                                                                                    disable_web_page_preview=True), ))
    for device in devices:
        if "error" not in device:
            links = db.get_links(device["id"])
            if "error" not in links:
                text = group_links(links, device["name"])
                results.append(InlineQueryResultArticle(id=uuid4(),
                                                        title=device["name"],
                                                        input_message_content=InputTextMessageContent(text,
                                                                                    parse_mode=ParseMode.HTML,
                                                                                    disable_web_page_preview=True), ))
    bot.answerInlineQuery(query.id, results=results)

"""
### INLINE CALLBACK 
"""
def inline_button_callback(bot, update):
    query = update.callback_query
    text = ""
    keyboard = []
    query_data = query.data.split(".")
    if query_data[0] == "main":
        text = "Choose something."
        temp = []
        devices = db.get_all_devices_roms()
        groups = group(devices, 2)
        for grouped in groups:
            for device in grouped:
                temp += [InlineKeyboardButton(device["name"], callback_data="show.%s" % device["db_name"])]
            keyboard += [temp]
            temp = []
    elif query_data[0] == "show":
        device = db.get_device(query_data[1])
        text = group_links(db.get_links(device["id"]), device["name"])
        keyboard = [[InlineKeyboardButton("Main Menù", callback_data="main")]]
    elif query_data[0] == "feedback":
        if query_data[1] == "unread" or query_data[1] == "all":
            if query_data[1] == "unread":
                unread_db = db.feedback_get_unread()
            else:
                unread_db = db.feedback_get_unread(True)
            keyboard = []
            if unread_db:
                text = "Choose the feedback to read."
                unread_groups = group(group(unread_db, 2), 5)
                temp = []
                for groups in unread_groups[0]:
                    for grouped in groups:
                        lenght = 25
                        if len(grouped["text"]) > lenght:
                            button_text = "%s [...]" % (grouped["text"][:lenght].strip())
                        else:
                            button_text = "%s" % (grouped["text"][:lenght].strip())
                        temp += [InlineKeyboardButton(button_text, callback_data="feedback.read.%s" % grouped["id"])]
                    keyboard += [temp]
                    temp = []
            else:
                text = "Nothing to read."
            keyboard += [[InlineKeyboardButton("Go back", callback_data="feedback.menu")]]
        elif query_data[1] == "menu":
            text = "What do you want to read?"
            keyboard = [[InlineKeyboardButton("Unread feedbacks", callback_data="feedback.unread")],
                        [InlineKeyboardButton("All feedbacks", callback_data="feedback.all")]]
        elif query_data[1] == "read":
            feedback = db.feedback_get(query_data[2])
            db.feedback_set_read(query_data[2])
            name = ""
            username = ""
            if feedback["first_name"]:
                name += feedback["first_name"]
            if feedback["last_name"]:
                name += " %s" % feedback["last_name"]
            if feedback["username"]:
                username += " (@%s) " % feedback["username"]
            text += "From <b>%s</b>%s[ID: <i>%s</i>]\n\n%s" % (
            name.strip(), username, feedback["user_id"], feedback["feedback"])
            keyboard += [[InlineKeyboardButton("Go back", callback_data="feedback.unread")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if text:
        if query.message:
            bot.editMessageText(text=text, chat_id=query.message.chat_id, message_id=query.message.message_id,
                                reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        else:
            bot.editMessageText(text=text, inline_message_id=query.inline_message_id, reply_markup=reply_markup,
                                parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    elif keyboard:
        if query.message:
            bot.editMessageReplyMarkup(chat_id=query.message.chat_id, message_id=query.message.message_id,
                                       reply_markup=reply_markup)
        else:
            bot.editMessageReplyMarkup(inline_message_id=query.inline_message_id, reply_markup=reply_markup)

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

    # Set Database Handler as global class
    setGlobals()

    # Inline Query Handler
    dp.add_handler(InlineQueryHandler(inline_query))

    # Inline Callback
    dp.add_handler(CallbackQueryHandler(inline_button_callback))

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