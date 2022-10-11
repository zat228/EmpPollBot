import httplib2
import googleapiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
import logging
from datetime import timedelta, datetime
from aiogram import Bot, Dispatcher, executor, types
import time
from quizzer import Quest
CREDENTIALS_FILE = ''  # Имя файла с закрытым ключом, вы должны подставить свое

# Читаем ключи из файла
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])

httpAuth = credentials.authorize(httplib2.Http()) # Авторизуемся в системе
service = googleapiclient.discovery.build('sheets', 'v4', http=httpAuth) # Выбираем работу с таблицами и 4 версию API
spreadsheetId = ''  # Код гугл таблицы


def data_send(data, name_sheet):
    results = service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheetId, body={
        "valueInputOption": "USER_ENTERED",
        # Данные воспринимаются, как вводимые пользователем (считается значение формул)
        "data": [
            {"range": f"{name_sheet}!B3",
             "majorDimension": "ROWS",  # Сначала заполнять строки, затем столбцы
             "values": data
             }
        ]
    }).execute()


bot = Bot(token="")     # Бот токен
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

quest_db = []           # Здесь хранится информация о опросах, на момент создания
finished_quest = []     # Зедсь хранятся завершёные опросы
quest_owners = []       # Здесь хранятся пары "id викторины <--> id её создателя"
not_finish = []         # Хранение пользователей, не завершивших создание опроса
answers_m = {}


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    if message.chat.type == types.ChatType.PRIVATE:
        poll_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        poll_keyboard.add(types.KeyboardButton(text="Создать опрос"))
        poll_keyboard.add(types.KeyboardButton(text="Отмена"))
        await message.answer("Нажмите на кнопку ниже и создайте опрос! ", reply_markup=poll_keyboard)
    else:
        dog = await bot.get_me()
        await message.answer(f"Эта команда доступна в личных сообщениях @{dog.username}")


@dp.message_handler(commands=["stop"])
async def cmd_stop(message: types.Message):
    if message.chat.type != types.ChatType.PRIVATE:
        words = message.text.split()
        if len(words) == 1:
            await message.reply("Для остановки опроса, введите команду с кодом опроса.\nПример: /stop 534728634")
        elif len(words) > 1:
            if words[1] in answers_m:
                await parse_info(answers_m[words[1]])
                await message.reply(f"Опрос завершён")
            else:
                await message.answer(f"Опрос уже отправлен или его не существует.")
    else:
        await message.reply(f"Эта комаднда доступна только в чатах")


@dp.message_handler(commands=["c"])     # Отлов команды завершения создания ответов и создание времени
async def cmd_continue(message: types.Message):
    for i in quest_db:
        if i.owner == message.from_user.id and i.variants != []:
            i.mach = 4
            await message.answer("Введите время опроса. укажите время в минутах \n"
                                 "Если в этом нет необходимости напишите /t")
            break
        else:
            await message.answer("Список ответов пустой, заполните его")
            break


@dp.message_handler(commands=["t"])     # Установка отсутствия времени и переход к анонимности опроса
async def cmd_timer(message: types.Message):
    for i in quest_db:
        if i.owner == message.from_user.id:
            i.mach = 5
            i.time = False
            await message.answer("Без времени")
            anonim_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            anonim_keyboard.add(types.KeyboardButton(text="Да"))
            anonim_keyboard.add(types.KeyboardButton(text="Нет"))
            await message.answer(f"Сделать опрос анонимным?", reply_markup=anonim_keyboard)


