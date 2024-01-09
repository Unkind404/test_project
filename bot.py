from datetime import datetime
from operator import ifloordiv
from sqlite3 import connect
from threading import Timer
import requests
import time
from click import command
import telebot
import logging
import psycopg2
import json

bot = telebot.TeleBot("token");
conn = psycopg2.connect(
    user='tgbot',
    password='tgbot123',
    host='127.0.0.1',
    port='5432',
    database='bot_db'
)
cur = conn.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        db_chat_id BIGINT NOT NULL,
        db_repo_user VARCHAR(255) NOT NULL,
        db_repo_name VARCHAR(255) NOT NULL,
        sub_rule1 TEXT NOT NULL,
        sub_rule2 TEXT,
        timestamp INTEGER NOT NULL
    )
''')
conn.commit()

req_url = "https://api.github.com/repos/{repo_user}/{repo_name}/{sub_type}" 
headers = {'Accept':'application/vnd.github.v3+json'}
r = requests.get(req_url, headers=headers)
r.json()


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Данный бот позволяет подписаться на репозитории Github и получать информацию об обновлениях issues и pull requests.\n\n Для подписки на репозиторий используйте команду:\n **/sub <repo_url> <events>**\nгде:\n   **<repo_url>** - адрес репозитория\n   **<events>** - события, на которые хотите подписаться.\n\nПример команды:\n**/sub https://github.com/tornadoweb/tornado mr,issue**", disable_web_page_preview=True)
    

@bot.message_handler(commands=['sub'])
def sub(message):
    command_args = message.text.split()[1:]

    if len(command_args)<=1:
        bot.reply_to(message, "Недостаточно данных для подписки")
    else:
        repo_url = command_args[0]
        event = command_args[1]
        response_message = f"Вы подписались на {repo_url} для получения событий об {event}"
        bot.reply_to(message, response_message, disable_web_page_preview=True)

        chat_id = message.chat.id
        repo_info = repo_url.split('/')[3:]
        repo_user = repo_info[0]
        repo_name = repo_info[1]
        event_split = event.split(',')
        if len(event_split)==1:
            sub_rule1 = event_split[0]
            sub_rule2 = None
        else:
            sub_rule1 = event_split[0]
            sub_rule2 = event_split[1]

    ts = datetime.now().timestamp()
    print(ts)
    insert_query = """INSERT INTO users (db_chat_id, db_repo_user, db_repo_name, sub_rule1, sub_rule2, timestamp) VALUES (%s, %s, %s, %s, %s, %s)"""
    insert_data = (chat_id, repo_user, repo_name, sub_rule1, sub_rule2, ts)
    update_query = """UPDATE users SET sub_rule1=%s, sub_rule2=%s, timestamp=%s WHERE  db_chat_id=%s AND db_repo_user=%s AND db_repo_name=%s"""
    update_data = (sub_rule1, sub_rule2, ts, chat_id, repo_user, repo_name)
    select_query = """SELECT sub_rule1, sub_rule2 FROM users WHERE db_chat_id=%s AND db_repo_user=%s AND db_repo_name=%s"""
    select_data = (chat_id, repo_user, repo_name)
    
    cur.execute(select_query, select_data)
    db_out = cur.fetchall()
    if db_out==[]:
        cur.execute(insert_query, insert_data)
    else:
        cur.execute(update_query, update_data)
    conn.commit()

@bot.message_handler(commands=['unsub'])
def unsub(message):
    command_args = message.text.split()[1:]
    if len(command_args)<1:
        bot.reply_to_message(message, 'Для отписки используйте команду /unsub <repo_url>')
    else:
        repo_url = command_args[0] #Лишняя строка, но пусть будет
        repo_info = repo_url.split('/')[3:]
        repo_user = repo_info[0]
        repo_name = repo_info[1]
        chat_id = message.chat.id
        delete_data = (chat_id, repo_user, repo_name)
        delete_query = """DELETE FROM users WHERE chat_id=%s AND repo_user=%s AND repo_name=%s"""
        cur.execute(delete_query, delete_data)
        conn.commit()


def check():
    ts = datetime.now().timestamp()
    ts = int(ts)
    ts_check = ts-6000
    print(ts, ts_check)
    cur.execute("SELECT * FROM users WHERE timestamp < %s",[ts_check])

    rows = cur.fetchall()
    result=[]
    for row in rows:
        result << row.split(',') #Проблема с выводом значений в массивы. В БД есть значения null, которые нужно тоже получить. Либо добавлять при запросе к БД проверку на пустое поле
        res1 = result[0:3]
        res2 = result[1:2]
        print(res1, res2)


while True:
    time.sleep(30)
    t = Timer(30, check)
    t.start()


logging.basicConfig(filename='test.log',encoding='utf-8',level=logging.DEBUG)
bot.infinity_polling()