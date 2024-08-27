import asyncio
import sqlite3
import time
from datetime import datetime, timedelta
from email.message import EmailMessage

import aiosmtplib
import schedule
from config import *


async def check_and_send_reminders():
    now = datetime.now()
    try:
        with sqlite3.connect("db") as conn:
            c = conn.cursor()
            c.execute(
                """SELECT r.id, cl.firstName, cl.eMail, r.appointmentDate, 
           r.appointmentTime, r.remind, s.serviceName, 
           ms.price, m.firstName AS masterFirstName, 
           m.lastName AS masterLastName
        FROM Record r
        JOIN Clients cl ON r.clientPhoneNumber = cl.phoneNumber
        JOIN Services s ON r.serviceId = s.id
        JOIN MasterServices ms ON r.masterId = ms.masterId AND r.serviceId = ms.serviceId
        JOIN Masters m ON r.masterId = m.id
        WHERE DATE(datetime(substr(r.appointmentDate, 7, 4) || '-' || 
           substr(r.appointmentDate, 4, 2) || '-' || 
           substr(r.appointmentDate, 1, 2))) >= DATE(?) AND r.remind IS NOT NULL""",
                (now.strftime("%Y-%m-%d"),),
            )
            records = c.fetchall()
            print(records)
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return

    for record in records:
        print(record)
        try:
            (
                id,
                client_first_name,
                email,
                date,
                time,
                remind,
                service_name,
                price,
                master_first_name,
                master_last_name,
            ) = record
            appointment_time = datetime.strptime(f"{date} {time}", "%d-%m-%Y %H:%M")
            reminder_time = appointment_time - timedelta(hours=remind)
            print(reminder_time)
            if (now >= reminder_time) and email:
                subject = 'Напоминание о запланированном визите в парикмахерскую "HAIR SALMING LIICING"'
                body = (
        f"Уважаемый(ая) {client_first_name}, напоминаем вам о том что вы записаны на визит в парикмахерскую\n "
        f'"HAIR SALMING LIICING" ул. Красный проспект, 122; \n'
        f"К мастеру: {master_first_name} {master_last_name};\n"
        f"Когда: {date} в {time};\n"
        f"На услугу {service_name};\n"
        f"Стоимость услуги: {int(price) if price == int(price) else price}₽"
    )
                message = EmailMessage()
                message["From"] = smtp_username
                message["To"] = email
                message["Subject"] = subject
                message.set_content(body)  # Или любой другой контент

                # Отправляем сообщение
                await aiosmtplib.send(
                    message,
                    hostname=smtp_host,
                    port=smtp_port,
                    username=smtp_username,
                    password=smtp_password,
                    use_tls=True,
                )
                with sqlite3.connect("db") as conn:
                    c = conn.cursor()
                    c.execute("UPDATE Record SET remind = NULL WHERE id = ?", (id,))
                    conn.commit()
        except aiosmtplib.SMTPException as e:
            print(f"Ошибка SMTP при отправке сообщения: {e}")
        except asyncio.TimeoutError as e:
            print(f"Превышено время ожидания при отправке сообщения: {e}")
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")


def job():
    asyncio.run(check_and_send_reminders())


# Настройка расписания
schedule.every(1).minutes.do(job)  # Проверка каждую минуту

while True:
    schedule.run_pending()
    time.sleep(1)
