import logging
import re
from base64 import b64decode
from http import HTTPStatus
from time import sleep, time
from typing import Dict, List, Union

from requests import Response, Session

from config.enums import MessageEnum, UrlsEnum
from config.headers import HEADERS
from config.mini_games import MINI_GAMES
from config.morse import MORSE_CODE_DICT
from generator import CodeGenerator
from mixins import CardSorterMixin, TimestampMixin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s   %(message)s")


def retry(func):
    def wrapper(*args, **kwargs):
        while True:
            try:
                result = func(*args, **kwargs)
                if result.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.ACCEPTED):
                    return result
                else:
                    logging.info(MessageEnum.MSG_BAD_RESPONSE.format(status=result.status_code, text=result.text))
                    sleep(10)
            except Exception as error:
                logging.error(MessageEnum.MSG_SESSION_ERROR.format(error=error))
                sleep(1)

    return wrapper


class HamsterClient(Session, TimestampMixin, CardSorterMixin):
    state: Dict = None
    promos: List[str] = None
    boosts: Dict = None
    upgrades: Dict = None
    tasks: List = None
    task_checked_at: float = None
    codes: List[str] = []

    def __init__(self, token, name="NoName", **kwargs) -> None:
        super().__init__()
        self.features = kwargs
        self.headers: Dict = HEADERS.copy()
        self.headers["Authorization"]: str = f"Bearer {token}"
        self.request = retry(super().request)
        self.name: str = name

    @property
    def balance(self) -> Union[int, None]:
        """ Количество заработанных монет """
        if self.state:
            return int(self.state["balanceCoins"])

    @property
    def level(self) -> Union[int, None]:
        """ Текущий уровень """
        if self.state:
            return self.state["level"]

    @property
    def keys(self) -> Union[int, None]:
        """
        Количество ключей
        параметр totalKeys имеет такое же значение как и balanceKeys. Возможно изменится после траты ключей.
        """
        if self.state:
            return self.state["balanceKeys"]

    @property
    def available_taps(self) -> Union[int, None]:
        """ Энергия """
        if self.state:
            return self.state["availableTaps"]

    @property
    def recover_per_sec(self) -> Union[int, None]:
        """ Востановление энергии в секунду """
        if self.state:
            return self.state["tapsRecoverPerSec"]

    @property
    def _is_taps_boost_available(self) -> Union[bool, None]:
        """ Проверка, доступны ли усиления """
        self._update_boosts_list()
        if not self.boosts:
            return
        for boost in self.boosts["boostsForBuy"]:
            if (
                boost["id"] == 'BoostFullAvailableTaps'
                and boost["cooldownSeconds"] == 0
                and boost["level"] <= boost["maxLevel"]
            ):
                return True

    @property
    def stats(self) -> Dict:
        """ Статистика """
        return {
            "уровень": self.level,
            "энергия": self.available_taps,
            'баланс': re.sub(r'(?<!^)(?=(\d{3})+$)', ' ', str(self.balance)),
            'ключи': re.sub(r'(?<!^)(?=(\d{3})+$)', ' ', str(self.keys)),
            "доход в час": re.sub(r'(?<!^)(?=(\d{3})+$)', ' ', str(self.state['earnPassivePerHour']))
        }

    @property
    def log_prefix(self) -> str:
        """ Префикс с именем пользователя для логирования """
        return f"[{self.name}]\t "

    def get_cipher_data(self) -> Dict:
        """
        Получить информацио о шифре

        Example:
            {
                'cipher': 'REV4GSQ==',
                'bonusCoins': 1000000,
                'isClaimed': True,
                'remainSeconds': 27144
            }
        """
        result = self.post(url=UrlsEnum.CONFIG).json()
        return result['dailyCipher']

    def log_stats(self):
        """ Логирование статистики"""
        logging.info(self.log_prefix + " ".join(f"{k}: {v} |" for k, v in self.stats.items()))

    def claim_daily_cipher(self) -> None:
        """ Разгадываем шифр """
        cipher_data = self.get_cipher_data()
        if not cipher_data['isClaimed']:
            raw_cipher = cipher_data['cipher']
            logging.info(MessageEnum.MSG_CRYPTED_CIPHER.format(cipher=raw_cipher))
            re_result = re.search('\d+', raw_cipher[3:])  # noqa W605
            if re_result:
                str_len = re_result[0]
                raw_cipher = raw_cipher.replace(str_len, "", 1)
                raw_cipher = raw_cipher.encode()
                cipher = b64decode(raw_cipher).decode()
                morse_cipher = "  ".join((MORSE_CODE_DICT.get(char, " ") for char in cipher))
                logging.info(MessageEnum.MSG_CIPHER.format(cipher=cipher + " | " + morse_cipher))
                self.post(url=UrlsEnum.CLAIM_DAILY_CIPHER, json={"cipher": cipher})

    def sync(self) -> None:
        """ Обновить данные о пользователе """
        try:
            response = self.post(url=UrlsEnum.SYNC)
            self.state = response.json()["clickerUser"]
            logging.info(self.log_prefix + MessageEnum.MSG_SYNC)
        except Exception as error:
            logging.error(self.log_prefix + MessageEnum.MSG_SYNC_ERROR.format(error=error))

    def _apply_minigame_code(self, code: str) -> None:
        """
        Ввести код из мини игры для получения ключей
        :param code: код для ввода
        """
        data = {"promoCode": code}
        response = self.post(url=UrlsEnum.APPLY_PROMO, json=data)
        if response.status_code == HTTPStatus.OK:
            logging.info(self.log_prefix + MessageEnum.MSG_SUCCESSFUL_PROMO_APPLY.format(code=code))
        else:
            logging.info(self.log_prefix + MessageEnum.MSG_UNSUCCESSFUL_PROMO_APPLY.format(code=code))
        if code in self.codes:
            self.codes.remove(code)

    def _generate_minigame_codes(self) -> None:
        """ Сгенерировать коды из мини игр """
        for game in MINI_GAMES.keys():
            key_gen = CodeGenerator(key_count=4, account_name=self.name, game_name=game)
            self.codes += key_gen.execute()

    def apply_all_codes(self):
        """ Ввести все коды """
        if self.features['generate_codes']:
            self.request = super().request
            self._generate_minigame_codes()
            for code in self.codes:
                self._apply_minigame_code(code)
            self.request = retry(super().request)

    def check_task(self) -> None:
        """ Получение ежедневной награды """
        data = {
            "taskId": "streak_days"
        }
        if not self.task_checked_at or time() - self.task_checked_at >= 60 * 60:
            self.post(url=UrlsEnum.CHECK_TASK, json=data)
            self.task_checked_at = time()

    def tap(self) -> None:
        """ Тапаем на монеты максимальное кол-во раз """
        taps_count = self.available_taps or self.recover_per_sec
        data = {
            "count": taps_count,
            "availableTaps": self.available_taps - taps_count,
            "timestamp": self.timestamp()
        }
        self.post(url=UrlsEnum.TAP, json=data).json()
        logging.info(self.log_prefix + MessageEnum.MSG_TAP.format(taps_count=taps_count))

    def apply_boost(self, boost_name='BoostFullAvailableTaps') -> None:
        """
        Взять усиление
        :param boost_name: название усиления
        """
        if self._is_taps_boost_available:
            data = {
                "boostId": boost_name,
                "timestamp": self.timestamp()
            }
            self.post(url=UrlsEnum.BUY_BOOST, json=data)

    def _update_tasks(self):
        """ Обновить список заданий """
        response = self.post(UrlsEnum.LIST_TASKS)
        if response.status_code == HTTPStatus.OK:
            result = response.json()
            self.tasks = list(filter(lambda d: d['isCompleted'] != True, result["tasks"]))

    def execute_youtube_tasks(self):
        """ Выполнить задания по просмотру youtube видео """
        self._update_tasks()
        for task in self.tasks:
            task_id = task['id']
            reward = task['rewardCoins']

            if not task_id.startswith('hamster_youtube'):
                continue

            if reward > 0:
                data = {'taskId': task_id}
                response = self.post(UrlsEnum.CHECK_TASK, json=data)
                if response.status_code == HTTPStatus.OK:
                    result = response.json()
                    result = result["task"]
                    is_completed = result.get('isCompleted')
                    if is_completed:
                        logging.info(self.log_prefix + MessageEnum.MSG_TASK_COMPLETED.format(reward=reward))
                    else:
                        logging.info(self.log_prefix + MessageEnum.MSG_TASK_NOT_COMPLETED)

    def _upgrade_card(self, upgrade_name) -> Response:
        """
        Купить карточку
        :param upgrade_name: название карточки
        """
        data = {
            "upgradeId": upgrade_name,
            "timestamp": self.timestamp()
        }
        response = self.post(url=UrlsEnum.BUY_UPGRADE, json=data)
        return response

    def _upgrades_list(self) -> None:
        """ Обновить список карточек """
        self.upgrades = self.post(url=UrlsEnum.UPGRADES_FOR_BUY).json()

    def _update_boosts_list(self) -> None:
        """
        Обновить список усилиений
         - BoostEarnPerTap
         - BoostMaxTaps
         - BoostFullAvailableTaps
         """
        self.boosts = self.post(url=UrlsEnum.BOOSTS_FOR_BUY).json()

    def _get_sorted_upgrades(self, method):
        """
            1. Фильтруем карточки
                - доступные для покупки
                - не просроченные
                - с пассивным доходом
                - без ожидания перезарядки
            2. Сортируем по профитности на каждую потраченную монету
        """
        methods = dict(
            payback=self.sorted_by_payback,
            price=self.sorted_by_price,
            profit=self.sorted_by_profit,
            profitness=self.sorted_by_profitness
        )
        prepared = []
        for upgrade in self.upgrades.get("upgradesForBuy"):
            if (
                upgrade["isAvailable"]
                and not upgrade["isExpired"]
                and upgrade["profitPerHourDelta"] > 0
                and not upgrade.get("cooldownSeconds")
            ):
                item = upgrade.copy()
                if 'condition' in item:
                    item.pop('condition')
                prepared.append(item)
        if prepared:
            sorted_items = [i for i in methods[method](prepared)]
            return sorted_items
        return []

    def buy_upgrades(self) -> None:
        """ Покупаем лучшие апгрейды на все монеты """
        if self.features['buy_upgrades']:
            while True:
                self._upgrades_list()
                if sorted_upgrades := self._get_sorted_upgrades(self.features['buy_decision_method']):
                    upgrade = sorted_upgrades[0]
                    if upgrade['price'] <= self.balance:
                        result = self._upgrade_card(upgrade['id'])
                        if result.status_code == HTTPStatus.OK:
                            self.state = result.json()["clickerUser"]

                        log_info = {
                            'name': upgrade['name'],
                            'price': re.sub(r'(?<!^)(?=(\d{3})+$)', ' ', str(upgrade['price'])),
                            'level': upgrade['level'],
                            'profitPerHourDelta': re.sub(
                                r'(?<!^)(?=(\d{3})+$)',
                                ' ',
                                str(upgrade['profitPerHourDelta'])
                            ),
                        }

                        logging.info(self.log_prefix + MessageEnum.MSG_BUY_UPGRADE.format(**log_info))
                        sleep(0.5)
                    else:
                        break
                else:
                    break
        else:
            self._upgrades_list()

    def claim_combo_reward(self) -> None:
        """ Получаем награду, если собрано комбо """
        combo = self.upgrades.get('dailyCombo', {})
        upgrades = combo.get('upgradeIds', [])
        combo_cards = ", ".join(upgrades)
        logging.info(self.log_prefix + MessageEnum.MSG_CLAIMED_COMBO_CARDS.format(cards=combo_cards or '-'))
        if combo and len(upgrades) == 3:
            if combo.get('isClaimed') is False:
                result = self.post(url=UrlsEnum.CLAIM_DAILY_COMBO)
                if result.status_code == HTTPStatus.OK:
                    self.state = result.json()["clickerUser"]
                    logging.info(self.log_prefix + MessageEnum.MSG_COMBO_EARNED.format(coins=combo['bonusCoins']))

    def execute(self) -> None:
        self.apply_all_codes()
        self.sync()
        self.claim_daily_cipher()
        self.tap()
        self.buy_upgrades()
        self.check_task()
        self.execute_youtube_tasks()
        self.claim_combo_reward()
        self.apply_boost()
        self.log_stats()
        sleep(0.5)
