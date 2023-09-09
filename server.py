"""
Модуль с описанием класса Server и самим запуском сервера.
"""
import logging
import sys
import asyncio
from asyncio.streams import StreamReader, StreamWriter
from datetime import datetime, timedelta

import aiofiles

from data_keeper import (
    active_writers,
    user_writer,
    user_password,
    writer_user,
    user_complain,
    user_msgcnt,
    user_starttime,
    user_ban,
)
from base_settings import ChatSettings


chat_settings = ChatSettings()
DATE_TIME_DELIMITER = chat_settings.DATE_TIME_DELIMITER
PRIVATE_MESSAGE_SIGN = chat_settings.PRIVATE_MESSAGE_SIGN
EXIT_SIGN = chat_settings.EXIT_SIGN
DATE_FORMAT = chat_settings.DATE_FORMAT
BACK_UP_FILE = chat_settings.BACK_UP_FILE
RULES = chat_settings.RULES
COMMANDS = chat_settings.COMMANDS
EMOJI = chat_settings.EMOJI

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


def delete_from_members(writer):
    """
    Функция удаляет всю информацию о пользователе,
    связанную с объектом StreamWriter
    """
    if writer in active_writers:
        active_writers.remove(writer)

    username = writer_user.get(writer, None)

    try:
        writers_list = user_writer[username]
        writers_list.remove(writer)
        user_writer[username] = writers_list
        if user_writer[username] == []:
            user_writer.pop(username)
        writer_user.pop(writer)

    except KeyError:
        logger.debug('some data for user avaible')


