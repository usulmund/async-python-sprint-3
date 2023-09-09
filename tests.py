"""
Модуль с тестами по взамсодействию с сервером
со стороны клиентов.
"""
import unittest
from multiprocessing import Process
import asyncio
import telnetlib

from server import Server, BACK_UP_FILE, logger
from time import sleep

HOST = 'localhost'
PORT = 8000


chat_server = Server()


def start_server():
    """
    Функция для запуска сервера.
    """
    with open(BACK_UP_FILE, 'w') as _:
        logger.info('\nBack-up file was cleared')
    try:
        asyncio.run(chat_server.listen())
    except KeyboardInterrupt:
        logger.info('\nServer was stoped')


def connect_to_client(username: str, password: str):
    """
    Функция для проверки подключения клиента к чату.
    """
    connection = telnetlib.Telnet(HOST, PORT)
    sleep(0.5)
    connection.write(username.encode() + b'\n')
    sleep(0.5)
    connection.write(password.encode() + b'\n')
    sleep(5)
    result = connection.read_very_eager().decode()
    connection.write(b'/exit\n')
    return result


def authorization(username: str, password: str):
    """
    Функция для подключения клиента к чату.
    Возвращает объект telnetlib.Telnet.
    """
    client = telnetlib.Telnet(HOST, PORT)
    sleep(0.5)
    client.write(username.encode() + b'\n')
    sleep(0.5)
    client.write(password.encode() + b'\n')
    return client


def send_private():
    """
    Функция для примера отправки приватных сообщений.
    """
    client_1 = authorization('a', 'a')
    client_2 = authorization('b', 'b')
    client_3 = authorization('c', 'c')
    client_1.write(b'/private b hello\n')
    result = []
    sleep(5)
    result.append(client_1.read_very_eager().decode())
    result.append(client_2.read_very_eager().decode())
    result.append(client_3.read_very_eager().decode())
    client_1.write(b'/exit\n')
    sleep(1)
    client_2.write(b'/exit\n')
    sleep(1)
    client_3.write(b'/exit\n')
    sleep(1)
    return result


def wrong_password():
    """
    Функция для примера ввода неверного пароль.
    """
    client_1 = authorization('OLEG', 'P@ssw0rd')
    sleep(5)
    client_1.write(b'/exit\n')

    client_1 = authorization('OLEG', 'b')
    sleep(1)
    client_1.write(b'OLEG\n')
    sleep(1)
    client_1.write(b'b\n')
    sleep(1)
    client_1.write(b'OLEG\n')
    sleep(1)
    client_1.write(b'b\n')
    sleep(1)
    client_1.write(b'OLEG\n')
    sleep(1)
    client_1.write(b'b\n')

    sleep(10)
    result = client_1.read_very_eager().decode()
    client_1.write(b'/exit\n')
    return result


def ban():
    """
    Функция для примера бана пользователя.
    """
    client_1 = authorization('A', 'a')
    client_2 = authorization('B', 'b')
    client_3 = authorization('C', 'c')
    client_4 = authorization('D', 'd')

    client_1.write(b'/ban D\n')
    client_2.write(b'/ban D\n')
    client_3.write(b'/ban D\n')
    sleep(10)

    result = client_4.read_very_eager().decode()

    client_1.write(b'/exit\n')
    sleep(1)
    client_2.write(b'/exit\n')
    sleep(1)
    client_3.write(b'/exit\n')
    sleep(1)
    client_4.write(b'/exit\n')

    return result


class AppTest(unittest.TestCase):
    """
    Класс с тестами для чата.
    """
    def test_сonnect(self):
        """Метод-тест для проверки соединения."""
        result = connect_to_client('OLEG', 'P@ssw0rd')
        self.assertIn('Welcome to chat, OLEG!', result)

    def test_private(self):
        """
        Метод-тест для проверки отправки приватных сообщений.
        """
        result = send_private()
        self.assertIn('hello', result[1])
        self.assertNotIn('hello', result[2])

    def test_wrong_password(self):
        """
        Метод-тест для проверки ввода неверного пароля.
        """
        result = wrong_password()
        self.assertIn('You spent all tries', result)


if __name__ == "__main__":
    server = Process(target=start_server)
    test = Process(target=unittest.main)
    server.start()
    test.start()
    test.join()

    if server.is_alive():
        try:
            server.kill()
        except Exception as e:
            logger.error(f'kill error: {e}')
