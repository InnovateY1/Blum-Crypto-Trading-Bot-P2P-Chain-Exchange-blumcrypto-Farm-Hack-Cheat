import logging
import random
import string
import threading
import time
import uuid
from datetime import datetime
from http import HTTPStatus
from typing import Dict, List, Union

from requests import Session

from config.enums import MessageEnum, UrlsEnum
from config.mini_games import MINI_GAMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s   %(message)s")


class CodeGenerator(Session):
    def __init__(self, game_name: str, key_count: int, account_name: str) -> None:
        super().__init__()
        self.game_name = game_name
        self.key_count = key_count
        self.account_name = account_name
        self.game: Dict = MINI_GAMES[self.game_name]

    @property
    def log_prefix(self) -> str:
        """ Префикс с именем пользователя для логирования """
        return f"[{self.account_name}]\t "

    @staticmethod
    def generate_client_id() -> str:
        """ Сгенерировать client_id """
        timestamp = int(datetime.now().timestamp() * 1000)
        random_numbers = ''.join(random.choices(string.digits, k=19))
        return f"{timestamp}-{random_numbers}"

    def sleep_with_random_delay(self) -> None:
        """ Случайная задержка """
        delay = self.game['events_delay'] * (random.random() / 3 + 1)
        time.sleep(delay)

    def get_client_token(self, client_id: str) -> str:
        """ Получить client_token """
        url = UrlsEnum.LOGIN_CLIENT
        payload = {
            "appToken": self.game["app_token"],
            "clientId": client_id,
            "clientOrigin": "deviceid"
        }
        headers = {'Content-Type': 'application/json'}
        response = self.post(url, json=payload, headers=headers)
        data = response.json()

        if response.status_code != HTTPStatus.OK:
            if data.get("error_code") == "TooManyIpRequest":
                raise Exception('Очень много запросов. Пожалуйста, подождите несколько минут и попробуйте еще раз.')
            else:
                raise Exception(data.get("error_message", 'Failed to log in'))

        return data["clientToken"]

    def emulate_progress(self, client_token: str) -> str:
        url = UrlsEnum.REGISTER_EVENT
        payload = {
            "promoId": self.game["promo_id"],
            "eventId": str(uuid.uuid4()),
            "eventOrigin": "undefined"
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {client_token}'
        }
        response = self.post(url, json=payload, headers=headers)
        data = response.json()
        return data.get("hasCode", False)

    def generate_key(self, client_token: str) -> str:
        """ Сгенерировать ключ """
        url = UrlsEnum.CREATE_CODE
        payload = {"promoId": self.game["promo_id"]}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {client_token}'
        }
        response = self.post(url, json=payload, headers=headers)
        data = response.json()

        if not response.ok:
            raise Exception(data.get("error_message", 'Не удалось сгенерировать ключ'))

        return data["promoCode"]

    def generate_key_process(self) -> Union[str, None]:
        client_id = self.generate_client_id()
        try:
            client_token = self.get_client_token(client_id)
        except Exception as err:
            logging.error(self.log_prefix + MessageEnum.MSG_UNSUCCESSFUL_GETTING_CLIENT_TOKEN.format(err=err))
            return None

        for _ in range(self.game['attempts_number']):
            self.sleep_with_random_delay()
            has_code = self.emulate_progress(client_token)
            if has_code:
                break

        try:
            key = self.generate_key(client_token)
            return key
        except Exception as err:
            logging.error(self.log_prefix + MessageEnum.MSG_UNSUCCESSFUL_GENERATE_KEY.format(err=err))
            return None

    def execute(self) -> List[str]:
        keys = []
        threads = []

        logging.info(self.log_prefix + MessageEnum.MSG_GENERATE_KEYS_GAME.format(game=self.game_name))

        def worker():
            key = self.generate_key_process()
            if key:
                keys.append(key)

        for _ in range(self.key_count):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return keys
