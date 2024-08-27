import asyncio
import json
import os
import re
import smtplib
import sqlite3
import sys
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import *
from service_confirmation_to_mail import send_confirmation_email

storage = MemoryStorage()
bot = Bot(token=token_bot_client, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    master_first_choice_1 = State()
    service_second_choice_1 = State()
    choice_date_after_service_1 = State()
    time_choice_1 = State()
    name_client_1 = State()
    phone_1 = State()
    email_1 = State()
    service_first_choice_2 = State()
    master_second_choice_2 = State()
    choice_date_after_master_2 = State()
    time_choice_2 = State()
    name_client_2 = State()
    phone_2 = State()
    email_2 = State()
    remind_1 = State()
    remind_2 = State()


@dp.message_handler(commands="start")
async def send_welcome(message: types.Message):
    try:
        photo_path = "image/start.jpg"
        start_buttons = ["Выбрать мастера", "Выбрать услугу", "Информация"]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in start_buttons:
            keyboard.add(types.KeyboardButton(button))
        with open(photo_path, "rb") as photo:
            await message.answer_photo(photo, reply_markup=keyboard)
    except Exception as e:
        print(f"An error occurred: {e}")
        await message.answer("Извините, произошла ошибка. Попробуйте снова")


#####################################################################################################################
@dp.message_handler((lambda message: message.text == "Информация"))
async def info(message: types.Message):
    # keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # keyboard.add(types.KeyboardButton("Назад"))
    await message.answer(
        "Парикмахерская 'HAIR SALMING LIICING'\n"
        "📞 8(913)-914-83-30\n"
        "🗺 ул. Красный проспект, 122\n"
        "Чтобы отменить запись напишите администратору: @Petrmameev\n"
        "Техническая проблема: @Petrmameev\n"
        "Хочу такого же бота: @Petrmameev"
    )


#####################################################################################################################


@dp.message_handler((lambda message: message.text == "Назад"))
async def back(message: types.Message):
    try:
        start_buttons = ["Выбрать мастера", "Выбрать услугу", "Информация"]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in start_buttons:
            keyboard.add(types.KeyboardButton(button))
        await message.answer("Изображение компании", reply_markup=keyboard)

    except Exception as e:
        print(f"An error occurred: {e}")
        await message.answer("Извините, произошла ошибка. Попробуйте снова")


#####################################################################################################################
@dp.message_handler(lambda message: message.text == "Выбрать услугу")
async def choice_service(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return
        conn = sqlite3.connect("db")
        c = conn.cursor()
        try:
            c.execute("SELECT id, servicename FROM Services")
            services = c.fetchall()
        finally:
            conn.close()
        print(services)
        service_dict = {service[1]: service[0] for service in services}

        await state.update_data(service_dict=service_dict)
        print(services)
        initial_buttons = [f"{service[1]} " for service in services]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for button in initial_buttons:
            keyboard.add(types.KeyboardButton(button))
        cancel_button = types.KeyboardButton("Отмена")
        keyboard.add(cancel_button)
        await message.answer("Выберите услугу", reply_markup=keyboard)
        await Form.service_first_choice_2.set()

    except sqlite3.OperationalError as e:
        await message.answer(
            "Произошла ошибка при получении списка услуг. Попробуйте снова позже"
        )
        print(f"SQLite operational error occurred: {e}")
    except Exception as e:
        # Catch all other exceptions and provide a user-friendly error message
        await message.answer("Извините, произошла ошибка. Попробуйте снова")
        print(f"Произошла непредвиденная ошибка: {e}")


@dp.message_handler(state=Form.service_first_choice_2)
async def choice_masters_after_service(message: types.Message, state: FSMContext):
    try:
        chosen_service_name = message.text
        if chosen_service_name in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return

        user_data = await state.get_data()
        service_dict = user_data.get("service_dict", {})
        print(service_dict)
        service_id = service_dict.get(chosen_service_name)

        if service_id is None:
            await message.answer("Возникла ошибка: мастер не найден")
            return

        conn = sqlite3.connect("db")
        try:
            c = conn.cursor()
            c.execute(
                """SELECT m.id, m.firstName, m.lastName, ms.price
                         FROM Masters AS m
                         JOIN MasterServices AS ms ON m.id = ms.masterId
                         WHERE ms.serviceId = ?""",
                (service_id,),
            )
            masters = c.fetchall()

        finally:
            conn.close()
        print(masters)
        if not masters:
            await message.answer("У выбранную услугу мастер не оказывает")
            return

        await state.update_data(
            chosen_service=chosen_service_name, serviceId=service_id
        )

        master_dict = {f"{info[1]} {info[2]}": info[0] for info in masters}
        await state.update_data(master_dict=master_dict)
        print(master_dict)

        initial_buttons = [
            f"{info[1]} {info[2]} - Цена: {int(info[3]) if info[3] == int(info[3]) else info[3]}₽"
            for info in masters
        ]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        for button in initial_buttons:
            keyboard.add(types.KeyboardButton(button))

        cancel_button = types.KeyboardButton("Отмена")
        keyboard.add(cancel_button)

        await message.answer("Выберите мастера и узнайте цену", reply_markup=keyboard)
        await Form.master_second_choice_2.set()

    except sqlite3.OperationalError as e:
        await message.answer(
            "Извините, произошла ошибка базы данных. Попробуйте еще раз"
        )

    except Exception as e:
        await message.answer("Извините, произошла неизвестная ошибка. Попробуйте снова")
        print(f"An error occurred: {e}")


@dp.message_handler(state=Form.master_second_choice_2)
async def choose_date_after_master(message: types.Message, state: FSMContext):
    try:
        chosen_master_name = message.text
        if chosen_master_name in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return
        user_data = await state.get_data()
        master_dict = user_data.get("master_dict", {})
        service_id = user_data.get("serviceId")
        master_id = master_dict.get(chosen_master_name.split(" - ")[0])
        if master_id is None:
            await message.answer("Ошибка: Информация об мастере не найдена")
            return

        await state.update_data(masterId=master_id)
        print(master_id)
        print(service_id)
        if not service_id:
            await message.answer("Возникла ошибка: информация о услуге не была найдена")
            return

        conn = sqlite3.connect("db")
        c = conn.cursor()
        c.execute("SELECT link_foto, description FROM Masters WHERE id = ?", (master_id,))
        master_record = c.fetchone()
        if master_record:
            master_foto = master_record[0]
            description = master_record[1]
            print(master_foto)
            print(description)
        else:
            await message.answer("Информация о мастере не найдена.")
            return

        if master_foto:
            photo_path = os.path.abspath(master_foto)  # Adjust the path as needed
            with open(photo_path, "rb") as photo:
                await message.answer_photo(photo=photo, caption=f"{chosen_master_name} - {description}")



        current_date = datetime.today()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        conn = sqlite3.connect("db")
        try:
            c = conn.cursor()
            date_buttons = []
            for i in range(30):
                date_check = (current_date + timedelta(days=i)).strftime("%d-%m-%Y")
                c.execute(
                    """SELECT EXISTS(
                                SELECT 1 FROM MasterTime
                                WHERE masterId = ? AND dayDate = ? AND
                                (start_0800 IS NOT NULL OR start_0900 IS NOT NULL OR start_1000 IS NOT NULL OR
                                 start_1100 IS NOT NULL OR start_1200 IS NOT NULL OR start_1300 IS NOT NULL OR
                                 start_1400 IS NOT NULL OR start_1500 IS NOT NULL OR start_1600 IS NOT NULL OR
                                 start_1700 IS NOT NULL OR start_1800 IS NOT NULL OR start_1900 IS NOT NULL)
                            )""",
                    (master_id, date_check),
                )
                if c.fetchone()[0]:
                    date_buttons.append(types.KeyboardButton(date_check))
                    if len(date_buttons) == 3:
                        keyboard.row(*date_buttons)
                        date_buttons = []
            if date_buttons:
                keyboard.row(*date_buttons)
        finally:
            conn.close()

        cancel_button = types.KeyboardButton("Отмена")
        keyboard.add(cancel_button)

        if keyboard.keyboard:
            await message.answer("Выберите дату", reply_markup=keyboard)
            await Form.choice_date_after_master_2.set()
        else:
            await message.answer("Нет доступных дат для выбранного мастера")
            await Form.choice_date_after_master_2.set()

    except sqlite3.OperationalError as op_err:
        await message.answer(
            "Возникла проблема с базой данных. Пожалуйста, попробуйте еще раз позже"
        )
        print(f"Database error: {op_err}")

    except Exception as e:
        await message.answer("Извините, произошла ошибка. Попробуйте снова")
        print(f"An unexpected error occurred: {e}")


@dp.message_handler(state=Form.choice_date_after_master_2)
async def choose_time_after_date_after_master(
    message: types.Message, state: FSMContext
):
    try:
        selected_date = message.text
        if selected_date in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return

        await state.update_data(selected_date=selected_date)
        user_data = await state.get_data()
        master_id = user_data.get("masterId")
        service_id = user_data.get("serviceId")
        print(master_id)
        print(service_id)
        if not master_id:
            await message.answer(
                "Возникла ошибка: информация о мастере не была найдена"
            )
            return
        conn = sqlite3.connect("db")
        try:
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
                         WHERE masterId = ? AND dayDate = ?""",
                (master_id, selected_date),
            )
            times = c.fetchone()

            c.execute(
                """SELECT appointmentTime
                             FROM Record
                             WHERE masterId = ? AND appointmentDate = ?""",
                (master_id, selected_date),
            )

            booked_times = [time[0] for time in c.fetchall()]

        finally:
            conn.close()

        now = datetime.now()

        choisen_date_datetime = datetime.strptime(selected_date, "%d-%m-%Y")
        time_threshold = (
            (now + timedelta(minutes=10)).strftime("%H:%M")
            if now.date() == choisen_date_datetime.date()
            else "00:00"
        )
        available_times = [
            time
            for time in times
            if time
            and (now.date() < choisen_date_datetime.date() or time > time_threshold)
            and time not in booked_times
        ]

        if not available_times:
            await message.answer(
                "Нет доступных времен для записи. Пожалуйста, выберите другую дату"
            )
            return

        await state.update_data(available_times=available_times)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        times_row = []
        for time in available_times:
            if time:
                times_row.append(types.KeyboardButton(time))
                if len(times_row) == 3:
                    keyboard.row(*times_row)
                    times_row = []
        if times_row:
            keyboard.row(*times_row)
        cancel_button = types.KeyboardButton("Отмена")
        keyboard.add(cancel_button)
        await message.answer("Выберите время для записи", reply_markup=keyboard)
        await Form.time_choice_2.set()

    except sqlite3.OperationalError as db_err:
        await message.answer(
            "Произошла ошибка базы данных. Пожалуйста, попробуйте позже"
        )
        print(f"Database error: {db_err}")

    except Exception as err:
        await message.answer(
            "Произошла неожиданная ошибка. Пожалуйста, попробуйте позже"
        )
        print(f"Unexpected error: {err}")


@dp.message_handler(state=Form.time_choice_2)
async def input_name_client(message: types.Message, state: FSMContext):
    try:
        choicen_time = message.text
        if choicen_time in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return
        user_data = await state.get_data()
        available_times = user_data["available_times"]
        if choicen_time not in available_times:
            await message.answer(
                "Выбранное время недоступно или уже прошло. Выберите время из предложенных вариантов."
            )
            return
        await state.update_data(appointmentTime=choicen_time)
        await state.update_data(phone=message.text)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("Отмена")
        )
        await message.answer("Введите Ваше имя", reply_markup=keyboard)
        await Form.name_client_2.set()
    except Exception as e:
        await message.answer(
            "Произошла ошибка при обработке вашего времени. Попробуйте еще раз"
        )
        print(f"Error in input_name_client: {e}")


@dp.message_handler(state=Form.name_client_2)
async def input_phone(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Отмена", "/start"):
            await state.finish()
            await send_welcome(message)
            return
        print(message.text)
        await state.update_data(name=message.text)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("Отмена")
        )
        await message.answer("Введите ваш номер телефона", reply_markup=keyboard)
        await Form.phone_2.set()
    except Exception as e:
        await message.answer(
            "Произошла ошибка при обработке вашего имени. Попробуйте еще раз"
        )
        print(f"Error in input_phone: {e}")


@dp.message_handler(state=Form.phone_2)
async def check_phone(message: types.Message, state: FSMContext):
    try:
        choise_name = message.text
        print(choise_name)
        if choise_name in ("Отмена", "/start"):
            await state.finish()
            await send_welcome(message)
            return
        phone_number = message.text
        if not is_valid_phone(phone_number):
            await message.answer(
                "Введен некорректный номер телефона. Пожалуйста, введите еще раз"
            )
            return
        await state.update_data(phone=phone_number)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("Отмена")
        )
        await message.answer("Введите ваш email", reply_markup=keyboard)
        await Form.email_2.set()
    except Exception as e:
        await message.answer(
            "Произошла ошибка при проверке вашего телефона. Попробуйте еще раз"
        )
        print(f"Error in check_phone: {e}")


@dp.message_handler(state=Form.email_2)
async def write_client_and_save_record(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Отмена", "/start"):
            await state.finish()
            await send_welcome(message)
            return

        email = message.text
        if not is_valid_email(email):
            await message.answer(
                "Введен некорректный адрес почты. Пожалуйста, введите еще раз"
            )
            return
        await state.update_data(email_clients=email)

        user_data = await state.get_data()
        client_first_name = user_data.get("name")
        client_phone_number = user_data.get("phone")
        master_id = user_data.get("masterId")
        service_id = user_data.get("serviceId")
        appointment_date = user_data.get("selected_date")
        appointment_time = user_data.get("appointmentTime")

        if service_id is None:
            await message.answer("Ошибка: Информация об услуге не найдена")
            return

        with sqlite3.connect("db") as conn:
            c = conn.cursor()
            c.execute(
                """SELECT appointmentTime FROM Record 
                         WHERE masterId = ? AND appointmentDate = ? AND appointmentTime = ?""",
                (master_id, appointment_date, appointment_time),
            )
            if c.fetchone():
                raise Exception("Вы не успели, на это время уже кто-то записался.")

            c.execute(
                """INSERT INTO Clients (firstName, phoneNumber, eMail) VALUES (?, ?, ?)""",
                (client_first_name, client_phone_number, email),
            )
            client_id = c.lastrowid

            c.execute(
                """SELECT firstName, lastName FROM Masters WHERE id = ?""", (master_id,)
            )
            if master_record := c.fetchone():
                firstName, lastName = master_record[0], master_record[1]

            c.execute(
                """SELECT serviceName FROM Services WHERE id = ?""", (service_id,)
            )
            if service_record := c.fetchone():
                serviceName = service_record[0]

            c.execute(
                """SELECT price FROM MasterServices WHERE masterId = ? AND  serviceId = ?""",
                (master_id, service_id),
            )
            if price_record := c.fetchone():
                price = price_record[0]

            reminder_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            reminder_times = [
                ("24 часа", 24),
                ("12 часов", 12),
                ("6 часов", 6),
                ("3 часа", 3),
                ("2 часа", 2),
                ("1 час", 1),
            ]
            buttons = [
                types.KeyboardButton(text=f"Напомнить за {label}")
                for label, hours in reminder_times
            ]
            while buttons:
                button_pair = buttons[:2]
                reminder_keyboard.add(*button_pair)
                buttons = buttons[2:]
            dont_remind = types.KeyboardButton("Не напоминать")
            reminder_keyboard.add(dont_remind)
            await Form.remind_2.set()

            c.execute(
                """INSERT INTO Record (clientFirstName, clientPhoneNumber, masterId,
                         serviceId, appointmentDate, appointmentTime) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    client_first_name,
                    client_phone_number,
                    master_id,
                    service_id,
                    appointment_date,
                    appointment_time,
                ),
            )
            conn.commit()
        await message.answer(
            f"Вы записаны на услугу {serviceName} к мастеру {firstName} {lastName}"
            f" на {appointment_date} в {appointment_time}, стоимость услуги:{int(price) 
                             if price == int(price) else price}₽",
            reply_markup=reminder_keyboard,
        )
        await send_confirmation_email(
            client_first_name,
            email,
            appointment_date,
            appointment_time,
            serviceName,
            price,
            firstName,
            lastName,
        )
    except sqlite3.IntegrityError as ie:
        await message.answer(
            "Ошибка базы данных при сохранении записи. Проверьте введенные данные и попробуйте снова"
        )
        print(f"Database IntegrityError: {ie}")

    except sqlite3.OperationalError as oe:
        await message.answer(
            "Ошибка операционной базы данных. Пожалуйста, попробуйте еще раз позже"
        )
        print(f"Database OperationalError: {oe}")

    except Exception as e:
        await message.answer(str(e))
        print(f"Unexpected error: {e}")


