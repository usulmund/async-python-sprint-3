"""
Модуль для хранения изменяемых объектов с информацией о пользователях.
"""
from asyncio.streams import StreamWriter
from datetime import datetime


active_writers: list[StreamWriter] = list()
user_writer: dict[str, list[StreamWriter]] = dict()
writer_user: dict[StreamWriter, str] = dict()
user_password: dict[str, str] = dict()
user_complain: dict[str, set] = dict()
user_msgcnt: dict[str, int] = dict()
user_starttime: dict[str, datetime] = dict()
user_ban: dict[str, bool] = dict()