class Server:
    """
    Класс с описанием сервера.
    Возможные параметры запуска: хост, порт,
    количество сообщений для восстановления новым пользователям,
    время нахождения в бане (часы),
    время жизни сообщений, по истечение которого они не восстанавливаются
    из бэк-апа (часы),
    количество сообщенйи, которое может отправить один пользователь
    в заданный период времени (часы).
    """

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 8000,
                 back_up_size: int = 20,
                 ban_time: int = 4,
                 msg_ttl: int = 1,
                 max_msg_per_period: int = 20,
                 msg_period: int = 1):

        self.__host = host
        self.__port = port
        self.__back_up_size = back_up_size
        self.__ban_time = ban_time * 3600
        self.__msg_ttl = msg_ttl * 3600
        self.__max_msg_per_period = max_msg_per_period
        self.__msg_period = msg_period * 3600

    async def listen(self):
        """
        Корутина, запускающая сервер
        в режиме вечной обработки.
        """
        server = await asyncio.start_server(self.handler, self.__host,
                                            self.__port)
        async with server:
            await server.serve_forever()

    async def handler(self, reader: StreamReader, writer: StreamWriter):
        """
        Корутина, перехватывающая соединения.
        Производит авторизацию пользователя
        и запуск сервера в случае успеха авторизации.
        """
        try:
            address = writer.get_extra_info('peername')
            username, is_user_exist = await self.authorization(writer, reader)
        except Exception as e:
            logger.info(f'Client error while authorization: {e}')
            username = 'login_error'

        try:
            if username != 'login_error':
                logger.info('Start serving %s', address)
                logger.debug(writer)
                await self.start_serving(
                    is_user_exist,
                    writer,
                    reader,
                    address
                )
        except ConnectionResetError:
            logger.info('Client error while run: ConnectionResetError')

    async def authorization(self, writer: StreamWriter,
                            reader: StreamReader):
        """
        Корутина для авторизации пользователя.
        Запрашивает логин и пароль.
        Нового пользователя просто добавляет,
        для уже существующего проверяет корректность пароля.
        Возвращает пару: юзернейм, старый ли пользователь.
        В случае трижды неверно введенного пароля обрывает
        соединение с клиентом.
        """
        num_of_try = 0
        is_registation_succesfull = False
        logger.debug(user_password)
        while not is_registation_succesfull:
            username, password = await self.get_username_and_password(
                writer,
                reader
            )

            if user_password.get(username) is None:
                is_user_exist = False
            else:
                is_user_exist = True

            true_password = user_password.get(username, password)
            logger.info(true_password)

            if true_password == password:
                is_registation_succesfull = True
                await self.accept_user(username, password, writer)
                logger.debug(user_password)
                return username, is_user_exist
            else:
                fail_emj = EMOJI['fail']
                fail_message = f'{fail_emj} Wrong password. Try again.\n'
                writer.write(fail_message.encode())
                await writer.drain()
                num_of_try += 1

            if num_of_try > 3:
                error_emj = EMOJI['error']
                error_message = f'{error_emj} You spent all tries {error_emj}'
                writer.write(error_message.encode())
                await writer.drain()
                writer.close()
                logger.debug(user_password)

                return 'login_error', False

    async def accept_user(self, username: str, password: str,
                          writer: StreamWriter):
        """
        Корутина, добавляющая информацию о пользователе,
        делающая его полноправным участником чата.
        """
        success_emj = EMOJI['success']
        welcome_message = f'\n{success_emj} Welcome to chat, {username}!\n'
        writer.write(welcome_message.encode())
        await writer.drain()

        user_password[username] = password
        active_writers.append(writer)
        writers_list = user_writer.get(username, [])
        writers_list.append(writer)
        user_writer[username] = writers_list
        logger.info(f'user_writer:\t{user_writer}')
        writer_user[writer] = username

    async def start_serving(self, is_user_exist: bool, writer: StreamWriter,
                            reader: StreamReader, address: tuple):
        """
        Корутина для начала взаимодействия с сервером.
        Выводит бэк-ап и запускает клиента в общий чат.
        """
        if not is_user_exist:
            writer.write(RULES.encode())
            await writer.drain()
        try:
            await self.restore_back_up(
                writer, is_user_exist
            )
        except IndexError:
            logger.error('BACK_UP ERROR')

        try:
            await self.do_chating(address, writer, reader)
        except Exception as e:
            logger.error(f'chat_error {e}')

    async def get_username_and_password(self, writer: StreamWriter,
                                        reader: StreamReader):
        """
        Корутина, запрашивающая у пользователя логин и пароль
        с учетом, что логин должен является одним словом.
        """

        login_emj = EMOJI['login']
        is_username_correct = False
        while not is_username_correct:
            username_message = f'{login_emj} Enter username: '
            writer.write(username_message.encode())
            await writer.drain()

            username_bytes = await reader.read(1024)
            username = username_bytes.decode().strip()
            if len(username.split(' ')) == 1:
                is_username_correct = True
            else:
                err_emj = EMOJI['error']
                username_message = f'{err_emj} Use only one word\n'
                writer.write(username_message.encode())
                await writer.drain()

        password_message = f'{login_emj} Enter password: '
        writer.write(password_message.encode())
        await writer.drain()

        password_bytes = await reader.read(1024)
        password = password_bytes.decode().strip()
        return username, password

    async def restore_back_up(self, writer: StreamWriter,
                              is_user_exist: bool):
        """
        Корутина для вывода пользователю сообщений из бэк-апа.
        Получает аргументом объект StreamWriter и флаг,
        является ли вход повторным.
        Для нового пользователя выведет back_up_size последних сообщений.
        Для повторно зашедшего пользователя выведет все сообщения
        с момента его выхода.
        """

        try:
            async with aiofiles.open(BACK_UP_FILE, 'r') as back_up_file:
                back_up_messages = await back_up_file.readlines()

            back_up_messages = [
                message for message in back_up_messages
                if message.strip() != ''
            ]
            if not is_user_exist:
                await self.restore_messages_for_new_user(
                    back_up_messages, writer)
            else:
                await self.restore_messages_for_existing_user(
                    back_up_messages, writer)

        except FileNotFoundError:
            async with aiofiles.open(BACK_UP_FILE, 'w') as _:
                logger.info('Back-up file created')

    async def restore_messages_for_new_user(self, back_up_messages: list[str],
                                            writer: StreamWriter):
        """
        Корутина, выводящая новому пользователю последние
        back_up_size сообщений с учетом времени жизни сообщений.
        """
        logger.debug('NEW USER')
        cnt_of_messages = len(back_up_messages)
        num_first_message = max(0, cnt_of_messages - self.__back_up_size)
        for msg_num in range(num_first_message, cnt_of_messages):
            time = back_up_messages[msg_num].split(DATE_TIME_DELIMITER)[0]
            message = back_up_messages[msg_num].split(DATE_TIME_DELIMITER)[1]
            format_time = datetime.strptime(time, DATE_FORMAT)
            delta_time = timedelta(seconds=self.__msg_ttl)
            is_not_private = '/private' not in message
            if format_time + delta_time >= datetime.now() and is_not_private:
                writer.write(message.encode())
                await writer.drain()

    async def restore_messages_for_existing_user(self,
                                                 back_up_messages: list[str],
                                                 writer: StreamWriter):
        """
        Корутина для восстановления сообщений существующему пользователю
        с момента его выхода из чата.
        Ищется момент выхода пользователя и после него выводятся все
        пропущенные сообщения из общего чата.
        """
        logger.debug('OLD USER')

        cnt_of_messages = len(back_up_messages)
        num_first_message = 0
        username = writer_user[writer]
        for msg_num in range(cnt_of_messages):
            if f'{EXIT_SIGN} {username}' in back_up_messages[msg_num]:
                num_first_message = msg_num + 1

        for msg_num in range(num_first_message, cnt_of_messages):
            time = back_up_messages[msg_num].split(DATE_TIME_DELIMITER)[0]
            message = back_up_messages[msg_num].split(DATE_TIME_DELIMITER)[1]

            if datetime.strptime(time, DATE_FORMAT) + timedelta(
                    seconds=self.__msg_ttl) >= datetime.now():
                if '/private' not in message:
                    writer.write(message.encode())
                    await writer.drain()

                else:
                    sender_name = message.replace('\t', ' ').split(' ')[0][:-1]
                    recipient_name = message.replace(
                        '\t', ' ').split(' ')[2]
                    message_to_restore = ' '.join(
                        message.replace('\t', ' ').split(' ')[3:])

                    await self.show_back_up_if_recipient(
                        writer, sender_name, recipient_name,
                        message_to_restore)
                    await self.show_back_up_if_sender(writer, sender_name,
                                                      message)

    async def show_back_up_if_recipient(self, writer: StreamWriter,
                                        sender_name: str, recipient_name: str,
                                        message: str):
        """
        Корутина для вывода бэк-апа приватных сообщений в случае,
        если пользователем является получателем приватного сообщения.
        Получается объект StreamWriter для вошедшего пользователя,
        имя того, кому предназначалось приватное сообщение
        и само сообщение.
        """
        username = writer_user[writer]
        if username == recipient_name:
            private_message = f'{PRIVATE_MESSAGE_SIGN} {sender_name}:\t' \
                f'{message}\n'
            writer.write(private_message.encode())
            await writer.drain()

    async def show_back_up_if_sender(self, writer: StreamWriter,
                                     sender_name: str, message: str):
        """
        Корутина для вывода бэк-апа приватных сообщений в случае,
        если пользователем является отправителем приватного сообщения.
        Получается объект StreamWriter для вошедшего пользователя,
        имя того, кому предназначалось приватное сообщение
        и само сообщение.
        """
        username = writer_user[writer]
        if username == sender_name:
            writer.write(message.encode())
            await writer.drain()

    async def check_ban(self, username: str, cnt_of_complaints: int):
        """
        Корутина для проверки количества жалоб на пользователя
        и блокировки в случае превышения на ban_time часов.
        """
        writers_list = user_writer[username]

        if cnt_of_complaints > 2:
            logger.info(f'{username} was baned')
            ban_emj = EMOJI['ban']
            ban_message = f'{ban_emj} You was banned for '\
                f'{self.__ban_time/3600} houres {ban_emj}'
            user_ban[username] = True

            for writer in writers_list:
                writer.write(ban_message.encode())
                await writer.drain()
            await asyncio.sleep(self.__ban_time)

            user_complain[username] = set()
            info_emj = EMOJI['info']
            info_message = f'{info_emj} Your ban ended. Be careful'
            for writer in writers_list:
                writer.write(info_message.encode())
                await writer.drain()

            user_ban[username] = False
            logger.info(f'{username} free')

    def increase_msg_cnt(self, username):
        """
        Метод для подсчета количества отправленных сообщений пользователем.
        В случае, если это было его первое сообщение,
        инициализируется время начала чаттинга.
        """
        user_msgcnt[username] = user_msgcnt.get(username, 0) + 1
        if user_msgcnt[username] == 1:
            user_starttime[username] = datetime.now().strftime(DATE_FORMAT)
        return user_msgcnt[username]

    def is_message_over(self, username):
        """
        Метод для проверки превышения порога
        в max_msg_per_period сообщений.
        """
        if user_msgcnt.get(username, 0) > self.__max_msg_per_period:
            return True
        else:
            return False

    def is_period_over(self, username):
        """
        Метод для проверки окончания периода msg_period,
        в течение которого можно отправить max_msg_per_period сообщений.
        """
        now_time = datetime.now()
        start_period = user_starttime.get(username, now_time)
        if isinstance(start_period, str):
            end_period = datetime.strptime(
                start_period,
                DATE_FORMAT) + timedelta(seconds=self.__msg_period)
        else:
            end_period = start_period + timedelta(seconds=self.__msg_period)
        return now_time > end_period

    async def wait_end_of_period(self, username: str):
        """
        Корутина для блокировки пользователя.
        Используется, когда пользователь истратил весь лимит
        сообщений.
        Блокировка до окончания текущего периода.
        """
        writers_list = user_writer[username]
        logger.info(f'{username} lost spent all messages')

        now_time = datetime.now()
        start_period = user_starttime.get(username, now_time)
        delta_time = timedelta(seconds=self.__msg_period)
        if isinstance(start_period, str):
            end_period_time = datetime.strptime(
                start_period,
                DATE_FORMAT) + delta_time
        else:
            end_period_time = start_period + delta_time

        att_emj = EMOJI['attention']
        att_message = f'{att_emj} You spent all messages. ' \
            f'Wait until {end_period_time}'
        for writer in writers_list:
            writer.write(att_message.encode())
            await writer.drain()

        time_to_wait = end_period_time - datetime.now()
        logger.info(
            f'wait for {time_to_wait.seconds} sec; '
            f'now {datetime.now()}, end {end_period_time}'
        )

        await asyncio.sleep(time_to_wait.seconds)

        att_message = f'{att_emj} You can write messages again'
        for writer in writers_list:
            writer.write(att_message.encode())
            await writer.drain()
        logger.info(f'{username} can write messages again')

    async def do_chating(self, address: tuple, writer: StreamWriter,
                         reader: StreamReader):
        """
        Корутина, отлавливающая сообщения от пользователя.
        Происходит проверка количества отправленных сообщений
        и количество жалоб на пользователя.
        Обрабатываются команды, стандартные и приватные сообщения,
        а также выход пользователя из чата.
        """
        is_chating = True
        while is_chating:
            username = writer_user[writer]

            data = await reader.read(1024)
            if not data:
                is_chating = False
                break

            message = data.decode().strip()
            logger.debug(message)

            is_message_command = message in COMMANDS or '/ban' in message
            is_user_in_ban = user_ban.get(username, False)
            msg_cnt_per_period = user_msgcnt.get(username, 0)
            if not is_message_command and not is_user_in_ban:
                msg_cnt_per_period = self.increase_msg_cnt(username)

            await self.check_if_can_write(username, message)

            logger.info(f'user {username} send {msg_cnt_per_period} messages')
            is_chating = await self.choose_message_type(
                username,
                data,
                address,
                writer
            )

        logger.info('Clients in chat: %d', len(active_writers))
        logger.info('Stop serving %s', address)
        delete_from_members(writer)
        try:
            writer.close()
        except Exception as e:
            logger.info(f'conn close: {e}')

    async def check_if_can_write(self, username: str, message: str):
        """
        Корутина для проверки, имеет ли пользователь
        возможность отправлять сообщения.
        Если пользователь перешел лимит сообщений,
        то ожидает до конца периода.
        В конце периода время и количество сообщений сбрасывается.
        """
        try:
            if message not in COMMANDS and not self.is_period_over(
                    username) and self.is_message_over(username):
                await self.wait_end_of_period(username)

        except ConnectionResetError:
            logger.error(f'user {username} lost connection during waiting')

        if self.is_period_over(username):
            user_starttime[username] = datetime.now()
            user_msgcnt[username] = 1

    async def choose_message_type(self, username: str, data: bytes,
                                  address: tuple, writer: StreamWriter):
        """
        Корутина с разветвлением в зависимости от типа сообщения.
        Запрещает отправлять сообщения забаненому пользователю,
        выполняет команды и отправляет сообщения в общий чат.
        Вовращает флаг, оставлять ли пользователя в чате.
        """
        cnt_of_complaints = len(user_complain.get(username, set()))
        message = data.decode().strip()
        is_chating = True
        if cnt_of_complaints > 2 and message not in COMMANDS:
            logger.info(
                f'banned {username} try to send message: {message}')

        elif message == '/exit':
            logger.info('Client %s wants to end the chat session', address)
            await self.turn_out_user(writer, username)
            is_chating = False

        elif message == '/status':
            await self.show_status(writer)

        elif message == '/rules':
            writer.write(RULES.encode())
            await writer.drain()

        elif '/private' in message:
            logger.info(f'Private: {message}')
            await self.send_private(writer, data)

        elif '/ban' in message:
            intruder_username = ' '.join(message.split(' ')[1:])
            logger.info(
                f'User {writer_user[writer]} wanna ban {intruder_username}'
            )
            await self.add_complain(intruder_username, writer)
        else:
            await self.send_all(username, data)
        return is_chating

    async def turn_out_user(self, writer: StreamWriter, username: str):
        """
        Корутина для отключения пользователя от чата.
        Отправляет флаг клиенту и сообщение о выходе
        другим пользователям чата.
        Также удаляет информацию об объекте StreamWriter.
        """
        try:
            writer.write(b'/end')
            await self.send_bye_message(writer, username)
        except Exception as e:
            logger.info(f'client out already: {e}')
        delete_from_members(writer)

    async def show_status(self, writer: StreamWriter):
        """
        Корутина для вывода состояния чата.
        """
        status = 'CHAT INFO:\n' \
            f'*\tHOST = {self.__host}\n' \
            f'*\tPORT = {self.__port}\n' \
            f'*\tUSERS ONLINE:\n'

        writer.write(status.encode())
        await writer.drain()
        for user in user_writer:
            msg = f'\t*\t{user}\n'
            writer.write(msg.encode())
            await writer.drain()

    async def send_bye_message(self, writer: StreamWriter, username: str):
        """
        Корутина для отправки сообщения о выходе пользователя из чата.
        Сообщение также фиксируется в бэк-апе.
        """
        bye_message = f'{EXIT_SIGN} {username} left the chat'

        for some_writer in active_writers:
            if some_writer is not writer:
                some_writer.write(bye_message.encode())
                await some_writer.drain()

        await self.store_message(username, bye_message.encode())

    async def add_complain(self, intruder_username: str,
                           sender_writer: StreamWriter):
        """
        Корутина для отправки жалоб на пользователя.
        В случае отсутсвия пользователя отсылает отправителю жалобы
        сообщение об ошибке,
        иначе добавляет пользователю жалобу, идентифицирующую как
        имя отправителя жалобы.
        Проверяется количество жалоб, и в случае привышения
        пользователь блокируется.
        """
        if intruder_username not in user_password or writer_user[
                sender_writer] == intruder_username:
            error_emj = EMOJI['error']
            message = f'{error_emj} Ban error: check username'
            sender_writer.write(message.encode())
            await sender_writer.drain()

        else:
            user_complain[intruder_username] = user_complain.get(
                intruder_username, set())

            if writer_user[sender_writer] not in user_complain[
                    intruder_username]:
                user_complain[intruder_username].add(
                    writer_user[sender_writer])
                logger.debug(user_complain[intruder_username])
                att_emj = EMOJI['attention']
                message = f'{att_emj} Someone complained about you. ' \
                    f'Number of complaints: ' \
                    f'{len(user_complain[intruder_username])}'

                for writer in user_writer[intruder_username]:
                    writer.write(message.encode())
                    await writer.drain()

                cnt_of_complaints = len(
                    user_complain.get(intruder_username, set()))

                await self.check_ban(intruder_username, cnt_of_complaints)

    async def send_private(self, sender_writer: StreamWriter, data: bytes):
        """
        Корутина для отправки приватных сообщений.
        В случае некорректного запроса отправителю
        выводится сообщение об ошибке,
        иначе получателю выводится приватное сообщение.
        """
        sender_name = writer_user[sender_writer]
        try:
            recipient_name = data.decode().split(' ')[1]
            message = ' '.join(data.decode().split(' ')[2:])
            logger.debug(recipient_name)
            logger.debug(message)

            private_message = f'{PRIVATE_MESSAGE_SIGN} {sender_name}:\t'\
                f'{message}'

            att_emj = EMOJI['attention']
            if recipient_name in user_writer and message != '\n':
                for writer in user_writer[recipient_name]:
                    writer.write(private_message.encode())
                    await writer.drain()
                await self.store_message(sender_name, data)

            else:
                att_message = f'{att_emj} {recipient_name} : No such user\n'
                sender_writer.write(att_message.encode())
                await sender_writer.drain()

        except IndexError:
            error_emj = EMOJI['error']
            error_message = f'{error_emj} ' \
                'Incorrect syntax for private message.\n' \
                'Template: /private <username> <message>\n'
            sender_writer.write(error_message.encode())
            await sender_writer.drain()

    async def send_all(self, sender_name: str,
                       data: bytes):
        """
        Корутина для отправки сообщений в общий чат.
        Для отправителя сообщение выводится с приставкой "you".
        """
        await self.store_message(sender_name, data)
        if data.decode().strip() != '':
            for some_writer in active_writers:
                if writer_user[some_writer] != sender_name:
                    data_to_send = f'{sender_name}:\t{data.decode()}'
                    some_writer.write(data_to_send.encode())
                    await some_writer.drain()
                else:
                    data_to_send = f'you:\t{data.decode()}'
                    some_writer.write(data_to_send.encode())
                    await some_writer.drain()

    async def store_message(self, sender_name: str, data: bytes):
        """
        Корутина для сохранения сообщений в бэк-ап.
        """
        async with aiofiles.open(BACK_UP_FILE, 'a') as back_up_file:
            message_time_datetime = datetime.now()
            message_time = message_time_datetime.strftime(DATE_FORMAT)
            back_up_message = f'{message_time}{DATE_TIME_DELIMITER}' \
                f'{sender_name}:\t{data.decode()}\n'
            await back_up_file.write(back_up_message)


if __name__ == '__main__':
    chat_server = Server()
    with open(BACK_UP_FILE, 'w') as _:
        logger.info('\nBack-up file was cleared')
    try:
        asyncio.run(chat_server.listen())
    except (KeyboardInterrupt, RuntimeError):
        logger.info('\nServer was stoped')
