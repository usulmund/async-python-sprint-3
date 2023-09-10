"""
Модуль с описанием класса ChatSettings,
содержит настройки чата.
"""
from pydantic import BaseSettings


class ChatSettings(BaseSettings):

    HOST: str = '127.0.0.1'
    PORT: int = 8000
    BACK_UP_SIZE: int = 20
    BAN_TIME: int = 4
    MSG_TTL: int = 1
    MAX_MSG_PER_PERIOD: int = 20
    MSG_PERIOD: int = 1

    DATE_DELIMITER: str = ' % '
    PRIVATE_MESSAGE_SIGN: str = '>>'
    EXIT_SIGN: str = '~~'
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    BACK_UP_FILE: str = 'back_up_messages.txt'
    RULES: str = '_______________________________________________________\n' \
        'Use this app to communicate in public and private chats.\n' \
        'Be polite with other chat-members, ' \
        'otherwise you can get ban after 3 complaints.\n' \
        '\nSome templates:\n' \
        '*\t/rules -- show rules of chat\n' \
        '*\t/status -- show info about chat\n' \
        '*\t/private <username> <message> -- send private message\n' \
        '*\t/ban <username> -- complain about some user\n\n' \
        'Enter "/exit" to out from chat\n' \
        '_______________________________________________________\n'
    EMOJI: dict[str, str] = {
        'login': '(^o^)',
        'ban': '(!_!)',
        'info': '(=-=)',
        'error': '(@_@)',
        'attention': '(*0*)',
        'success': '!(*o*)!',
        'fail': '(-_-;)',
    }
