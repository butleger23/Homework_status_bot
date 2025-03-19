### Описание проекта:

В данном проекте был создан telegram бот, предназначенный для получения информации посредством шорт-поллинга и оповещения соответствующего юзера.

### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/butleger23/Homework_status_bot.git
```

```
cd Homework_status_bot
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv venv
```

```
source venv/bin/activate
```

Установить зависимости из файла requirements.txt:

```
python3 -m pip install --upgrade pip
```

```
pip install -r requirements.txt
```

Необходимо создать файл .env и наполнить его парами ключ-значение для ключей:

```
PRACTICUM_TOKEN=[токен из ЯП]
TELEGRAM_TOKEN=[token вашего telegram бота]
TELEGRAM_CHAT_ID=[telegram id адресата]
```

Выполнить команду:

```
python homework.py
```
