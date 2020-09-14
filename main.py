import telebot
import mysql.connector
from collections import defaultdict
import os

import maps_api


TOKEN = "960484549:AAG_8_kO8sDTSFb99I_cH7i6XmiZMFLLmnA"
START, TITLE, PHOTO, LOCATION = range(4)
USER_STATE = defaultdict(lambda: START)

bot = telebot.TeleBot(TOKEN)

db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    passwd="Sekret_45",
    port=3306,
    database="tg_bot"
)

cursor = db.cursor()


@bot.message_handler(commands=['start'])
def start_handler(message):
    info = (message.from_user.id, message.from_user.username)
    try:
        cursor.execute("INSERT INTO users (user_id, user_name) VALUES (%s, %s)", info)
        db.commit()
        bot.send_message(message.chat.id, "Привет! Я помогу тебе запомнить понравившиеся места, а потом " +
                         "напомнить тебе о них и найти ближайшее, когда это будет нужно :)")
        bot.send_message(message.chat.id, "Введи /add, чтобы начать добавлять новое место. Введи \list, " +
                         "чтобы просмотреть добавленные места. Введи /reset, чтобы удалить все записи. " +
                         "Отправь свою геолокацию, чтобы увидеть добавленные места в радиусе 500 метров."
                         "")
    except mysql.connector.errors.IntegrityError:
        bot.send_message(message.chat.id, "Уже запущен!")


values = {}


@bot.message_handler(commands=['add'])
def handle_add(message):
    values[message.chat.id] = []
    bot.send_message(message.chat.id, "Напиши название места")
    update_state(message, TITLE)


@bot.message_handler(func=lambda message: get_state(message) == TITLE)
def handle_title(message):
    values[message.chat.id].append(message.text)
    bot.send_message(message.chat.id, "Отправь фото")
    update_state(message, PHOTO)


@bot.message_handler(content_types=['photo'], func=lambda message: get_state(message) == PHOTO)
def handle_photo(message):
    photo = message.photo[0]
    file_info = bot.get_file(photo.file_id)
    file = bot.download_file(file_info.file_path)
    values[message.chat.id].append(photo.file_id)
    with open("images/" + photo.file_id, 'wb') as new_file:
        new_file.write(file)
    bot.send_message(message.chat.id, "Отправь свою геолокацию")
    update_state(message, LOCATION)


@bot.message_handler(content_types=['location'], func=lambda message: get_state(message) == LOCATION)
def handle_location(message):
    location = message.location
    values[message.chat.id].append(str(location.latitude))
    values[message.chat.id].append(str(location.longitude))
    values[message.chat.id].append(str(message.from_user.id))
    cursor.execute(
        "INSERT INTO places (place_name, image_name, latitude, longitude, user_id) VALUES (%s, %s, %s, %s, %s)",
        tuple(values[message.chat.id]))
    db.commit()
    bot.send_message(message.chat.id,
                     "Место добавлено!. Введи /add, чтобы начать добавлять новое место. Введи /list для просмотра последних 10 добавленных мест.")
    values[message.chat.id].clear()
    update_state(message, START)


@bot.message_handler(commands=['list'])
def handle_list_command(message):
    cursor.execute("SELECT place_name, image_name from places WHERE user_id = (%s)", [message.from_user.id])
    res = cursor.fetchall()
    res = res[len(res) - 10:len(res)]
    if len(res):
        for info in res:
            place_name = str(info[0])
            img_name = str(info[1])
            image = open("images/" + img_name, "rb")
            bot.send_photo(message.chat.id, image, place_name)
    else:
        bot.send_message(message.chat.id, "Нет добавленных мест")


@bot.message_handler(content_types=['location'])
def handle_location(message):
    cursor.execute("SELECT place_id, place_name, latitude, longitude from places WHERE user_id = (%s)",
                   [message.from_user.id])
    res = cursor.fetchall()
    loc = message.location
    dists = []
    bot.send_message(message.chat.id, "Обрабатываем...")
    for place_id, place_name, lat, long in res:
        dists.append((place_id, place_name, maps_api.get_distance(loc.latitude, loc.longitude, lat, long), lat, long))

    dists = sorted(list(filter(lambda a: a[2] <= 500.0, dists)), key=lambda a: a[2])
    if len(dists):
        for i in dists:
            text = i[1] + " - " + str(i[2]) + "м\n"
            bot.send_message(message.chat.id, text)
            bot.send_location(message.chat.id, i[3], i[4])
    else:
        bot.send_message(message.chat.id, "Нет добавленных мест в радиусе 500 метров.")


@bot.message_handler(commands=['reset'])
def handle_reset(message):
    cursor.execute("SELECT image_name FROM places WHERE user_id = {}".format(message.from_user.id))
    res = cursor.fetchall()
    for name in res:
        try:
            os.remove("images/" + name[0])
        except FileNotFoundError:
            pass
    cursor.execute("DELETE FROM places WHERE user_id = {}".format(message.from_user.id))
    db.commit()
    bot.send_message(message.chat.id, "Записи о местах успешно удалены.")


def update_state(message, new_state):
    USER_STATE[message.chat.id] = new_state


def get_state(message):
    return USER_STATE[message.chat.id]


if __name__ == "__main__":
    bot.polling()
