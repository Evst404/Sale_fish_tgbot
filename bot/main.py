import asyncio
import logging
import os
import io
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qsl, urlunparse, quote

import redis.asyncio as redis
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BufferedInputFile,
)
from dotenv import load_dotenv


@dataclass
class StrapiConfig:
    url_base: str
    products_url: str
    products_params: Dict[str, str]
    token_read: Optional[str]
    token_write: Optional[str]

    @property
    def auth_token(self) -> Optional[str]:
        return self.token_write or self.token_read


_strapi_config: Optional[StrapiConfig] = None


def set_strapi_config(config: StrapiConfig) -> None:
    global _strapi_config
    _strapi_config = config


def get_strapi_config() -> StrapiConfig:
    if _strapi_config is None:
        raise RuntimeError("Strapi config is not initialized")
    return _strapi_config


def build_strapi_config_from_env() -> StrapiConfig:
    url_base = os.getenv("STRAPI_URL_BASE", "http://localhost:1337")
    products_env = os.getenv("STRAPI_URL")
    if products_env:
        parsed = urlparse(products_env)
        products_url = urlunparse(parsed._replace(query="", fragment=""))
        products_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    else:
        products_url = f"{url_base}/api/products"
        products_params = {"populate": "*"}

    return StrapiConfig(
        url_base=url_base,
        products_url=products_url,
        products_params=products_params,
        token_read=os.getenv("STRAPI_TOKEN"),
        token_write=os.getenv("STRAPI_TOKEN_WRITE"),
    )


class ShopStates(StatesGroup):
    handle_menu = State()
    handle_cart = State()
    waiting_email = State()


async def fetch_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    config = get_strapi_config()
    url = f"{config.url_base}/api/products/{quote(str(product_id))}"
    token = config.token_read
    params = {"populate": "*"}

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            payload = await resp.json()
            return payload.get("data")


async def create_cart(telegram_id: str) -> Dict[str, Any]:
    
    config = get_strapi_config()
    url = f"{config.url_base}/api/carts"
    token = config.auth_token

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {"data": {"telegram_id": telegram_id}}

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 409:
                return {"error": "Cart already exists"}
            resp.raise_for_status()
            return await resp.json()


async def fetch_cart_by_telegram(telegram_id: str) -> Optional[Dict[str, Any]]:
   
    config = get_strapi_config()
    url = f"{config.url_base}/api/carts"
    token = config.auth_token
    params = {
        "filters[telegram_id][$eq]": telegram_id,
        "populate[items][populate][product]": "true",
    }

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            payload = await resp.json()
            carts = payload.get("data") or []
            return carts[0] if carts else None


async def fetch_client_by_telegram(telegram_id: str) -> Optional[Dict[str, Any]]:
    
    config = get_strapi_config()
    url = f"{config.url_base}/api/clients"
    token = config.auth_token
    params = {"filters[telegram_id][$eq]": telegram_id}

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            payload = await resp.json()
            clients = payload.get("data") or []
            return clients[0] if clients else None


async def upsert_client_email(telegram_id: str, email: str) -> None:
   
    config = get_strapi_config()
    token = config.auth_token

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    existing = await fetch_client_by_telegram(telegram_id)
    timeout = aiohttp.ClientTimeout(total=10)

    if not existing:
        payload = {"data": {"telegram_id": telegram_id, "email": email}}
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{config.url_base}/api/clients", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                await resp.json()
        return

    client_doc_id = existing.get("documentId") or existing.get("id")
    payload = {"data": {"email": email}}
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.put(f"{config.url_base}/api/clients/{client_doc_id}", headers=headers, json=payload) as resp:
            resp.raise_for_status()
            await resp.json()


async def upsert_cart_with_item(telegram_id: str, product_id: int, quantity: float = 1.0) -> None:
    
    config = get_strapi_config()
    token = config.auth_token

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    existing_cart = await fetch_cart_by_telegram(telegram_id)

    if not existing_cart:
        payload = {"data": {"telegram_id": telegram_id, "items": [{"product": product_id, "quantity": quantity}]}}
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{config.url_base}/api/carts", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                await resp.json()
        return

    cart_id = existing_cart.get("id")
    cart_doc_id = existing_cart.get("documentId") or cart_id
    current_items = existing_cart.get("items") or []

    new_items: List[Dict[str, Any]] = []
    for item in current_items:
        prod = item.get("product")
        prod_id = None
        if isinstance(prod, dict):
            prod_id = prod.get("id")
        if prod_id is not None:
            entry: Dict[str, Any] = {"product": prod_id, "quantity": item.get("quantity", 1)}
            new_items.append(entry)

    new_items.append({"product": product_id, "quantity": quantity})

    payload = {"data": {"items": new_items}}
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.put(f"{config.url_base}/api/carts/{cart_doc_id}", headers=headers, json=payload) as resp:
            resp.raise_for_status()
            await resp.json()


