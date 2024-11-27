import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv
from telebot import TeleBot

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

CLIENT_ERROR_STATUS_CODE_FIRST_NUMBER = 4

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG
)

handler = logging.StreamHandler(sys.stdout)


def check_tokens():
    """Checks that programm has all needed tokens"""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return

    missing_tokens = []
    if not PRACTICUM_TOKEN:
        missing_tokens.append('PRACTICUM_TOKEN')

    if not TELEGRAM_TOKEN:
        missing_tokens.append('TELEGRAM_TOKEN')

    if not TELEGRAM_CHAT_ID:
        missing_tokens.append('TELEGRAM_CHAT_ID')

    error_message = (
        f'Отсутствует обязательная переменная окружения: '
        f'{", ".join(missing_tokens)}'
    )
    logging.critical(error_message)
    raise NoTokenException(error_message)


def send_message(bot, message):
    """Sends me a message"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Бот отправил сообщение: {message}')
    except Exception as error:
        logging.error(
            f'При отправке сообщения {message} возникла ошибка: {error}'
        )


def get_api_answer(timestamp):
    """Sends a request to yandex api to get homework info"""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': str(timestamp)}
        )
    except requests.RequestException:
        raise NetworkException(
            'There was an ambiguous exception that '
            'occurred while handling your request.'
        )
    else:
        python_response = response.json()
        RESPONSE_STATUS_CODE_FIRST_NUMBER = response.status_code // 100

        if (
            RESPONSE_STATUS_CODE_FIRST_NUMBER
            == CLIENT_ERROR_STATUS_CODE_FIRST_NUMBER
        ):
            raise NetworkException(
                f'При обращении к эндпоинту {ENDPOINT} '
                f'возникла ошибка со стороны клиента: {python_response}'
            )
        elif response.status_code != 200:
            raise NetworkException(
                f'При обращении к эндпоинту {ENDPOINT} '
                f'возникла ошибка со стороны сервера: {python_response}'
            )

        return python_response


def check_response(response):
    """Checks that api response conforms to documentation"""
    if type(response) is not dict:
        raise TypeError(f'Данные получены не в виде словаря: {response}')

    if type(response.get('homeworks')) is not list:
        raise TypeError(
            f'Под ключом homeworks должен находиться список, '
            f'а приходит {response.get("homeworks")}'
        )

    if (
        response.get('homeworks') is None
        or response.get('current_date') is None
    ):
        raise WrongResponseException('В ответе api отсутствует один из ключей')


def parse_status(homework):
    """Returns homework status"""
    if homework is None:
        logging.debug('Ни у одной из домашних работ не появился новый статус')
        return 'Ни у одной из домашних работ не появился новый статус'
    elif not homework.get('homework_name'):
        raise WrongResponseException(
            f'В homework отсутствует ключ homework_name: {homework}'
        )

    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS.keys():
        raise WrongHomeworkStatusException(
            f'Неожиданный статус домашней работы, '
            f'обнаруженный в ответе API: {status}'
        )
    verdict = HOMEWORK_VERDICTS.get(status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    last_error_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if len(response.get('homeworks')):
                message = parse_status(response.get('homeworks')[0])
            else:
                message = parse_status(None)
            send_message(bot, message)
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logging.error(error_message)
            if last_error_message != error_message:
                send_message(bot=bot, message=error_message)
            last_error_message = error_message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
