# Запуск

- Виртуальное окружение:
    * poetry shell
    * poetry install
- Клиент: python3 client.py
- Сервер: python3 server.py
- Тестирование: python3 tests.py



# Чаттинг

При подключении введите логин и пароль.
Внимание! Логин не должен содержать пробельных символов.

Если у вас уже есть существующий аккаунт, введите тот пароль, который вы использовали при регистрации.
У вас будет три попытки.
При входе вам выведутся все сообщения, которые вы пропустили за время своего отсутствия, в том числе приватные.

Если вы только зарегистрировались, вам будет выведена небольшая справка о существовании в чате, а также несколько последних сообщений.

Внимание! Все сообщения хранятся определенное время. По истечении этого срока (по умолчанию, 1 час) их невозможно будет восстановить.

## Команды
* /rules - повторный просмотр справки.
* /status - посмотреть информацию о чате: например, пользователи онлайн.
* /private - отправить приватное сообщение. Шаблон можете увидеть в справке. Если кто-то вам отправит такое сообщение, оно будет выделено ">>". Можно отправлять сообщения в чат с самим собой в качестве заметок.
* /ban - отправить жалобу на пользователя. Шаблон также в справке.
* /exit - выйти из чата.

Чтобы отправить сообщение в общий чат, просто наберите его и нажмите Enter.

Вы можете заходить в чат с нескольких устройств. Их состояния синхронизированы.

Будьте вежливы в чате, так как, если на вас пожалуются хотя бы три пользователя, вы будете заблокированы на некоторое время и не сможете участвовать в обсуждении.
Не беспокойтесь, один и тот же пользователь не сможет отправить на вас более одной жалобы.

В чате установлено ограничение на количество сообщений за период времени.
По умолчанию это 20 сообщений в час (если иное не указал администратор сервера).
Когда вы истратите все сообщения, вам придется ждать до конца периода.
Вы не сможете обойти это ограничение входом с другого устройства.
Как только вы исчерпаете лимит, вы будете крайне ограничены в действиях.
В случае, если вам надоест просто наблюдать за участниками чата, нажмите ctrl+C для выхода.


***Если вы запускаете на MacOS, при завершении работы может выпадать исполючение RuntimeError. Я использую Windows и Ubuntu и данное исключение оследить не могу.***