@dp.message_handler(state=Form.remind_2)
async def set_remind_in_db(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        client_first_name = user_data.get("name")
        client_phone_number = user_data.get("phone")
        appointment_date = user_data.get("selected_date")
        appointment_time = user_data.get("appointmentTime")
        if message.text in ("Не напоминать", "Отмена", "/start"):
            await state.finish()
            await send_welcome(message)
            return
        else:
            remind_text = message.text.split()
            print(remind_text)
            remind = int(remind_text[2]) if len(remind_text) == 4 else 0

        with sqlite3.connect("db") as conn:
            c = conn.cursor()
            c.execute(
                """UPDATE Record SET remind = ? WHERE clientPhoneNumber = ? AND appointmentDate = ? AND appointmentTime = ?""",
                (remind, client_phone_number, appointment_date, appointment_time),
            )
            conn.commit()

        await state.finish()
        await message.answer(
            f"Отправим вам напоминалку на почту за {remind_text[2]} час(а)."
        )
        await send_welcome(message)
        return
    except sqlite3.IntegrityError as ie:
        await message.answer(
            "Ошибка базы данных при сохранении записи. Проверьте введенные данные и попробуйте снова"
        )
        print(f"Database IntegrityError: {ie}")
    except sqlite3.OperationalError as oe:
        await message.answer(
            "Ошибка операционной базы данных. Пожалуйста, попробуйте еще раз позже"
        )
        print(f"Database OperationalError: {oe}")
    except Exception as e:
        await message.answer(str(e))
        print(f"Unexpected error: {e}")


##################################################################################################################


@dp.message_handler(lambda message: message.text == "Выбрать мастера")
async def choice_masters(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return
        conn = sqlite3.connect("db")
        c = conn.cursor()
        c.execute("SELECT id, firstName, lastName, link_foto, description FROM Masters")
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
        await Form.master_first_choice_1.set()

    except sqlite3.OperationalError as e:
        await message.answer(
            "Произошла ошибка при получении списка мастеров. Попробуйте снова позже"
        )
        print(f"SQLite operational error occurred: {e}")
    except Exception as e:
        await message.answer("Извините, произошла ошибка. Попробуйте снова")
        print(f"Произошла непредвиденная ошибка: {e}")


@dp.message_handler(state=Form.master_first_choice_1)
async def choice_service_after_master(message: types.Message, state: FSMContext):
    try:
        chosen_master_name = message.text
        if chosen_master_name in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return

        user_data = await state.get_data()
        master_dict = user_data.get("master_dict", {})
        master_id = master_dict.get(chosen_master_name)

        if master_id is None:
            await message.answer("Возникла ошибка: мастер не найден")
            return
        print(master_id)

        #добавление фото и информации о мастере в меню выбора сервиса

        conn = sqlite3.connect("db")
        c = conn.cursor()
        c.execute("SELECT link_foto, description FROM Masters WHERE id = ?", (master_id,))
        master_record = c.fetchone()
        if master_record:
            master_foto = master_record[0]
            description = master_record[1]
            print(master_foto)
            print(description)
        else:
            await message.answer("Информация о мастере не найдена.")
            return

        if master_foto:
            photo_path = os.path.abspath(master_foto)  # Adjust the path as needed
            with open(photo_path, "rb") as photo:
                await message.answer_photo(photo=photo, caption=f"{chosen_master_name} - {description}")




        conn.close()
        conn = sqlite3.connect("db")
        try:
            c = conn.cursor()
            c.execute(
                """SELECT Services.serviceName, MasterServices.price, MasterServices.serviceId
                         FROM MasterServices
                         JOIN Services ON MasterServices.serviceId = Services.id
                         WHERE MasterServices.masterId = ?;""",
                (master_id,),
            )
            services = c.fetchall()
        finally:
            conn.close()
            print(services)

        if not services:
            await message.answer("У выбранного мастера нет доступных услуг")
            return

        await state.update_data(chosen_master=chosen_master_name, masterId=master_id)

        service_dict = {f"{service[0]}": service[2] for service in services}
        await state.update_data(service_dict=service_dict)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        # Update the loop to handle service_name, price, and service_id
        for service_name, price, service_id in services:
            button_text = f"{service_name} - Цена: {int(price) if price == int(price) else price}₽"
            keyboard.add(types.KeyboardButton(button_text))

        cancel_button = types.KeyboardButton("Отмена")
        keyboard.add(cancel_button)
        await message.answer("Выберите услугу", reply_markup=keyboard)
        await Form.service_second_choice_1.set()
    except sqlite3.OperationalError as e:
        await message.answer(
            "Извините, произошла ошибка базы данных. Попробуйте еще раз"
        )

    except Exception as e:
        await message.answer("Извините, произошла неизвестная ошибка. Попробуйте снова")
        print(f"An error occurred: {e}")


@dp.message_handler(state=Form.service_second_choice_1)
async def choose_date_after_service(message: types.Message, state: FSMContext):
    try:
        chosen_service_name = message.text
        if chosen_service_name in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return
        user_data = await state.get_data()
        service_dict = user_data.get("service_dict", {})
        master_id = user_data.get("masterId")

        service_id = service_dict.get(chosen_service_name.split(" - ")[0])
        if service_id is None:
            await message.answer("Ошибка: Информация об услуге не найдена")
            return

        await state.update_data(serviceId=service_id)
        print(master_id)
        print(service_id)
        if not master_id:
            await message.answer(
                "Возникла ошибка: информация о мастере не была найдена"
            )
            return
        current_date = datetime.today()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        conn = sqlite3.connect("db")
        try:
            c = conn.cursor()
            date_buttons = []
            for i in range(30):
                date_check = (current_date + timedelta(days=i)).strftime("%d-%m-%Y")
                c.execute(
                    """SELECT EXISTS(
                                SELECT 1 FROM MasterTime
                                WHERE masterId = ? AND dayDate = ? AND
                                (start_0800 IS NOT NULL OR start_0900 IS NOT NULL OR start_1000 IS NOT NULL OR
                                 start_1100 IS NOT NULL OR start_1200 IS NOT NULL OR start_1300 IS NOT NULL OR
                                 start_1400 IS NOT NULL OR start_1500 IS NOT NULL OR start_1600 IS NOT NULL OR
                                 start_1700 IS NOT NULL OR start_1800 IS NOT NULL OR start_1900 IS NOT NULL)
                            )""",
                    (master_id, date_check),
                )
                if c.fetchone()[0]:
                    date_buttons.append(types.KeyboardButton(date_check))
                    if len(date_buttons) == 3:
                        keyboard.row(*date_buttons)
                        date_buttons = []
            if date_buttons:
                keyboard.row(*date_buttons)
        finally:
            conn.close()

        cancel_button = types.KeyboardButton("Отмена")
        keyboard.add(cancel_button)

        if keyboard.keyboard:
            await message.answer("Выберите дату", reply_markup=keyboard)
            await Form.choice_date_after_service_1.set()
        else:
            await message.answer("Нет доступных дат для выбранного мастера")
            await Form.choice_date_after_service_1.set()

    except sqlite3.OperationalError as op_err:
        await message.answer(
            "Возникла проблема с базой данных. Пожалуйста, попробуйте еще раз позже"
        )
        print(f"Database error: {op_err}")

    except Exception as e:
        # Handle other exceptions
        await message.answer("Извините, произошла ошибка. Попробуйте снова")
        print(f"An unexpected error occurred: {e}")


@dp.message_handler(state=Form.choice_date_after_service_1)
async def choose_time_after_date_after_service(
    message: types.Message, state: FSMContext
):
    try:
        selected_date = message.text
        if selected_date in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return

        await state.update_data(selected_date=selected_date)
        user_data = await state.get_data()
        master_id = user_data.get("masterId")
        service_id = user_data.get("serviceId")
        if not master_id:
            await message.answer(
                "Возникла ошибка: информация о мастере не была найдена"
            )
            return
        conn = sqlite3.connect("db")
        try:
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
                         WHERE masterId = ? AND dayDate = ?""",
                (master_id, selected_date),
            )
            times = c.fetchone()

            c.execute(
                """SELECT appointmentTime
                                         FROM Record
                                         WHERE masterId = ? AND appointmentDate = ?""",
                (master_id, selected_date),
            )

            booked_times = [time[0] for time in c.fetchall()]

        finally:
            conn.close()

        now = datetime.now()
        choisen_date_datetime = datetime.strptime(selected_date, "%d-%m-%Y")
        time_threshold = (
            (now + timedelta(minutes=10)).strftime("%H:%M")
            if now.date() == choisen_date_datetime.date()
            else "00:00"
        )
        available_times = [
            time
            for time in times
            if time
            and (now.date() < choisen_date_datetime.date() or time > time_threshold)
            and time not in booked_times
        ]

        if not available_times:
            await message.answer("Нет доступных временных слотов на выбранную дату")
            return

        await state.update_data(available_times=available_times)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        times_row = []
        for time in available_times:
            if time:
                times_row.append(types.KeyboardButton(time))
                if len(times_row) == 3:
                    keyboard.row(*times_row)
                    times_row = []
        if times_row:
            keyboard.row(*times_row)
        cancel_button = types.KeyboardButton("Отмена")
        keyboard.add(cancel_button)
        await message.answer("Выберите время для записи", reply_markup=keyboard)
        await Form.time_choice_1.set()

    except sqlite3.OperationalError as db_err:
        await message.answer(
            "Произошла ошибка базы данных. Пожалуйста, попробуйте позже"
        )
        print(f"Database error: {db_err}")

    except Exception as err:
        await message.answer(
            "Произошла неожиданная ошибка. Пожалуйста, попробуйте позже"
        )
        print(f"Unexpected error: {err}")


@dp.message_handler(state=Form.time_choice_1)
async def input_name_client(message: types.Message, state: FSMContext):
    try:
        choicen_time = message.text
        if choicen_time in ("Отмена", "/start"):
            await cancel_handler(message, state)
            return
        user_data = await state.get_data()
        available_times = user_data["available_times"]
        if choicen_time not in available_times:
            await message.answer("Пожалуйста, выберите время из списка доступных")
            return
        await state.update_data(appointmentTime=choicen_time)
        await state.update_data(phone=message.text)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("Отмена")
        )
        await message.answer("Введите Ваше имя", reply_markup=keyboard)
        await Form.name_client_1.set()
    except Exception as e:
        await message.answer(
            "Произошла ошибка при обработке вашего времени. Попробуйте еще раз"
        )
        print(f"Error in input_name_client: {e}")


@dp.message_handler(state=Form.name_client_1)
async def input_phone(message: types.Message, state: FSMContext):
    try:
        print(message.text)
        if message.text in ("Отмена", "/start"):
            await state.finish()
            await send_welcome(message)
            return
        await state.update_data(name=message.text)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("Отмена")
        )
        await message.answer("Введите ваш номер телефона", reply_markup=keyboard)
        await Form.phone_1.set()
    except Exception as e:
        await message.answer(
            "Произошла ошибка при обработке вашего имени. Попробуйте еще раз"
        )
        print(f"Error in input_phone: {e}")


@dp.message_handler(state=Form.phone_1)
async def check_phone(message: types.Message, state: FSMContext):
    try:
        choise_name = message.text
        print(choise_name)
        if choise_name in ("Отмена", "/start"):
            await state.finish()
            await send_welcome(message)
            return
        phone_number = message.text
        if not is_valid_phone(phone_number):
            await message.answer(
                "Введен некорректный номер телефона. Пожалуйста, введите еще раз"
            )
            return
        await state.update_data(phone=phone_number)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("Отмена")
        )
        await message.answer("Введите ваш email", reply_markup=keyboard)
        await Form.email_1.set()
    except Exception as e:
        await message.answer(
            "Произошла ошибка при проверке вашего телефона. Попробуйте еще раз"
        )
        print(f"Error in check_phone: {e}")


@dp.message_handler(state=Form.email_1)
async def write_client_and_save_record(message: types.Message, state: FSMContext):
    try:
        if message.text in ("Отмена", "/start"):
            await state.finish()
            await send_welcome(message)
            return

        email = message.text
        if not is_valid_email(email):
            await message.answer(
                "Введен некорректный адрес почты. Пожалуйста, введите еще раз"
            )
            return
        await state.update_data(email_clients=email)

        user_data = await state.get_data()
        client_first_name = user_data.get("name")
        client_phone_number = user_data.get("phone")
        master_id = user_data.get("masterId")
        service_id = user_data.get("serviceId")
        appointment_date = user_data.get("selected_date")
        appointment_time = user_data.get("appointmentTime")

        if service_id is None:
            await message.answer("Ошибка: Информация об услуге не найдена")
            return

        with sqlite3.connect("db") as conn:
            c = conn.cursor()
            c.execute(
                """SELECT appointmentTime FROM Record 
                         WHERE masterId = ? AND appointmentDate = ? AND appointmentTime = ?""",
                (master_id, appointment_date, appointment_time),
            )
            if c.fetchone():  # If the slot is taken, raise an exception
                raise Exception("Вы не успели, на это время уже кто-то записался")

            c.execute(
                """INSERT INTO Clients (firstName, phoneNumber, eMail) VALUES (?, ?, ?)""",
                (client_first_name, client_phone_number, email),
            )
            client_id = c.lastrowid

            c.execute(
                """SELECT firstName, lastName FROM Masters WHERE id = ?""", (master_id,)
            )
            if master_record := c.fetchone():
                firstName, lastName = master_record[0], master_record[1]

            c.execute(
                """SELECT serviceName FROM Services WHERE id = ?""", (service_id,)
            )
            if service_record := c.fetchone():
                serviceName = service_record[0]

            c.execute(
                """SELECT price FROM MasterServices WHERE masterId = ? AND  serviceId = ?""",
                (master_id, service_id),
            )
            if price_record := c.fetchone():
                price = price_record[0]

            reminder_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            reminder_times = [
                ("24 часа", 24),
                ("12 часов", 12),
                ("6 часов", 6),
                ("3 часа", 3),
                ("2 часа", 2),
                ("1 час", 1),
            ]
            buttons = [
                types.KeyboardButton(text=f"Напомнить за {label}")
                for label, hours in reminder_times
            ]
            while buttons:
                button_pair = buttons[:2]
                reminder_keyboard.add(*button_pair)
                buttons = buttons[2:]
            dont_remind = types.KeyboardButton("Не напоминать")
            reminder_keyboard.add(dont_remind)
            await Form.remind_1.set()

            c.execute(
                """INSERT INTO Record (clientFirstName, clientPhoneNumber, masterId,
                         serviceId, appointmentDate, appointmentTime) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    client_first_name,
                    client_phone_number,
                    master_id,
                    service_id,
                    appointment_date,
                    appointment_time,
                ),
            )
            conn.commit()
        await message.answer(
            f"Вы записаны на услугу {serviceName} к мастеру {firstName} {lastName} на {appointment_date} в "
            f"{appointment_time}, стоимость услуги:{int(price) 
            if price == int(price) else price}₽",
            reply_markup=reminder_keyboard,
        )
        await send_confirmation_email(
            client_first_name,
            email,
            appointment_date,
            appointment_time,
            serviceName,
            price,
            firstName,
            lastName,
        )
    except sqlite3.IntegrityError as ie:
        await message.answer(
            "Ошибка базы данных при сохранении записи. Проверьте введенные данные и попробуйте снова"
        )
        print(f"Database IntegrityError: {ie}")

    except sqlite3.OperationalError as oe:
        await message.answer(
            "Ошибка операционной базы данных. Пожалуйста, попробуйте еще раз позже"
        )
        print(f"Database OperationalError: {oe}")

    except Exception as e:
        await message.answer(str(e))
        print(f"Unexpected error: {e}")


