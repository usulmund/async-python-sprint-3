"""
Модуль с описанием класса Client и запуском клиента.
"""
import asyncio
from aioconsole import ainput


class Client:
    """
    Класс с описанием клиента.
    Возможные параметры: хост, порт.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.__host = host
        self.__port = port
        self.__is_server_work = True

    async def open_chat(self) -> None:
        """
        Корутина для подключения к серверу.
        Ожижает завершение конкуретных корутин по отправке и чтению сообщений.
        """
        self.__reader, self.__writer = await asyncio.open_connection(
            self.__host,
            self.__port
        )
        await asyncio.gather(self.read_message(), self.send_message())

    async def read_message(self) -> None:
        """
        Корутина для чтения сообщений.
        Работает до тех пор, пока не будет получено сообщение
        о завершении работы сервера.
        """
        while True:
            try:
                message = await self.__reader.read(1024)
                if message.decode() == '/end' or message.decode() == '':
                    self.__is_server_work = False
                    break
                else:
                    print(message.decode())

            except Exception as e:
                print('read message error ', e)

    async def send_message(self) -> None:
        """
        Корутина для отправки сообщений.
        В случае отправки сообщения exit или отключения сервера
        завершает работу.
        """
        while True:
            try:
                message = await ainput('')
                if message.strip() != '':
                    self.__writer.write(message.encode())
                    await self.__writer.drain()
                if message == '/exit' or not self.__is_server_work:
                    break
            except Exception as e:
                print('send_message_error', e)


if __name__ == '__main__':
    client = Client()
    try:
        asyncio.run(client.open_chat())
    except (KeyboardInterrupt, ConnectionRefusedError, RuntimeError):
        print('STOP')
