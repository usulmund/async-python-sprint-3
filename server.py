import logging
import sys
import asyncio
from asyncio.streams import StreamReader, StreamWriter
import os

from bidict import bidict
import aiofiles
# приватный чат - отправлять сообщения только определенному юзеру
# удобно ли использовать словарь?


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


from data_keeper import active_writers, addr_user, uniq_names, user_writer, user_password



BACK_UP_FILE = 'back_up_messages.txt'



# придумать как выводить пользователю приватные сообщения
# видимо сохранять в бэк ап кому они отправлялись и сравнивать с именем пользователя

def delete_from_members(writer):
    if writer in active_writers:
        active_writers.remove(writer)

class Server:
    def __init__(self, host="127.0.0.1", port=8000, back_up_size=20):
        self.__host = host
        self.__port = port
        self.__back_up_size = back_up_size

    async def listen(self):
        server = await asyncio.start_server(
          self.handler,
          self.__host,
          self.__port  
        )
        async with server:
            await server.serve_forever()
    
    async def handler(self, reader: StreamReader, writer: StreamWriter):
        address = writer.get_extra_info('peername')
        username, is_user_exist = await self.authorization(writer, reader, address)
        if username != 'login_error':
            logger.info('Start serving %s', address)
            logger.debug(writer)
            # if is_new_member:
            await self.restore_back_up(username, is_user_exist)
            await self.do_chating(address, writer, reader)
    
    async def authorization(self, writer: StreamWriter, reader: StreamReader, address):
        num_of_try = 0
        is_registation_succesfull = False
        logger.debug(user_password)
        while not is_registation_succesfull:
            writer.write(
                b'Enter username: '
            )
            await writer.drain()
            username = await reader.read(1024)
            username = username.decode().strip()
            
            writer.write(
                b'Enter password: '
            )
            await writer.drain()
            password = await reader.read(1024)
            password = password.decode().strip()

            if user_password.get(username) == None:
                is_user_exist = False
            else:
                is_user_exist = True


            true_password = user_password.get(username, password)
            logger.info(true_password)

            if true_password == password:
                is_registation_succesfull = True
                writer.write(
                    b'Welcome to chat, ' + username.encode() + b'!\n'
                )
                await writer.drain()
                user_password[username] = password
                # uniq_names.add(username)
                addr_user[address] = username
                active_writers.append(writer)
                user_writer[username] = writer
                logger.debug(user_password)

                return username, is_user_exist
            else:
                writer.write(
                    b'Wrong password. Try again.\n'
                )
                await writer.drain()   
                num_of_try += 1
            if num_of_try > 3:
                writer.write(
                    b'You spend all tries :('
                )
                await writer.drain()
                writer.close()
                #break
                logger.debug(user_password)

                return 'login_error', False


    async def restore_back_up(self, username, is_user_exist):
        writer: StreamWriter = user_writer[username]

        try:
            async with aiofiles.open(BACK_UP_FILE, 'r') as back_up_file:
                back_up_messages = await back_up_file.readlines()
            
            cnt_of_messages = len(back_up_messages)
            if not is_user_exist:
                num_first_message = max(0, cnt_of_messages - self.__back_up_size + 1)
                for msg_num in range(num_first_message, cnt_of_messages):
                    message = back_up_messages[msg_num]
                    writer.write(message.encode())
                    await writer.drain()
            else:
                
                num_first_message = 0
                for msg_num in range(cnt_of_messages):
                    if f'~~ {username}' in back_up_messages[msg_num]:
                        num_first_message = msg_num + 1

                for msg_num in range(num_first_message, cnt_of_messages):
                    message = back_up_messages[msg_num]
                # for message in back_up_messages:
                    # try:
                    #     while f'~~ {username}'
                    # except StopIteration:
                    #     logger.info('No messages to back-up')
                    if '/private' not in message:
                        writer.write(message.encode())
                        await writer.drain()
                    else: # b:	/private a mem
                        
                        sender_name = message.replace('\t', ' ').split(' ')[0][:-1]
                        recipient_name = message.replace('\t', ' ').split(' ')[2] # если для получателя
                        message_to_restore = ' '.join(message.replace('\t', ' ').split(' ')[3:])

                        # # отображение приватного сообщения получателю
                        await self.show_back_up_if_recipient(username, recipient_name, message_to_restore)
                        
                        await self.show_back_up_if_sender(username, sender_name, message)
                                     

        except FileNotFoundError:
            async with aiofiles.open(BACK_UP_FILE, 'w') as _:
                logger.info('Back-up file created')
    
    # опасно - протестировать
    async def show_back_up_if_recipient(self, username, recipient_name, message):
        # обработать кей ерор
        recipient_writer = user_writer[recipient_name]
        if recipient_writer in active_writers and username == recipient_name:
            data_to_send =  b'>> Private message from ' + recipient_writer.encode() + b':\t' + message.encode()
            recipient_writer.write(data_to_send)
            await recipient_writer.drain()

    async def show_back_up_if_sender(self, username, sender_name, message):
        # обработать кей ерор
        sender_writer = user_writer[sender_name]
        if sender_writer in active_writers and username == sender_name:
            sender_writer.write(message.encode())
            await sender_writer.drain() 


    async def do_chating(self, address, writer: StreamWriter, reader: StreamReader):
        is_chating = True
        while is_chating:

            data = await reader.read(1024)
            if not data:
                is_chating = False

            message = data.decode().strip()
            logger.debug(message)
            #is_chating = await chat_member.send(data)
            message = data.decode().strip()
            # print(message)
            if message == 'exit':
                logger.info('Client %s wants to end the chat session', address)
                writer.write(b'/end')
                await self.send_bye_message(writer, address)
                is_chating = False
                delete_from_members(writer)
                # обработать все удаления и что оставить чтобы можно было повторно зайти
                # !!!!!!!!!!
                # хотя мб и не удалять имена а хранить аккаунты
                # но нужен пароль
                # удалять при выходе из уникальных имен
                # удалить везде!!!!
            elif '/private' in message:
                logger.info(f'private: {message}')
                await self.send_private(address, data)
                await writer.drain()
            else:
                await self.send_all(writer, address, data)
                await writer.drain()

        logger.info('Clients in chat: %d', len(active_writers))

        logger.info('Stop serving %s', address)  # сделать выход из сервера по команде aioconsole
        writer.close()

    async def send_private(self, sender_address, data):
        sender_name =  addr_user[sender_address]
        sender_writer = user_writer[sender_name]
        
        # обработать пустые сообщения
        try:
            recipient_name = data.decode().split(' ')[1]
            message = ' '.join(data.decode().split(' ')[2:])
            logger.debug(recipient_name)
            logger.debug(message)
            data_to_send =  b'>> Private message from ' + sender_name.encode() + b':\t' + message.encode()
            if recipient_name in user_writer and message != '\n':
                recipient_writer = user_writer[recipient_name]
                recipient_writer.write(data_to_send)
                await self.store_message(sender_name, data)
            elif message == '\n':
                sender_writer.write(b'You tried to send empty message\n')
            else:
                sender_writer.write(recipient_name.encode() + b': No such user\n')
        except IndexError:
            sender_writer.write(b'Incorrect syntax for private message. ' \
                            b'Template: /private <username> <message>\n')

    async def send_all(self, writer: StreamWriter, address, data):
        sender_name = addr_user[address]

        await self.store_message(sender_name, data)
        for some_writer in active_writers:
            if not some_writer is writer:
                data_to_send = sender_name.encode() + b':\t' + data
                some_writer.write(data_to_send)
    
    async def store_message(self, sender_name, data):
        # if self.is_back_up_full():
        #     async with aiofiles.open(BACK_UP_FILE, 'r') as back_up_file:
        #         messages = await back_up_file.readlines()
        #     async with aiofiles.open(BACK_UP_FILE, 'w') as back_up_file: #
        #         await back_up_file.writelines(messages[1:])

        async with aiofiles.open(BACK_UP_FILE, 'a') as back_up_file:
            back_up_message = f'{sender_name}:\t{data.decode()}\n'
            await back_up_file.write(back_up_message)

    # def is_back_up_full(self):
    #     message_cnt = 0
    #     # try:
    #     #     with open(BACK_UP_FILE, 'r') as back_up_file:
    #     #         for line in back_up_file:
    #     #             message_cnt += 1
    #     # except FileNotFoundError:
    #     #     with open(BACK_UP_FILE, 'w') as back_up_file:
    #     #         logger.info('Back-up file created')
    #     with open(BACK_UP_FILE, 'r') as back_up_file:
    #         for line in back_up_file:
    #             message_cnt += 1

    #     print(f'msg_cnt: {message_cnt}')
    #     return message_cnt >= self.__back_up_size


    async def send_bye_message(self, writer: StreamWriter, address):
        bye_message = f'~~ {addr_user[address]} left the chat'

        for some_writer in active_writers:
            if not some_writer is writer:
                some_writer.write(bye_message.encode())
        
        await self.store_message(addr_user[address], bye_message.encode())

if __name__ == '__main__':
    chat_server = Server()
    try:
        asyncio.run(chat_server.listen())
    except KeyboardInterrupt:
        # for writer in active_writers:
        #     writer.close()
        with open(BACK_UP_FILE, 'w') as _:
            logger.info('\nBack-up file was cleared')
        logger.info('\nServer was stoped')
    
    