async def update_cart_items(cart_doc_id: str, items: List[Dict[str, Any]]) -> None:
    
    config = get_strapi_config()
    token = config.auth_token

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {"data": {"items": items}}
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.put(f"{config.url_base}/api/carts/{cart_doc_id}", headers=headers, json=payload) as resp:
            resp.raise_for_status()
            await resp.json()


async def download_image(url: str, session: Optional[aiohttp.ClientSession] = None) -> Optional[BufferedInputFile]:
  
    close_session = False
    if session is None:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        close_session = True
    try:
        async with session.get(url) as resp:
            if not resp.ok:
                return None
            data = await resp.read()
            filename = url.split("/")[-1] or "image.jpg"
            return BufferedInputFile(data, filename=filename)
    finally:
        if close_session:
            await session.close()


def _chunk_buttons(buttons: List[InlineKeyboardButton], width: int = 2) -> List[List[InlineKeyboardButton]]:
    
    rows: List[List[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), width):
        rows.append(buttons[i : i + width])
    return rows


async def fetch_products() -> List[Dict[str, Any]]:
    
    config = get_strapi_config()
    url = config.products_url
    params = config.products_params
    token = config.token_read

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            payload = await resp.json()
            return payload.get("data", [])


async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ShopStates.handle_menu)
    await send_products_menu(message)


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Состояние сброшено. Наберите /start чтобы начать заново.")


async def echo(message: Message, state: FSMContext) -> None:
   
    await state.set_state(ShopStates.handle_menu)
    await message.answer("Используйте кнопки или команду /start, чтобы выбрать товар.")


async def echo_email(message: Message, state: FSMContext) -> None:
    email = message.text.strip()
    telegram_id = str(message.from_user.id)

    try:
        await upsert_client_email(telegram_id, email)
    except Exception as exc:
        logging.exception("Не удалось записать email: %s", exc)
        await message.answer("Не удалось сохранить почту. Попробуйте позже.")
        return

    await state.clear()
    logging.info("Получен email от %s: %s", message.from_user.id, email)
    await message.answer(f"Спасибо! Ваша почта: {email}. Мы свяжемся для оплаты.")


async def send_products_menu(target: Message) -> None:
    try:
        products = await fetch_products()
    except Exception as exc:
        logging.exception("Не удалось получить товары: %s", exc)
        await target.answer("Не удалось получить список товаров. Попробуйте позже.")
        return

    if not products:
        await target.answer("Товары не найдены.")
        return

    buttons = []
    for item in products:
        doc_id = item.get("documentId") or str(item.get("id"))
        numeric_id = item.get("id")
        title = item.get("title") or f"Товар #{numeric_id}"
        buttons.append(
            InlineKeyboardButton(
                text=title,
                callback_data=f"product:{numeric_id}:{doc_id}",
            )
        )

    rows = _chunk_buttons(buttons, width=2)
    rows.append([InlineKeyboardButton(text="🧺 Моя корзина", callback_data="mycart")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    await target.answer(
        "Выберите товар по кнопке ниже.",
        reply_markup=keyboard,
    )


async def render_cart(message: Message, telegram_id: str) -> None:
    
    cart = await fetch_cart_by_telegram(telegram_id)
    if not cart or not cart.get("items"):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="back_to_list")]]
        )
        await message.answer("Ваша корзина пуста.", reply_markup=keyboard)
        return

    items = cart.get("items", [])
    lines = ["Ваша корзина:"]
    buttons_rows: List[List[InlineKeyboardButton]] = []
    for idx, item in enumerate(items, start=1):
        prod = item.get("product") or {}
        title = prod.get("title") or f"Товар #{prod.get('id')}"
        qty = item.get("quantity") or 1
        price = prod.get("price")
        price_part = f" — {price}" if price is not None else ""
        lines.append(f"{idx}. {title} x {qty}{price_part}")
        buttons_rows.append([InlineKeyboardButton(text=f"Убрать {idx}", callback_data=f"cart_remove:{idx-1}")])

    buttons_rows.append(
        [
            InlineKeyboardButton(text="Оплатить", callback_data="checkout"),
            InlineKeyboardButton(text="В меню", callback_data="back_to_list"),
        ]
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons_rows)
    await message.answer("\n".join(lines), reply_markup=keyboard)


