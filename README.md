Чтобы создать и активировать виртуальное окружение в Linux, нужно использовать следующие шаги в терминале.

apt install python3-virtualenv

1. Установите пакет virtualenv если он еще не установлен:
   apt install python3-virtualenv
   
3. Перейдите в директорию вашего проекта:
   cd ~/service_fish
   
4. Создайте виртуальное окружение:
   virtualenv venv

5. Активируйте виртуальное окружение:

   source venv/bin/activate
   
   
pip install -r requirements.txt
