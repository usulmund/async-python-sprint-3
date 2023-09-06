from bidict import bidict
from asyncio.streams import StreamWriter

active_writers: list[StreamWriter] = list()
addr_user: dict = dict()
user_writer: dict = dict() # учесть все удаления!!!
uniq_names: set = set()

user_password: dict = dict()