async def handle_button(callback: CallbackQuery, state: FSMContext) -> None:
    callback_data = callback.data or ""
    if callback_data == "mycart":
        await state.set_state(ShopStates.handle_cart)
    else:
        await state.set_state(ShopStates.handle_menu)
    await callback.answer()

    if callback_data == "back_to_list":
        await state.set_state(ShopStates.handle_menu)
        await send_products_menu(callback.message)
        return

    if callback_data == "mycart":
        telegram_id = str(callback.from_user.id)
        await render_cart(callback.message, telegram_id)
        return
    if callback_data == "checkout":
        await state.set_state(ShopStates.waiting_email)
        await callback.message.answer("Введите вашу почту для оформления:")
        return

    if callback_data.startswith("cart_remove:"):
        telegram_id = str(callback.from_user.id)
        try:
            idx_str = callback_data.split(":", 1)[1]
            idx = int(idx_str)
        except Exception:
            await callback.message.answer("Некорректный номер позиции.")
            return

        cart = await fetch_cart_by_telegram(telegram_id)
        if not cart:
            await callback.message.answer("Корзина не найдена.")
            return
        items = cart.get("items") or []
        if idx < 0 or idx >= len(items):
            await callback.message.answer("Позиция не найдена.")
            return

       
        new_items: List[Dict[str, Any]] = []
        for i, item in enumerate(items):
            if i == idx:
                continue
            prod = item.get("product") or {}
            prod_id = prod.get("id")
            if prod_id is not None:
                new_items.append({"product": prod_id, "quantity": item.get("quantity", 1)})

        await update_cart_items(cart.get("documentId") or cart.get("id"), new_items)
        await render_cart(callback.message, telegram_id)
        return

    if callback_data.startswith("product:"):
        parts = callback_data.split(":")
        product_numeric_id = parts[1] if len(parts) > 1 else None
        product_doc_id = parts[2] if len(parts) > 2 else parts[1]

        product = await fetch_product_by_id(product_doc_id)
        if not product:
            await callback.message.answer("Товар не найден.")
            return

        title = product.get("title") or "Товар"
        description = product.get("description") or "Нет описания."
        price = product.get("price")
        price_text = f"{price}" if price is not None else "—"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Добавить в корзину", callback_data=f"addcart:{product_numeric_id}"),
                ],
                [InlineKeyboardButton(text="🧺 Моя корзина", callback_data="mycart")],
                [InlineKeyboardButton(text="← Назад к списку", callback_data="back_to_list")],
            ]
        )

        
        image_url = None
        picture = product.get("picture")
        if isinstance(picture, list) and picture:
            first = picture[0] or {}
            image_url = first.get("url")
            if image_url and image_url.startswith("/"):
                image_url = f"{get_strapi_config().url_base}{image_url}"

        caption = f"<b>{title}</b>\nЦена: {price_text}\n\n{description}"

        if image_url:
            file = await download_image(image_url)
            if file:
                await callback.message.answer_photo(
                    photo=file,
                    caption=caption,
                    reply_markup=keyboard,
                )
            else:
                await callback.message.answer(
                    caption,
                    reply_markup=keyboard,
                )
        else:
            await callback.message.answer(
                caption,
                reply_markup=keyboard,
            )
        return

    if callback_data.startswith("addcart:"):
        telegram_id = str(callback.from_user.id)
        product_numeric_id = callback_data.split(":", 1)[1]
        try:
            await upsert_cart_with_item(telegram_id, int(product_numeric_id), quantity=1.0)
            await callback.message.answer("Товар добавлен в корзину.")
        except Exception as exc:
            logging.exception("Не удалось добавить в корзину: %s", exc)
            await callback.message.answer("Не удалось добавить в корзину. Попробуйте позже.")
        return

    await callback.message.answer(f"Вы выбрали: {callback_data}")


async def main() -> None:
    load_dotenv()

    token = os.getenv("BOT_TOKEN")
    redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    set_strapi_config(build_strapi_config_from_env())

    if not token:
        raise RuntimeError("BOT_TOKEN is not set in the environment")

    logging.basicConfig(level=logging.INFO)

    redis_pool = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
    storage = RedisStorage(redis=redis_pool)

    dp = Dispatcher(storage=storage)
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_cancel, Command("cancel"))
    dp.message.register(echo, ShopStates.handle_menu, F.text)
    dp.message.register(echo_email, ShopStates.waiting_email, F.text)
    dp.callback_query.register(
        handle_button,
        F.data.regexp(r"^(product:|back_to_list|addcart:|mycart$|cart_remove:|checkout)"),
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
