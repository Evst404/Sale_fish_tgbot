# Sale Fish Telegram Bot

Бот на aiogram для витрины/корзины с интеграцией со Strapi API и сбором email.

## Как запустить
1) Перейдите в каталог `bot`:
   ```bash
   cd bot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2) Настройте переменные окружения: скопируйте `.env.example` в `.env` и заполните:
   - `BOT_TOKEN`
   - `STRAPI_URL_BASE` и `STRAPI_URL`
   - `STRAPI_TOKEN` (чтение) и `STRAPI_TOKEN_WRITE` (create/update)
   - `REDIS_HOST/PORT/DB`
3) Запустите Redis локально (или используйте внешний):
   ```bash
   redis-server --daemonize yes
   redis-cli ping  # должно быть PONG
   ```
4) Запуск бота:
   ```bash
   source .venv/bin/activate
   python main.py
   ```

## Функционал
- Список товаров из Strapi, карточка с фото/ценой/описанием.
- Корзина: добавление, просмотр, удаление позиций, переход в меню.
- Оплата: запрос email, сохранение контакта в коллекцию `Client` на стороне Strapi.

## Что в репозитории
- `bot/` — исходный код бота, `requirements.txt`, `.env.example`, README.
- `.gitignore` — игнорирует окружения, временные файлы, дампы.

Страница решения: https://github.com/Evst404/Sale_fish_tgbot
