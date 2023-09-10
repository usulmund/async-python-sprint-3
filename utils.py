"""
Модуль с описанием класса Commands,
содержащим перечисление команд.
"""
from enum import Enum


class Commands(Enum):
    RULES = '/rules'
    STATUS = '/status'
    EXIT = '/exit'
