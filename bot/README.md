Магазин-бот на aiogram 3 + Redis + Strapi

Установка
---------
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Настройка
---------
1) Скопируйте `.env.example` из корня в `bot/.env` и заполните:
   - `BOT_TOKEN`
   - `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
   - `STRAPI_URL_BASE`, `STRAPI_URL`, `STRAPI_TOKEN`, `STRAPI_TOKEN_WRITE`
2) Запустите Redis и убедитесь, что `redis-cli ping` возвращает `PONG`.

Запуск
------
```bash
source .venv/bin/activate
python3 main.py
```

Поведение
---------
- `/start` загружает товары из Strapi, строит инлайн-меню.
- Карточка товара показывает описание, цену, фото (если есть), кнопки «Добавить в корзину», «Моя корзина», «Назад».
- Корзина показывает позиции, позволяет удалять, кнопка «Оплатить» запрашивает email и сохраняет его в Strapi.
- Состояния и корзина хранятся в Redis.