@dp.message_handler(commands=["op"])
async def op_start(message):
    words = message.text.split()
    if len(words) == 1:
        await message.reply("Пропишите команду с кодом опроса.\nПример: /op 534728634")
    elif len(words) > 1:
        for i in quest_owners:
            if i[0] == int(words[1]):
                await message.reply("Опрос найден, загружаю...")
                for z in finished_quest:
                    if z.quiz_id == int(words[1]):
                        answers_m[f"{z.quiz_id}"] = {}
                        answers_m[f"{z.quiz_id}"]["answers"] = {}      # создание ключа в виде айди опроса для хранения данных голосования
                        answers_m[f"{z.quiz_id}"]["quiz_name"] = z.quiz_name
                        answers_m[f"{z.quiz_id}"]["quiz_text"] = z.quiz_text
                        inline_kb = types.InlineKeyboardMarkup(resize_keyboard=True)
                        for h in z.variants:    # Создание кнопок с ответами
                            inline_kb.add(types.InlineKeyboardButton(f'{h}', callback_data=f'{z.quiz_id}_{h}'))
                            if h not in answers_m[f"{z.quiz_id}"]:  # Создание счётчиков ответов
                                answers_m[f"{z.quiz_id}"]["answers"][f"{h}"] = 0
                        answers_m[f"{z.quiz_id}"]["answered_users"] = []
                        if z.time is not False:     # Запись времени окнчания голосования, если таймер поставлен
                            answers_m[f"{z.quiz_id}"]["clock"] = datetime.now() + z.time
                        else:
                            answers_m[f"{z.quiz_id}"]["clock"] = False
                        answers_m[f"{z.quiz_id}"]["anonmis"] = z.anonims    # Запись об анонимности голосования
                        t = answers_m[f"{z.quiz_id}"]["clock"]  # Переменная для таймера
                        answers_m[f"{z.quiz_id}"]["user_info"] = {} # Создание списка ответов участников. Используется только в случае не анонимности
                        await message.answer(f"Опрос: {z.quiz_name}\nВопрос: {z.quiz_text}\nАнонимность: {z.anonims}\nТаймер: до {t}\nНачали!", reply_markup=inline_kb)
                break


@dp.callback_query_handler()
async def process_callback_(callback_query: types.CallbackQuery):
    a = callback_query.data.split("_")
    if a[0] in answers_m:
        if (answers_m[a[0]]["clock"] != False) and answers_m[a[0]]["clock"] <= datetime.now():  # Проверка времени
            await parse_info(answers_m[a[0]])
            answers_m.pop(a[0])
            await bot.answer_callback_query(callback_query.id, f"Опрос завершён", show_alert=True)
        else:
            if a[1] in answers_m[a[0]]["answers"]:     # Проверка наличия ответа в опросе(для подстраховки)
                if callback_query.from_user.id not in answers_m[a[0]]["answered_users"]:    # Отвечал ли уже пользователь?
                    answers_m[a[0]]["answered_users"].append(callback_query.from_user.id)
                    answers_m[a[0]]["answers"][a[1]] += 1
                    if answers_m[a[0]]["anonmis"]:  # Проверка опроса на анонимность
                        pass
                    else:
                        answers_m[a[0]]["user_info"][f"{callback_query.from_user.last_name}"] = a[1]   # Запись ответа пользователя
                    print(answers_m)
                    await bot.answer_callback_query(callback_query.id, f"Вы выбрали ответ: {a[1]}", show_alert=True)
                else:
                    await bot.answer_callback_query(callback_query.id, f"Нехорошо фальсифицировать опросы!", show_alert=True)
    else:
        await bot.answer_callback_query(callback_query.id, "Опрос завершён или не существует", show_alert=True)


async def parse_info(data):     # Отправка на гугл таблицы
    results = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheetId,
        body={
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": f"{data['quiz_name']}",
                            "gridProperties": {
                                "rowCount": 200,
                                "columnCount": 12
                            }
                        }
                    }
                }
            ]
        }).execute()

    row_res = []
    row_res.append([f"Название опроса: {data['quiz_name']}"])
    row_res.append([f"Вопрос опроса: {data['quiz_text']}"])
    if not data['anonmis']:
        for i in data['user_info']:
            row_res.append([f"Пользователь {i} ответил", data['user_info'][i]])
    for i in data["answers"]:
        row_res.append([f"За вариант {i} - ", f"{data['answers'][i]}", "голосов"])
    data_send(row_res, data['quiz_name'])


async def save_pool(user_id, quiz_ids):
    quest_owners.append([quiz_ids, user_id])    # Сохраниение пары "викторина - пользователь"
    not_finish.remove(user_id)          # Удаление юзера из списка "незакончивших"
    finished_quest.append(quest_db[0])  # Добавления опроса в список завершённых
    for i in quest_db:                  # Удаление опроса из хранилища сборщика
        if i.quiz_id == quiz_ids:
            quest_db.remove(i)


