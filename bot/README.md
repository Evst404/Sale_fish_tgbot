Echo-бот на стейт-машине (aiogram 3 + Redis)
================================================

Запуск
------
1) Создайте окружение и установите зависимости:
   ```bash
   cd bot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2) Настройте переменные окружения: скопируйте `.env.example` в `.env` и пропишите `BOT_TOKEN` (уже проставлен в текущем `.env`), при необходимости поправьте `REDIS_*`.
   Для кнопок и корзины добавьте `STRAPI_URL`, `STRAPI_URL_BASE`, `STRAPI_TOKEN` (read-only) и `STRAPI_TOKEN_WRITE` (Full Access для создания корзин).
3) Запустите Redis (если он не работает):
   ```bash
   redis-server --daemonize yes
   ```
   Проверка: `redis-cli ping` → `PONG`.
4) Старт бота:
   ```bash
   source .venv/bin/activate
   python main.py
   ```

Кнопки с товарами
-----------------
- `/start` запрашивает товары из Strapi (`STRAPI_URL`, `STRAPI_TOKEN`) и строит инлайн-кнопки с названиями, переводит в состояние HANDLE_MENU.
- Нажатие на товар делает запрос за подробностями по ID (`STRAPI_URL_BASE`) и показывает название, цену и описание, плюс кнопку «Назад к списку».
- Кнопка «Добавить в корзину» создаёт пустую корзину с `telegram_id` пользователя через POST `/api/carts` (использует `STRAPI_TOKEN_WRITE`, иначе `STRAPI_TOKEN`).

Как работает стейт-машина
-------------------------
- `/start` → устанавливает состояние `EchoStates.waiting_message` и ждёт ввод.
- Любое текстовое сообщение в этом состоянии отзеркаливается и оставляет бота в том же состоянии.
- `/cancel` очищает состояние, при необходимости можно снова вызвать `/start`.
