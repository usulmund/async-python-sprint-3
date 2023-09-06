import logging
import sys
import asyncio
from asyncio.streams import StreamReader, StreamWriter
import os
from bidict import bidict
from aioconsole import ainput

# from server import addr_user, active_writers


# active_writers: list[asyncio.streams.StreamWriter] = list()
from data_keeper import active_writers, addr_user, uniq_names, user_writer



class Client:
    def __init__(self, host="127.0.0.1", port=8000):
        self.__host = host
        self.__port = port
        self.__is_server_work = True

    async def open_chat(self):
        self.__reader, self.__writer = await asyncio.open_connection(
            self.__host,
            self.__port
        )
        # await asyncio.sleep(0.1)
        await asyncio.gather( # подумать чем заменить
            self.read_message(),
            self.send_message()
        )
    async def read_message(self):
        while True:
            try:
                message = await self.__reader.read(1024)
                if message.decode() == '/end' or message.decode() == '':
                    # print()
                    self.__is_server_work = False
                    break
                else:
                    print(message.decode()) # заменить на формат вывод

            except Exception as e:
                print('read message error ', e)

    async def send_message(self):
        while True:
            try:
                message = await ainput('')
                self.__writer.write(message.encode())
                await self.__writer.drain()
                if message == 'exit' or self.__is_server_work == False:
                    #self.__writer.write(b' left the chat')
                    # await self.__writer.#drain()
                    break
            except Exception as e:
                print('send_message_error', e)
 

if __name__ == '__main__':
    
    client = Client()
    try:
        asyncio.run(client.open_chat())
    except:
        print('STOP')