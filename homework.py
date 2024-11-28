import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv
from http import HTTPStatus
from telebot import apihelper, TeleBot

from exceptions import (
    NetworkException,
    NoTokenException,
    WrongHomeworkStatusException,
    WrongResponseException,
)


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens():
    """Проверяет наличие необходимых для работы программы токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    missing_tokens = []

    for token_name, value in tokens.items():
        if value is None:
            missing_tokens.append(token_name)

    if not missing_tokens:
        return

    error_message = (
        'Отсутствует обязательная переменная окружения: '
        f'{", ".join(missing_tokens)}'
    )
    logging.critical(error_message)
    raise NoTokenException(error_message)


def send_message(bot, message):
    """Посылает сообщение в мой телеграм чат."""
    logging.debug(f'Бот начал отправлять сообщение: {message}')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Бот отправил сообщение: {message}')
    except (apihelper.ApiException, requests.RequestException) as error:
        logging.error(
            f'При отправке сообщения {message} возникла ошибка: {error}'
        )


def get_api_answer(timestamp):
    """Посылает запрос в Яндекс API для получения информации о задании."""
    params = {'from_date': str(timestamp)}
    logging.debug(
        'Производится запрос к с по данному эндпоинту '
        f'{ENDPOINT} c данными аргументами {params}'
    )
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logging.debug('Запрос к Яндекс API завершился успешно')
    except requests.RequestException as error:
        raise ConnectionError(
            f'При обращении к эндпоинту {ENDPOINT} '
            f'возникла ошибка со стороны клиента: {error}'
        )
    else:
        if response.status_code != HTTPStatus.OK:
            raise NetworkException(
                f'При обращении к эндпоинту {ENDPOINT} возникла ошибка со '
                f'стороны сервера: {response.reason} со статусом '
                f'{response.status_code}'
            )

        return response.json()


def check_response(response):
    """Проверяет что ответ Яндекс API соответствует документации."""
    logging.debug('Начало проверки ответа Яндекс API')
    if not isinstance(response, dict):
        raise TypeError(
            'Данные получены не в виде словаря, '
            f'полученный тип данных: {type(response)}')

    if 'homeworks' not in response:
        raise WrongResponseException('В ответе api отсутствует homeworks')

    if not isinstance(
        response.get('homeworks'), list
    ):
        raise TypeError(
            'Под ключом homeworks должен находиться список, '
            f'а приходит {type(response.get("homeworks"))}'
        )
    logging.debug('Проверка ответа Яндекс API успешно завершена')


def parse_status(homework):
    """Возвращает статус домашней работы."""
    logging.debug('Начало проверки статуса домашней работы')
    if 'homework_name' not in homework:
        raise KeyError(
            f'В homework отсутствует ключ homework_name: {homework}'
        )
    homework_name = homework.get('homework_name')

    if 'status' not in homework:
        raise KeyError(f'В homework отсутствует ключ status: {homework}')
    status = homework.get('status')

    if status not in HOMEWORK_VERDICTS.keys():
        raise WrongHomeworkStatusException(
            'Неожиданный статус домашней работы, '
            f'обнаруженный в ответе API: {status}'
        )
    verdict = HOMEWORK_VERDICTS.get(status)

    logging.debug('Статус домашней работы успешно проверен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response.get('homeworks'):
                message = parse_status(response.get('homeworks')[0])
                send_message(bot, message)
                last_error_message = None
            else:
                logging.debug(
                    'Ни у одной из домашних работ не появился новый статус'
                )
            timestamp = response.get('current_date', int(time.time()))
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logging.error(error_message)
            if last_error_message != error_message:
                send_message(bot=bot, message=error_message)
                last_error_message = error_message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format=(
            '%(lineno)d - %(funcName)s - %(asctime)s '
            '- %(levelname)s - %(message)s'
        ),
        level=logging.DEBUG,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    main()
