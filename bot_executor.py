import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta

import pandas as pd
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import token_bot_executor

storage = MemoryStorage()
bot = Bot(token=token_bot_executor, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    employee = State()
    master_1 = State()
    date_1 = State()
    master_2 = State()
    date_2 = State()
    master_3 = State()
    date_3 = State()
    time_choice = State()
    master_schedule = State()


time_to_column = {
    "08:00": "start_0800",
    "09:00": "start_0900",
    "10:00": "start_1000",
    "11:00": "start_1100",
    "12:00": "start_1200",
    "13:00": "start_1300",
    "14:00": "start_1400",
    "15:00": "start_1500",
    "16:00": "start_1600",
    "17:00": "start_1700",
    "18:00": "start_1800",
    "19:00": "start_1900",
}


chosen_master_id = {}


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    try:
        start_buttons = [
            "Заполнить график (дни)",
            "Редактировать график",
            "Получить файл с записями",
            "Получить график мастера",
            "Получить общий график",
        ]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in start_buttons:
            keyboard.add(types.KeyboardButton(button))
        await message.answer("Привет! Чего желаешь", reply_markup=keyboard)
    except Exception as e:
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова")
        print(f"Error in send_welcome: {e}")


@dp.message_handler(lambda message: message.text == "Получить график мастера")
async def choice_masters_in_schedule(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return
        conn = sqlite3.connect("db")
        c = conn.cursor()
        c.execute("SELECT id, firstName, lastName FROM Masters")
        masters = c.fetchall()
        conn.close()
        master_dict = {f"{master[1]} {master[2]}": master[0] for master in masters}

        await state.update_data(master_dict=master_dict)

        initial_buttons = [f"{master[1]} {master[2]}" for master in masters]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in initial_buttons:
            keyboard.add(types.KeyboardButton(button))

        cancel_button = types.KeyboardButton("Отмена")
        keyboard.add(cancel_button)
        await message.answer("Выберите мастера", reply_markup=keyboard)
        await Form.master_schedule.set()

    except sqlite3.OperationalError as e:
        await message.reply(
            "Произошла ошибка при получении списка мастеров. Попробуйте снова позже"
        )
        print(f"SQLite operational error occurred: {e}")

    except Exception as e:
        await message.reply("Извините, произошла ошибка. Попробуйте снова")
        print(f"Произошла непредвиденная ошибка: {e}")


@dp.message_handler(state=Form.master_schedule)
async def get_schedule(message: types.Message, state: FSMContext):
    try:
        chosen_master_name = message.text
        if chosen_master_name in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return

        user_data = await state.get_data()
        master_dict = user_data.get("master_dict", {})
        master_id = master_dict.get(chosen_master_name)

        if master_id is None:
            await message.reply("Возникла ошибка: мастер не найден.")
            return

        conn = sqlite3.connect("db")
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT 
    strftime('%d-%m-%Y', datetime(substr(MasterTime.dayDate, 7, 4) || '-' ||
    substr(MasterTime.dayDate, 4, 2) || '-' || substr(MasterTime.dayDate, 1, 2))) AS DisplayDate,
    COALESCE(rec1.clientFirstName, MasterTime.start_0800) AS '08:00',
    COALESCE(rec2.clientFirstName, MasterTime.start_0900) AS '09:00',
    COALESCE(rec3.clientFirstName, MasterTime.start_1000) AS '10:00',
    COALESCE(rec4.clientFirstName, MasterTime.start_1100) AS '11:00',
    COALESCE(rec5.clientFirstName, MasterTime.start_1200) AS '12:00',
    COALESCE(rec6.clientFirstName, MasterTime.start_1300) AS '13:00',
    COALESCE(rec7.clientFirstName, MasterTime.start_1400) AS '14:00',
    COALESCE(rec8.clientFirstName, MasterTime.start_1500) AS '15:00',
    COALESCE(rec9.clientFirstName, MasterTime.start_1600) AS '16:00',
    COALESCE(rec10.clientFirstName, MasterTime.start_1700) AS '17:00',
    COALESCE(rec11.clientFirstName, MasterTime.start_1800) AS '18:00',
    COALESCE(rec12.clientFirstName, MasterTime.start_1900) AS '19:00'
FROM MasterTime
LEFT JOIN Record as rec1 ON MasterTime.masterId = rec1.masterId AND MasterTime.dayDate = rec1.appointmentDate AND rec1.appointmentTime = '08:00'
LEFT JOIN Record as rec2 ON MasterTime.masterId = rec2.masterId AND MasterTime.dayDate = rec2.appointmentDate AND rec2.appointmentTime = '09:00'
LEFT JOIN Record as rec3 ON MasterTime.masterId = rec3.masterId AND MasterTime.dayDate = rec3.appointmentDate AND rec3.appointmentTime = '10:00'
LEFT JOIN Record as rec4 ON MasterTime.masterId = rec4.masterId AND MasterTime.dayDate = rec4.appointmentDate AND rec4.appointmentTime = '11:00'
LEFT JOIN Record as rec5 ON MasterTime.masterId = rec5.masterId AND MasterTime.dayDate = rec5.appointmentDate AND rec5.appointmentTime = '12:00'
LEFT JOIN Record as rec6 ON MasterTime.masterId = rec6.masterId AND MasterTime.dayDate = rec6.appointmentDate AND rec6.appointmentTime = '13:00'
LEFT JOIN Record as rec7 ON MasterTime.masterId = rec7.masterId AND MasterTime.dayDate = rec7.appointmentDate AND rec7.appointmentTime = '14:00'
LEFT JOIN Record as rec8 ON MasterTime.masterId = rec8.masterId AND MasterTime.dayDate = rec8.appointmentDate AND rec8.appointmentTime = '15:00'
LEFT JOIN Record as rec9 ON MasterTime.masterId = rec9.masterId AND MasterTime.dayDate = rec9.appointmentDate AND rec9.appointmentTime = '16:00'
LEFT JOIN Record as rec10 ON MasterTime.masterId = rec10.masterId AND MasterTime.dayDate = rec10.appointmentDate AND rec10.appointmentTime = '17:00'
LEFT JOIN Record as rec11 ON MasterTime.masterId = rec11.masterId AND MasterTime.dayDate = rec11.appointmentDate AND rec11.appointmentTime = '18:00'
LEFT JOIN Record as rec12 ON MasterTime.masterId = rec12.masterId AND MasterTime.dayDate = rec12.appointmentDate AND rec12.appointmentTime = '19:00'
WHERE MasterTime.masterId = ?
ORDER BY datetime(substr(MasterTime.dayDate, 7, 4) || '-' ||
    substr(MasterTime.dayDate, 4, 2) || '-' || substr(MasterTime.dayDate, 1, 2));

        """,
            (master_id,),
        )
        data = cursor.fetchall()
        conn.close()

        # Проверка на наличие данных
        if not data:
            await message.answer("Нет данных для отображения.")
            return

        columns = [
            "DayDate",
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
            "17:00",
            "18:00",
            "19:00",
        ]
        df = pd.DataFrame(data, columns=columns)

        # Конвертация и сортировка дат
        df["DayDate"] = pd.to_datetime(df["DayDate"], format="%d-%m-%Y")
        # Сортировка по 'DayDate'
        df.sort_values(by="DayDate", inplace=True)
        # Конвертация обратно в строку для отображения
        df["DayDate"] = df["DayDate"].dt.strftime("%d-%m-%Y")
        # Создание файла Excel и отправка его в чат
        filename = f"schedule_master_{master_id}.xlsx"
        df.to_excel(filename, index=False)
        with open(filename, "rb") as file:
            await message.answer_document(
                document=file, caption=f"Вот график {chosen_master_name}"
            )
    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при обращении к базе данных")
        print(f"Database error: {e}")
    except Exception as e:
        await message.answer("Произошла неожиданная ошибка")
        print(f"General error: {e}")


######################################################################################################################


@dp.message_handler(lambda message: message.text == "Получить общий график")
async def choice_masters_in_schedule(message: types.Message, state: FSMContext):
    try:
        conn = sqlite3.connect("db")
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT
    strftime('%d-%m-%Y', datetime(substr(MasterTime.dayDate, 7, 4) || '-' ||
    substr(MasterTime.dayDate, 4, 2) || '-' || substr(MasterTime.dayDate, 1, 2))) AS DisplayDate,
    Masters.firstName AS Master,
    COALESCE(rec1.clientFirstName, MasterTime.start_0800) AS '08:00',
    COALESCE(rec2.clientFirstName, MasterTime.start_0900) AS '09:00',
    COALESCE(rec3.clientFirstName, MasterTime.start_1000) AS '10:00',
    COALESCE(rec4.clientFirstName, MasterTime.start_1100) AS '11:00',
    COALESCE(rec5.clientFirstName, MasterTime.start_1200) AS '12:00',
    COALESCE(rec6.clientFirstName, MasterTime.start_1300) AS '13:00',
    COALESCE(rec7.clientFirstName, MasterTime.start_1400) AS '14:00',
    COALESCE(rec8.clientFirstName, MasterTime.start_1500) AS '15:00',
    COALESCE(rec9.clientFirstName, MasterTime.start_1600) AS '16:00',
    COALESCE(rec10.clientFirstName, MasterTime.start_1700) AS '17:00',
    COALESCE(rec11.clientFirstName, MasterTime.start_1800) AS '18:00',
    COALESCE(rec12.clientFirstName, MasterTime.start_1900) AS '19:00'
FROM MasterTime
LEFT JOIN Masters ON MasterTime.masterId = Masters.id
LEFT JOIN Record as rec1 ON MasterTime.masterId = rec1.masterId AND MasterTime.dayDate = rec1.appointmentDate AND rec1.appointmentTime = '08:00'
LEFT JOIN Record as rec2 ON MasterTime.masterId = rec2.masterId AND MasterTime.dayDate = rec2.appointmentDate AND rec2.appointmentTime = '09:00'
LEFT JOIN Record as rec3 ON MasterTime.masterId = rec3.masterId AND MasterTime.dayDate = rec3.appointmentDate AND rec3.appointmentTime = '10:00'
LEFT JOIN Record as rec4 ON MasterTime.masterId = rec4.masterId AND MasterTime.dayDate = rec4.appointmentDate AND rec4.appointmentTime = '11:00'
LEFT JOIN Record as rec5 ON MasterTime.masterId = rec5.masterId AND MasterTime.dayDate = rec5.appointmentDate AND rec5.appointmentTime = '12:00'
LEFT JOIN Record as rec6 ON MasterTime.masterId = rec6.masterId AND MasterTime.dayDate = rec6.appointmentDate AND rec6.appointmentTime = '13:00'
LEFT JOIN Record as rec7 ON MasterTime.masterId = rec7.masterId AND MasterTime.dayDate = rec7.appointmentDate AND rec7.appointmentTime = '14:00'
LEFT JOIN Record as rec8 ON MasterTime.masterId = rec8.masterId AND MasterTime.dayDate = rec8.appointmentDate AND rec8.appointmentTime = '15:00'
LEFT JOIN Record as rec9 ON MasterTime.masterId = rec9.masterId AND MasterTime.dayDate = rec9.appointmentDate AND rec9.appointmentTime = '16:00'
LEFT JOIN Record as rec10 ON MasterTime.masterId = rec10.masterId AND MasterTime.dayDate = rec10.appointmentDate AND rec10.appointmentTime = '17:00'
LEFT JOIN Record as rec11 ON MasterTime.masterId = rec11.masterId AND MasterTime.dayDate = rec11.appointmentDate AND rec11.appointmentTime = '18:00'
LEFT JOIN Record as rec12 ON MasterTime.masterId = rec12.masterId AND MasterTime.dayDate = rec12.appointmentDate AND rec12.appointmentTime = '19:00'
ORDER BY datetime(substr(MasterTime.dayDate, 7, 4) || '-' ||
    substr(MasterTime.dayDate, 4, 2) || '-'  || substr(MasterTime.dayDate, 1, 2)), Masters.firstName;

        """
        )
        data = cursor.fetchall()
        conn.close()

        # Проверка на наличие данных
        if not data:
            await message.answer("Нет данных для отображения.")
            return

        columns = [
            "DayDate",
            "Master",
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
            "17:00",
            "18:00",
            "19:00",
        ]
        df = pd.DataFrame(data, columns=columns)

        # Конвертация и сортировка дат
        df["DayDate"] = pd.to_datetime(df["DayDate"], format="%d-%m-%Y")
        # Сортировка по 'DayDate'
        df.sort_values(by="DayDate", inplace=True)
        # Конвертация обратно в строку для отображения
        df["DayDate"] = df["DayDate"].dt.strftime("%d-%m-%Y")
        # Создание файла Excel и отправка его в чат
        filename = f"schedule_master_all.xlsx"
        df.to_excel(filename, index=False)
        with open(filename, "rb") as file:
            await message.answer_document(document=file, caption=f"Вот общий график")
    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при обращении к базе данных")
        print(f"Database error: {e}")
    except Exception as e:
        await message.answer("Произошла неожиданная ошибка")
        print(f"General error: {e}")


######################################################################################################################


@dp.message_handler(lambda message: message.text == "Редактировать график")
async def create_schedule(message: types.Message):
    try:
        initial_buttons = [
            "Редактировать дни",
            "Редактировать часы",
            "Назад",
        ]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in initial_buttons:
            keyboard.add(types.KeyboardButton(button))
        await message.answer("Что будешь делать?", reply_markup=keyboard)

    except Exception as e:
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова")
        print(f"Error in create_schedule: {e}")


######################################################################################################


@dp.message_handler(lambda message: message.text == "Назад")
async def go_back(message: types.Message):
    try:
        initial_buttons = [
            "Заполнить график (дни)",
            "Редактировать график",
            "Получить файл с записями",
            "Получить файл с графиком",
        ]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in initial_buttons:
            keyboard.add(types.KeyboardButton(button))
        await message.answer("Привет! Чего желаешь?", reply_markup=keyboard)

    except Exception as e:
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова")
        print(f"Error in create_schedule: {e}")


######################################################################################################
@dp.message_handler(lambda message: message.text == "Редактировать дни")
async def choose_master_change_day(message: types.Message):
    try:
        # Подключение к базе данных
        conn = sqlite3.connect("db")
        c = conn.cursor()

        # Выполнение запроса к базе данных и получение всех мастеров
        c.execute("SELECT id, firstName, lastName FROM Masters")
        masters = c.fetchall()

        # Создание списка кнопок с именами и фамилиями мастеров
        initial_buttons = [f"{master[1]} {master[2]}" for master in masters]
        initial_buttons.append("Отмена")

        global chosen_master_id
        # Сохраняем id мастеров в глобальной переменной
        chosen_master_id = {f"{master[1]} {master[2]}": master[0] for master in masters}

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in initial_buttons:
            keyboard.add(types.KeyboardButton(button))
        await message.answer("Выберите мастера", reply_markup=keyboard)
        await Form.master_2.set()

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при подключении к базе данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


@dp.message_handler(state=Form.master_2)
async def choose_date(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return

        chosen_master = message.text
        master_id = chosen_master_id.get(chosen_master)
        if not master_id:
            await message.answer(
                "Пожалуйста, выберите мастера из предложенных вариантов"
            )
            return

        await state.update_data(chosen_master=chosen_master, masterId=master_id)

        current_date = datetime.today()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        conn = sqlite3.connect("db")
        c = conn.cursor()

        date_buttons = []
        for i in range(30):
            date_check = (current_date + timedelta(days=i)).strftime("%d-%m-%Y")
            c.execute(
                """SELECT EXISTS(SELECT 1 FROM MasterTime WHERE masterId = ? AND dayDate = ? AND 
                        (start_0800 IS NOT NULL OR start_0900 IS NOT NULL OR start_1000 IS NOT NULL OR
                             start_1100 IS NOT NULL OR start_1200 IS NOT NULL OR start_1300 IS NOT NULL OR
                             start_1400 IS NOT NULL OR start_1500 IS NOT NULL OR start_1600 IS NOT NULL OR
                             start_1700 IS NOT NULL OR start_1800 IS NOT NULL OR start_1900 IS NOT NULL))""",
                (master_id, date_check),
            )
            if c.fetchone()[0]:
                date_buttons.append(types.KeyboardButton(date_check))
                if len(date_buttons) == 3:
                    keyboard.row(*date_buttons)
                    date_buttons = []

        if date_buttons:
            keyboard.row(*date_buttons)

        conn.close()

        cancel_button = types.KeyboardButton("Сохранить")
        keyboard.add(cancel_button)
        if keyboard.keyboard:
            await message.answer("Выберите дату для удаления", reply_markup=keyboard)
            await Form.date_2.set()
        else:
            await message.answer("Нет доступных дат для выбранного мастера")

    except sqlite3.Error as e:
        await message.answer("Возникла ошибка базы данных. Попробуйте снова позже")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка. Попробуйте снова")
        print(f"Unexpected error: {e}")


@dp.message_handler(state=Form.date_2)
async def delete_day_from_database(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Сохранить", "Отмена", "/start"):
            await cancel_handler(message, state)
            return

        user_data = await state.get_data()
        chosen_master = user_data["chosen_master"]
        master_id = chosen_master_id[chosen_master]
        date = message.text

        conn = sqlite3.connect("db")
        c = conn.cursor()
        try:
            c.execute(
                f"""UPDATE MasterTime SET
            start_0800 = NULL,
            start_0900 = NULL,
            start_1000 = NULL,
            start_1100 = NULL,
            start_1200 = NULL,
            start_1300 = NULL,
            start_1400 = NULL,
            start_1500 = NULL,
            start_1600 = NULL,
            start_1700 = NULL,
            start_1800 = NULL,
            start_1900 = NULL
        WHERE masterId = {master_id} AND dayDate = '{date}';"""
            )
            conn.commit()
            await message.answer("График успешно обновлен, день очищен!")
            await show_date_selection_2(message, state)
        except sqlite3.IntegrityError:
            await message.answer("Извините, график на этот день уже очищен")
            await show_date_selection_2(message, state)
        finally:
            conn.close()

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка базы данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


async def show_date_selection_2(message: types.Message, state: FSMContext):
    try:
        current_date = datetime.today()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        user_data = await state.get_data()
        chosen_master = user_data.get("chosen_master")

        if not chosen_master:
            await message.answer("Выбранного мастера нет в базе данных")
            return

        master_id = chosen_master_id.get(chosen_master)
        conn = sqlite3.connect("db")
        c = conn.cursor()

        date_buttons = []
        for i in range(30):
            date_check = (current_date + timedelta(days=i)).strftime("%d-%m-%Y")
            c.execute(
                """SELECT COUNT(*) from MasterTime WHERE masterId = ? 
                         AND dayDate = ? AND (start_0800 IS NOT NULL OR 
                                              start_0900 IS NOT NULL OR 
                                              start_1000 IS NOT NULL OR 
                                              start_1100 IS NOT NULL OR 
                                              start_1200 IS NOT NULL OR 
                                              start_1300 IS NOT NULL OR 
                                              start_1400 IS NOT NULL OR 
                                              start_1500 IS NOT NULL OR 
                                              start_1600 IS NOT NULL OR 
                                              start_1700 IS NOT NULL OR 
                                              start_1800 IS NOT NULL OR 
                                              start_1900 IS NOT NULL)""",
                (master_id, date_check),
            )
            available_slots = c.fetchone()[0]
            if available_slots > 0:
                date_buttons.append(types.KeyboardButton(date_check))
                if len(date_buttons) == 3:
                    keyboard.row(*date_buttons)
                    date_buttons = []

        if date_buttons:
            keyboard.row(*date_buttons)

        conn.close()

        back_button = types.KeyboardButton("Сохранить")
        keyboard.row(back_button)

        if keyboard.keyboard:
            await message.answer(
                "Выберите новую дату для очистки", reply_markup=keyboard
            )
            await Form.date_2.set()
        else:
            await message.answer("Нет доступных дат для выбранного мастера")

    except sqlite3.Error as db_error:
        await message.answer(
            "Возникла ошибка базы данных. Пожалуйста, попробуйте снова"
        )
        print(f"Database error encountered: {db_error}")

    except Exception as e:
        await message.answer(
            "Произошла неожиданная ошибка. Пожалуйста, попробуйте снова"
        )
        print(f"An unexpected error occurred: {e}")


######################################################################################################


@dp.message_handler(lambda message: message.text == "Редактировать часы")
async def choise_master_change_hours(message: types.Message):
    try:
        # Подключение к базе данных
        conn = sqlite3.connect("db")
        c = conn.cursor()

        # Выполнение запроса к базе данных и получение всех мастеров
        c.execute("SELECT id, firstName, lastName FROM Masters")
        masters = c.fetchall()

        # Создание списка кнопок с именами и фамилиями мастеров
        initial_buttons = [f"{master[1]} {master[2]}" for master in masters]
        initial_buttons.append("Отмена")

        global chosen_master_id
        # Сохраняем id мастеров в глобальной переменной
        chosen_master_id = {f"{master[1]} {master[2]}": master[0] for master in masters}

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in initial_buttons:
            keyboard.add(types.KeyboardButton(button))
        await message.answer("Выберите мастера", reply_markup=keyboard)
        await Form.master_3.set()

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при подключении к базе данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


@dp.message_handler(state=Form.master_3)
async def choose_date(message: types.Message, state: FSMContext):
    if message.text in ("Отмена", "/start"):
        await cancel_handler(message, state)
        return

    chosen_master = message.text
    master_id = chosen_master_id.get(chosen_master)
    if not master_id:
        await message.answer("Пожалуйста, выберите мастера из предложенных вариантов")
        return

    await state.update_data(chosen_master=chosen_master, masterId=master_id)

    current_date = datetime.today()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    conn = sqlite3.connect("db")
    c = conn.cursor()

    # Проверяем каждую дату на наличие доступного времени
    date_buttons = []
    for i in range(30):
        date_check = (current_date + timedelta(days=i)).strftime("%d-%m-%Y")
        c.execute(
            """SELECT EXISTS(SELECT 1 FROM MasterTime WHERE masterId = ? AND dayDate = ? AND 
                (start_0800 IS NOT NULL OR start_0900 IS NOT NULL OR start_1000 IS NOT NULL OR
                         start_1100 IS NOT NULL OR start_1200 IS NOT NULL OR start_1300 IS NOT NULL OR
                         start_1400 IS NOT NULL OR start_1500 IS NOT NULL OR start_1600 IS NOT NULL OR
                         start_1700 IS NOT NULL OR start_1800 IS NOT NULL OR start_1900 IS NOT NULL))""",
            (master_id, date_check),
        )
        if c.fetchone()[0]:
            date_buttons.append(types.KeyboardButton(date_check))
            if len(date_buttons) == 3:
                keyboard.row(*date_buttons)
                date_buttons = []

    if date_buttons:
        keyboard.row(*date_buttons)
    conn.close()

    back_button = types.KeyboardButton("Отмена")
    keyboard.add(back_button)

    if keyboard.keyboard:
        await message.answer("Выберите дату", reply_markup=keyboard)
        await Form.date_3.set()
    else:
        await message.answer("Нет доступных дат для выбранного мастера")


@dp.message_handler(state=Form.date_3)
async def choose_time(message: types.Message, state: FSMContext):
    if message.text in ("Отмена", "/start"):
        await cancel_handler(message, state)
        return
    chosen_date = message.text
    await state.update_data(chosen_date=chosen_date)
    user_data = await state.get_data()
    master_id = user_data.get("masterId")

    conn = sqlite3.connect("db")
    c = conn.cursor()
    c.execute(
        """SELECT start_0800,
                        start_0900,
                        start_1000,
                        start_1100,
                        start_1200,
                        start_1300,
                        start_1400,
                        start_1500,
                        start_1600,
                        start_1700,
                        start_1800,
                        start_1900
                 FROM MasterTime
                 WHERE masterId = ? AND dayDate = ?;""",
        (master_id, chosen_date),
    )
    times_row = c.fetchone()
    conn.close()
    current_datetime = datetime.now()
    chosen_datetime = datetime.strptime(chosen_date, "%d-%m-%Y")

    if not times_row:
        await message.answer("Нет доступного времени для изменения")
        return

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    time_buttons = []

    for i, available_time in enumerate(times_row):
        time_slot_datetime = current_datetime + timedelta(hours=i + 8)
        if available_time is not None and (
            time_slot_datetime.date() > current_datetime.date()
            or time_slot_datetime.time() > current_datetime.time()
        ):
            time_str = f"{i + 8:02d}:00"
            time_buttons.append(types.KeyboardButton(time_str))
            if len(time_buttons) == 3:
                keyboard.row(*time_buttons)
                time_buttons = []

    if time_buttons:
        keyboard.row(*time_buttons)

    back_button = types.KeyboardButton("Сохранить")
    keyboard.add(back_button)

    if not keyboard.keyboard:
        await message.answer("Нет доступных временных слотов для выбранной даты")
    else:
        await message.answer("Выберите время для удаления", reply_markup=keyboard)
        await Form.time_choice.set()


@dp.message_handler(state=Form.time_choice)
async def delete_time_in_database(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Сохранить", "Отмена", "/start"):
            await cancel_handler(message, state)
            return
        chosen_time = message.text
        user_data = await state.get_data()
        chosen_date = user_data.get("chosen_date")
        master_id = user_data.get("masterId")
        column_name = time_to_column.get(chosen_time)

        # await state.update_data(chosen_date=chosen_date)
        if master_id is None or chosen_date is None:
            await message.answer("Не установлена дата или мастер")
            return

        if not column_name:
            await message.answer("Вы выбрали некорректное время")
            return
        print(f"delete_time_in_database {user_data}")

        conn = sqlite3.connect("db")
        c = conn.cursor()
        try:
            sql_statement = f"UPDATE MasterTime SET {column_name} = NULL WHERE masterId = ? AND dayDate = ?;"
            c.execute(sql_statement, (master_id, chosen_date))
            conn.commit()
            await message.answer("График успешно обновлен!")

            await show_time_selection(message, state)
        except sqlite3.OperationalError as e:
            await message.answer(f"Возникла ошибка при обновлении базы данных: {e}")

            await show_time_selection(message, state)
        finally:
            conn.close()

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при подключении к базе данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


async def show_time_selection(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        chosen_date = user_data.get("chosen_date")
        master_id = user_data.get("masterId")
        conn = sqlite3.connect("db")
        c = conn.cursor()
        c.execute(
            """SELECT start_0800,
                            start_0900,
                            start_1000,
                            start_1100,
                            start_1200,
                            start_1300,
                            start_1400,
                            start_1500,
                            start_1600,
                            start_1700,
                            start_1800,
                            start_1900 FROM MasterTime WHERE masterId = ? AND dayDate = ?;""",
            (master_id, chosen_date),
        )
        times_row = c.fetchone()
        conn.close()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        time_buttons = []
        current_time = datetime.now()
        chosen_datetime = datetime.strptime(chosen_date, "%d-%m-%Y")
        available_slots_exist = False
        if times_row is not None:
            for i, available_time in enumerate(times_row):
                time_slot_datetime = current_time + timedelta(hours=i + 8)
                if available_time is not None and (
                    time_slot_datetime.date() != current_time.date()
                    or time_slot_datetime.time() > current_time.time()
                ):
                    time_str = f"{i + 8:02d}:00"
                    time_buttons.append(types.KeyboardButton(time_str))
                    available_slots_exist = (
                        True  # Обновляем переменную, если нашли доступный слот
                    )
                    if len(time_buttons) == 3:
                        keyboard.row(*time_buttons)
                        time_buttons = []
            if time_buttons:
                keyboard.row(*time_buttons)
        else:
            await message.answer("Нет доступных временных слотов для этой даты")
            return

        back_button = types.KeyboardButton("Сохранить")
        keyboard.row(back_button)
        await message.answer("Выберите время для удаления", reply_markup=keyboard)
        await Form.time_choice.set()

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при подключении к базе данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


######################################################################################################


@dp.message_handler(lambda message: message.text == "Заполнить график (дни)")
async def choose_master_create_day(message: types.Message, state: FSMContext):
    try:
        # Подключение к базе данных
        conn = sqlite3.connect("db")
        c = conn.cursor()

        # Выполнение запроса к базе данных и получение всех мастеров
        c.execute("SELECT id, firstName, lastName FROM Masters")
        masters = c.fetchall()

        # Создание списка кнопок с именами и фамилиями мастеров
        initial_buttons = [f"{master[1]} {master[2]}" for master in masters]
        initial_buttons.append("Отмена")

        global chosen_master_id
        # Сохраняем id мастеров в глобальной переменной
        chosen_master_id = {f"{master[1]} {master[2]}": master[0] for master in masters}

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in initial_buttons:
            keyboard.add(types.KeyboardButton(button))
        await message.answer("Выберите мастера", reply_markup=keyboard)
        # await state.finish()
        await Form.master_1.set()

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при подключении к базе данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


@dp.message_handler(state=Form.master_1)
async def choose_date(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return

        chosen_master = message.text
        master_id = chosen_master_id.get(chosen_master)
        if not master_id:
            await message.answer(
                "Пожалуйста, выберите мастера из предложенных вариантов"
            )
            return

        await state.update_data(chosen_master=chosen_master, masterId=master_id)

        current_date = datetime.today()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        conn = sqlite3.connect("db")
        c = conn.cursor()

        dates_with_no_appointments = []
        for i in range(30):
            date_to_format = current_date + timedelta(days=i)
            date_check = date_to_format.strftime("%d-%m-%Y")

            c.execute(
                """SELECT m.dayDate IS NULL OR (
                                 m.start_0800 IS NULL AND m.start_0900 IS NULL AND 
                                 m.start_1000 IS NULL AND m.start_1100 IS NULL AND
                                 m.start_1200 IS NULL AND m.start_1300 IS NULL AND 
                                 m.start_1400 IS NULL AND m.start_1500 IS NULL AND
                                 m.start_1600 IS NULL AND m.start_1700 IS NULL AND 
                                 m.start_1800 IS NULL AND m.start_1900 IS NULL
                             )
                             FROM (SELECT ? AS dayDate) AS d
                             LEFT JOIN MasterTime AS m ON m.masterId = ? AND m.dayDate = d.dayDate;
                          """,
                (date_check, master_id),
            )

            result = c.fetchone()
            if result and result[0]:
                dates_with_no_appointments.append(date_check)

        conn.close()

        for i in range(0, len(dates_with_no_appointments), 3):
            date_buttons = [
                types.KeyboardButton(date)
                for date in dates_with_no_appointments[i : i + 3]
            ]
            keyboard.add(*date_buttons)

        back_button = types.KeyboardButton("Сохранить")
        keyboard.add(back_button)

        if dates_with_no_appointments:
            await message.answer(
                "Выберите дату с пустым графиком", reply_markup=keyboard
            )
            await Form.date_1.set()
        else:
            await message.answer(
                "Не найдены даты без записи. Пожалуйста, выберите другого мастера или отмените"
            )

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при обращении к базе данны")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла неожиданная ошибка")
        print(f"General error: {e}")


@dp.message_handler(state=Form.date_1)
async def insert_into_database(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Сохранить", "Отмена", "/start"):
            await cancel_handler(message, state)
            return

        user_data = await state.get_data()
        chosen_master = user_data["chosen_master"]
        master_id = chosen_master_id[chosen_master]
        date = message.text

        conn = sqlite3.connect("db")
        c = conn.cursor()
        try:
            c.execute(
                """INSERT OR REPLACE INTO MasterTime (masterId, dayDate,
                            start_0800,
                            start_0900,
                            start_1000,
                            start_1100,
                            start_1200,
                            start_1300,
                            start_1400,
                            start_1500,
                            start_1600,
                            start_1700,
                            start_1800,
                            start_1900)
                         VALUES (?, ?, '08:00', '09:00', '10:00', '11:00', '12:00',
                                 '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00');""",
                (master_id, date),
            )
            conn.commit()
            await message.answer("График успешно обновлен!")
            await show_date_selection(message, state)
        except sqlite3.IntegrityError:
            await message.answer(
                "Извините, но запись на эту дату для данного мастера уже существует"
            )
            await show_date_selection(message, state)
        finally:
            conn.close()

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при подключении к базе данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


async def show_date_selection(message: types.Message, state: FSMContext):
    try:
        current_date = datetime.today()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        user_data = await state.get_data()
        chosen_master = user_data.get("chosen_master")

        if not chosen_master:
            await message.answer("Ошибка: мастер не выбран")
            return

        master_id = chosen_master_id.get(chosen_master)
        conn = sqlite3.connect("db")
        c = conn.cursor()

        date_buttons = []
        for i in range(30):
            date_to_format = current_date + timedelta(days=i)
            date_check = date_to_format.strftime("%d-%m-%Y")
            c.execute(
                """SELECT MAX(m.dayDate IS NULL OR (
                             m.start_0800 IS NULL AND m.start_0900 IS NULL AND 
                             m.start_1000 IS NULL AND m.start_1100 IS NULL AND
                             m.start_1200 IS NULL AND m.start_1300 IS NULL AND 
                             m.start_1400 IS NULL AND m.start_1500 IS NULL AND
                             m.start_1600 IS NULL AND m.start_1700 IS NULL AND 
                             m.start_1800 IS NULL AND m.start_1900 IS NULL
                         )) FROM (SELECT ? AS dayDate) AS d
                         LEFT JOIN MasterTime AS m ON m.masterId = ? AND m.dayDate = d.dayDate;
                      """,
                (date_check, master_id),
            )

            result = c.fetchone()
            if result is not None and result[0]:
                date_buttons.append(types.KeyboardButton(date_check))
                if len(date_buttons) == 3:
                    keyboard.row(*date_buttons)
                    date_buttons = []
        if date_buttons:
            keyboard.row(*date_buttons)
        conn.close()
        back_button = types.KeyboardButton("Сохранить")
        keyboard.row(back_button)
        if keyboard.keyboard:
            await message.answer(
                "Выберите дату с пустым графиком", reply_markup=keyboard
            )
            await Form.date_1.set()
        else:
            await message.answer("Нет дат с полностью свободным графиком")

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при обращении к базе данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла неожиданная ошибка")
        print(f"General error: {e}")


######################################################################################################


@dp.message_handler(lambda message: message.text == "Получить файл с записями")
async def get_file_records(message: types.Message):
    try:
        conn = sqlite3.connect("db")
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT
        Masters.firstName AS Master,
        Record.appointmentDate AS Day,
        Record.appointmentTime AS Time,
        Services.serviceName AS Service,
        Record.clientFirstName AS ClientName,
        Record.clientPhoneNumber AS ClientPhone
    FROM
        Record
    LEFT OUTER JOIN
        Masters ON Record.masterId = Masters.id
    LEFT OUTER JOIN
        Services ON Record.serviceId = Services.id
    ORDER BY
        Masters.firstName,
        Record.appointmentDate,
        Record.appointmentTime;
            """
        )
        data = cursor.fetchall()

        # Проверка на наличие данных
        if not data:
            await message.answer("Нет данных для отображения")
            return

        df = pd.DataFrame(
            data,
            columns=["Master", "Day", "Time", "Service", "ClientName", "ClientPhone"],
        )

        # Создаем файл Excel
        filename = "schedule.xlsx"
        writer = pd.ExcelWriter(filename, engine="xlsxwriter")
        df.to_excel(writer, index=False)
        writer.close()

        # Отправляем файл в чат
        with open(filename, "rb") as file:
            await message.answer_document(document=file, caption="Вот ваш график")

        conn.close()

    except sqlite3.Error as e:
        await message.answer("Произошла ошибка при обращении к базе данных")
        print(f"Database error: {e}")

    except Exception as e:
        await message.answer("Произошла неожиданная ошибка")
        print(f"General error: {e}")


######################################################################################################


@dp.message_handler(state="*", commands="Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await send_welcome(message)


@dp.message_handler(state="*", commands="Сохранить")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await send_welcome(message)


# @dp.message_handler(lambda message: message.text == "Добавить сотрудника")
# async def add_employee(message: types.Message):
#     # Create the keyboard with the "Отмена" button
#     keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
#     cancel_button = types.KeyboardButton("Отмена")
#     keyboard.add(cancel_button)
#     if message.text == "Отмена":
#         await cancel_handler(message)
#         return
#     # Send message with keyboard
#     await message.answer(
#         "Введите имя, фамилию и опыт работы сотрудника в формате 'Имя Фамилия Опыт'",
#         reply_markup=keyboard,
#     )
#     await Form.employee.set()
#
#
# @dp.message_handler(state=Form.employee)
# async def get_employee_data(message: types.Message, state: FSMContext):
#     conn = sqlite3.connect("db")
#     cursor = conn.cursor()
#     keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
#     cancel_button = types.KeyboardButton("Отмена")
#     keyboard.add(cancel_button)
#     if message.text == "Отмена":
#         await cancel_handler(
#             message, state
#         )  ### Почему то не работает ссылка на функцию
#         return
#     employee_data = message.text.split()
#     if len(employee_data) != 3:
#         await message.answer(
#             "Пожалуйста, введите данные в правильном формате: 'Имя Фамилия Опыт'"
#         )
#         return
#
#     first_name, last_name, experience = employee_data
#     if not experience.isdigit():
#         await message.answer(
#             "Опыт работы должен быть числом. Пожалуйста, введите данные в правильном формате: 'Имя Фамилия Опыт'"
#         )
#         return
#
#     experience = int(experience)
#
#     # Проверяем, есть ли уже такой сотрудник в базе данных
#     cursor.execute(
#         "SELECT * FROM Masters WHERE firstName = ? AND lastName = ?",
#         (first_name, last_name),
#     )
#     existing_employee = cursor.fetchone()
#
#     if existing_employee:
#         await message.answer("Сотрудник с таким именем и фамилией уже существует.")
#         return
#
#     # Добавляем рабоника в БД
#     cursor.execute(
#         "INSERT INTO Masters (firstName, lastName, experienceYears) VALUES (?, ?, ?)",
#         (first_name, last_name, experience),
#     )
#     conn.commit()
#
#     await message.answer(
#         f"Сотрудник {first_name} {last_name} с опытом работы {experience} год(а) успешно добавлен."
#     )
#
#     await state.finish()
#     conn.close()
#     await state.reset_state()
#
#     @dp.message_handler(state="*", commands="Отмена")
#     async def cancel_handler(message: types.Message, state: FSMContext):
#         # Подключение к базе данных
#         conn = sqlite3.connect("db")
#
#         # Закрытие соединения с базой данных
#         conn.close()
#
#         # Очистка состояния формы
#         await state.finish()
#         initial_buttons = [
#             "Заполнить/редактировать график",
#             "Получить файл с графиком",
#             "Добавить сотрудника",
#         ]
#         keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
#         for button in initial_buttons:
#             keyboard.add(types.KeyboardButton(button))
#         # Возврат в начальное меню
#         await message.answer(
#             "Вы отменили текущий процесс и вернулись в главное меню. Чего желаете?",
#             reply_markup=types.ReplyKeyboardRemove(),
#         )


if __name__ == "__main__":
    from aiogram import executor

    try:
        loop = asyncio.get_event_loop()
        bot_info = loop.run_until_complete(bot.get_me())
        print(f"Bot info: {bot_info}")
    except Exception as e:
        print(f"Bot is already running: {str(e)}")
        exit(0)
    executor.start_polling(dp)
