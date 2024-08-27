import asyncio
import sqlite3
import time
from datetime import datetime, timedelta
from email.message import EmailMessage

import aiosmtplib
import pytest
import schedule
from config import *


async def send_confirmation_email(
    client_first_name,
    email,
    date,
    time,
    service_name,
    price,
    master_first_name,
    master_last_name,
):
    if email:
        subject = 'Подтверждение записи в  салон красоты "HAIR SALMING LIICING"'
        body = (
            f"Уважаемый(ая) {client_first_name}, подтверждаем вашу запись в салон красоты "
            f'"HAIR SALMING LIICING" ул. Красный проспект, 122;\n'
            f"К мастеру: {master_first_name} {master_last_name};\n"
            f"Когда: {date} в {time};\n"
            f"На услугу: {service_name};\n"
            f"Стоимость услуги: {int(price) if price == int(price) else price}₽"
        )
        message = EmailMessage()
        message["From"] = smtp_username
        message["To"] = email
        message["Subject"] = subject
        message.set_content(body)  # Или любой другой контент

        try:
            # Отправляем сообщение
            await aiosmtplib.send(
                message,
                hostname=smtp_host,
                port=smtp_port,
                username=smtp_username,
                password=smtp_password,
                use_tls=True,
            )
        except aiosmtplib.SMTPException as e:
            print(f"Ошибка SMTP при отправке сообщения: {e}")
        except asyncio.TimeoutError as e:
            print(f"Превышено время ожидания при отправке сообщения: {e}")
        except Exception as e:
            print(f"Неожиданная ошибка при отправке сообщения: {e}")
