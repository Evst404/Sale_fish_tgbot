# Sale Fish CMS & Bot

Локальная Strapi CMS + Telegram-бот (aiogram) для витрины/корзины.

## Запуск Strapi
1) Node 22 через `nvm use 22`.
2) Из каталога `my-strapi-app`:
   ```bash
   npm install   # при необходимости
   npm run develop
   ```
3) Админка: `http://localhost:1337/admin`.
4) Основные типы:
   - `Product`: title, description, picture (media), price.
   - `Cart`: telegram_id, items (repeatable component cart-item с product + quantity).
   - `Client`: telegram_id, email.

## Запуск бота
1) Redis: `redis-server --daemonize yes` (проверка `redis-cli ping` → PONG).
2) Бот:
   ```bash
   cd ../bot
   source .venv/bin/activate
   python main.py
   ```
3) Переменные (см. `bot/.env.example`, не коммитить):
   - `BOT_TOKEN`
   - `STRAPI_URL_BASE`, `STRAPI_URL`
   - `STRAPI_TOKEN` (read), `STRAPI_TOKEN_WRITE` (full access)
   - `REDIS_HOST/PORT/DB`

Функционал бота:
- Каталог с кнопками, карточка товара с фото/ценой/описанием.
- Корзина: добавление, просмотр, удаление позиций, «В меню».
- Оплата: запрос email, сохранение в коллекцию `Client`.

## Проверка данных
- Корзины: Content Manager → Cart.
- Клиенты: Content Manager → Client.
- API пример:  
  `curl -H "Authorization: Bearer <token>" "http://localhost:1337/api/clients"`

## Замечания
- Не коммить `.env` и токены.
- Если бот пишет Conflict — запущен второй экземпляр, остановите лишний процесс (Ctrl+C).***