@dp.message_handler(lambda message: message.text == "Создать опрос")        # Начало создания опроса
async def test(message: types.Message):
    if not_finish.count(message.from_user.id) == 0:     # Проверка на наличие пользователся в списке незакончивших
        not_finish.append(message.from_user.id)         # Добавление в список незакончивших
        quest_db.append(Quest(quiz_id=message.from_user.id + round(time.time()),  # Добавление в список создания опросов
                              owner_id=message.from_user.id,
                              mach=1))
        await message.answer("Начинаем. Санчала введите название опроса", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Сначала закончите создание прошлого опроса")

# 540454127


@dp.message_handler(lambda message: message.text)
async def sztatments(message: types.Message):       # Система контроля создания опроса
    for i in quest_db:
        if i.owner == message.from_user.id:         # Поиск опроса по айди владельца
            # Переход "название опроса - вопроса опроса"
            if i.mach == 1:     # 1 - это этап создания названия опроса
                i.variants = []     # Обнуление массива класса
                i.mach = 2          # обозначение перехода ко второму этапу - созданию вопроса опроса (Короче, подобие машины состояний)
                i.quiz_name = message.text      # Назначение названия опроса
                # Сообщения выводимые пользователю
                await message.answer(f"Теперь опрос называется {i.quiz_name}.")
                await message.answer("Теперь добавьте вопрос опроса")
# \/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/Остальные состояния сформированны по той же логике\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/
                break
            # Переход "вопрос опроса - варианты ответов"
            elif i.mach == 2:
                i.quiz_text = message.text
                i.mach = 3
                await message.answer(f"Вопрос данного опроса: {i.quiz_text}")
                await message.answer("Далее введите варианты ответов")
                break
            # Переход "варианты ответа - таймер опроса"
            elif i.mach == 3:
                i.variants.append(message.text)
                await message.answer(f"Варианты ответов: {i.variants}")
                await message.answer("Вы можете добавить ещё. Если вы закончили напишите команду /c")
                break
            # Переход "время опроса - анонимность опроса"
            elif i.mach == 4:
                if message.text.isnumeric():
                    # now = datetime.now()
                    target = timedelta(minutes=int(message.text))
                    # future = now + target
                    i.time = target
                    await message.answer(f"Таймер опроса {target}")
                    i.mach = 5
                    anonim_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    anonim_keyboard.add(types.KeyboardButton(text="Да"))
                    anonim_keyboard.add(types.KeyboardButton(text="Нет"))
                    await message.answer(f"Сделать опрос анонимным?", reply_markup=anonim_keyboard)
                    break
                else:
                    await message.answer("Вводите только число в минутах, без приписок")
                    break
            # Переход "анонимность опроса - сохранение опроса"
            elif i.mach == 5:
                if message.text == 'Да':
                    i.anonims = True
                    await save_pool(message.from_user.id, i.quiz_id)        # Вызов функции сохраниения опроса
                    await message.answer(
                        "Опрос сохранён, теперь его можно отправить, добавив бота в беседу, выдав права"
                        "администратора, и вызвав этот опрос командой /op код_опроса", reply_markup=types.ReplyKeyboardRemove())
                    await message.answer(f"Ваш код опроса: {i.quiz_id}")
                    await message.answer("Бота можно добавить в группу нажав на него и выбрав кнопку \"Добавит"
                                         "ь в группу или канал\"")
                    break
                elif message.text == 'Нет':
                    i.anonims = False
                    await save_pool(message.from_user.id, i.quiz_id)         # Вызов функции сохраниения опроса
                    await message.answer(
                        "Опрос сохранён, теперь его можно отправить, добавив бота в беседу, выдав права"
                        "администратора, и вызвав этот опрос командой /op код_опроса", reply_markup=types.ReplyKeyboardRemove())
                    await message.answer(f"Ваш код опроса: {i.quiz_id}")
                    await message.answer("Бота можно добавить в группу нажав на него и выбрав кнопку \"Добавит"
                                         "ь в группу или канал\"")
                    break
                else:
                    await message.answer("Только \"Да\" или \"Нет\"")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)


