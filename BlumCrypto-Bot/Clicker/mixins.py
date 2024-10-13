from time import time
from typing import List


class TimestampMixin:
    @staticmethod
    def timestamp() -> int:
        return int(time())


class CardSorterMixin:
    """ Класс предоставляющий методы сортировки карт """
    @staticmethod
    def sorted_by_profit(prepared: List) -> List:
        """ Сортировка по прибыльности """
        return sorted(prepared, key=lambda x: x["profitPerHourDelta"], reverse=True)

    @staticmethod
    def sorted_by_profitness(prepared: List) -> List:
        """ Сортировка по цене профиту (отношение прибыльности к цене) """
        return sorted(prepared, key=lambda x: x['profitPerHourDelta'] / x['price'], reverse=True)

    @staticmethod
    def sorted_by_price(prepared: List) -> List:
        """ Сортировка по цене """
        return sorted(prepared, key=lambda x: x["price"], reverse=False)

    @staticmethod
    def sorted_by_payback(prepared: List) -> List:
        """ Сортировка по скорости окупаемости """
        return sorted(prepared, key=lambda x: x['price'] / x['profitPerHourDelta'], reverse=False)