@dp.message_handler(state=Form.remind_1)
async def set_remind_in_db(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        client_first_name = user_data.get("name")
        client_phone_number = user_data.get("phone")
        appointment_date = user_data.get("selected_date")
        appointment_time = user_data.get("appointmentTime")
        if message.text in ("Не напоминать", "Отмена", "/start"):
            await state.finish()
            await send_welcome(message)
            return
        else:
            remind_text = message.text.split()
            print(remind_text)
            remind = int(remind_text[2]) if len(remind_text) == 4 else 0

        with sqlite3.connect("db") as conn:
            c = conn.cursor()
            c.execute(
                """UPDATE Record SET remind = ? WHERE clientPhoneNumber = ? AND appointmentDate = ? AND appointmentTime = ?""",
                (remind, client_phone_number, appointment_date, appointment_time),
            )
            conn.commit()

        await state.finish()
        await message.answer(
            f"Отправим вам напоминалку на почту за {remind_text[2]} час(а)."
        )
        await send_welcome(message)
        return
    except sqlite3.IntegrityError as ie:
        await message.answer(
            "Ошибка базы данных при сохранении записи. Проверьте введенные данные и попробуйте снова"
        )
        print(f"Database IntegrityError: {ie}")
    except sqlite3.OperationalError as oe:
        await message.answer(
            "Ошибка операционной базы данных. Пожалуйста, попробуйте еще раз позже"
        )
        print(f"Database OperationalError: {oe}")
    except Exception as e:
        await message.answer(str(e))
        print(f"Unexpected error: {e}")


#####################################################################################################################


def is_valid_phone(phone_number: str) -> bool:
    pattern = r"^\+?[78][-\(]?\d{3}\)?-?\d{3}-?\d{2}-?\d{2}$"
    return bool(re.fullmatch(pattern, phone_number))


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z]{2,}$"
    return bool(re.fullmatch(pattern, email))


@dp.message_handler(state="*", commands="Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await send_welcome(message)


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
