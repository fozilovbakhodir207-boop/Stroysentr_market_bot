import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# ==========================================
# ⚙️ SOZLAMALAR VA TO'LOV KARTASI
# ==========================================
BOT_TOKEN = "8599909804:AAGrZoiDTW-dxkoOgyKCbGNBR841TAcchp4"  # BotFather tokeni
ADMIN_IDS = [6986848905]  # Telegram ID'ingiz
ORDERS_GROUP_ID = -1004434264658 # Guruh ID'si

# 💳 Do'konning plastic karta ma'lumotlari:
CARD_NUMBER = "4097 8300 8361 0556"
CARD_HOLDER = "Sadriddin Abduraxmonov"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ==========================================
# 1. FSM HOLATLARI (TOVAR QO'SHISH VA TO'LOV)
# ==========================================
class AddProductFSM(StatesGroup):
  name = State()
  price = State()
  stock = State()
  photo = State()


class CheckoutFSM(StatesGroup):
  phone = State()
  payment_method = State()
  receipt = State()


# ==========================================
# 2. DATABASE
# ==========================================
def init_db():
  conn = sqlite3.connect("stroy_sentr.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            photo_id TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            phone TEXT,
            payment_method TEXT,
            total_amount REAL,
            status TEXT DEFAULT 'pending'
        )
    """)
  conn.commit()
  conn.close()


# ==========================================
# 3. RENDER SERVER
# ==========================================
async def handle_ping(request):
  return web.Response(
      text="STROY SENTR Bot 24/7 rejimda ishlamoqda!", status=200
  )


async def start_web_server():
  app = web.Application()
  app.router.add_get("/", handle_ping)
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.environ.get("PORT", 8080))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()


# ==========================================
# 4. MENYULAR
# ==========================================
def main_menu_keyboard():
  kb = [
      [
          KeyboardButton(text="🛍 Mahsulotlar katalogi"),
          KeyboardButton(text="📦 Zakaz berish"),
      ],
      [
          KeyboardButton(text="💳 To'lov usullari"),
          KeyboardButton(text="🚚 Yetkazib berish"),
      ],
      [
          KeyboardButton(text="📞 Biz bilan aloqa"),
          KeyboardButton(text="📍 Do'konimiz manzili"),
      ],
  ]
  return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def payment_methods_keyboard():
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🔹 Click orqali to'lov", callback_data="pay_click"
              )
          ],
          [
              InlineKeyboardButton(
                  text="🔹 Payme orqali to'lov", callback_data="pay_payme"
              )
          ],
          [
              InlineKeyboardButton(
                  text="💳 Karta raqamiga o'tkazish (Chek yuborish)",
                  callback_data="pay_card",
              )
          ],
          [
              InlineKeyboardButton(
                  text="💵 Naqd pul (Qabul qilganda)", callback_data="pay_cash"
              )
          ],
      ]
  )
  return kb


# ==========================================
# 5. USER HANDLERLARI
# ==========================================
@dp.message(Command("start"))
async def start_handler(message: types.Message):
  welcome_text = (
      f"Assalomu alaykum, {message.from_user.full_name}!\n\n"
      "🏗 <b>STROY SENTR</b> rasmiy botiga xush kelibsiz!\n\n"
      "Kerakli bo'limni tanlang 👇"
  )
  await message.answer(
      welcome_text, parse_mode="HTML", reply_markup=main_menu_keyboard()
  )


@dp.message(F.text == "💳 To'lov usullari")
async def payment_info(message: types.Message):
  text = (
      "💳 <b>STROY SENTR To'lov tizimlari:</b>\n\n"
      "Bizda quyidagi to'lov turlari mavjud:\n"
      "1. 📱 <b>Click / Payme</b> ilovalari orqali\n"
      "2. 💳 <b>Karta raqamiga o'tkazma</b> (Uzcard/Humo)\n"
      "3. 💵 <b>Naqd pul</b> (Mahsulot yetib borgach)\n\n"
      "👇 Buyurtma berishda mos to'lov usulini tanlaysiz."
  )
  await message.answer(
      text, parse_mode="HTML", reply_markup=payment_methods_keyboard()
  )


@dp.callback_query(F.data == "pay_card")
async def card_payment_info(callback: types.CallbackQuery):
  text = (
      f"💳 <b>Karta orqali to'lov rekvizitlari:</b>\n\n"
      f"📌 <b>Karta:</b> <code>{CARD_NUMBER}</code>\n"
      f"👤 <b>Egani:</b> {CARD_HOLDER}\n\n"
      f"To'lovni amalga oshirgach, chek rasmini botga yuborishingiz kerak bo'ladi."
  )
  await callback.message.answer(text, parse_mode="HTML")
  await callback.answer()


@dp.callback_query(F.data == "pay_click")
async def click_payment_info(callback: types.CallbackQuery):
  await callback.message.answer(
      "📱 Click orqali to'lash uchun ilovadan <b>'O'tkazma'</b> bo'limiga kirib, "
      f"<code>{CARD_NUMBER}</code> kartasiga to'lovni bajaring va chekni yuboring.",
      parse_mode="HTML",
  )
  await callback.answer()


@dp.message(F.text == "🛍 Mahsulotlar katalogi")
async def show_catalog(message: types.Message):
  conn = sqlite3.connect("stroy_sentr.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, price, stock, photo_id FROM products")
  products = cursor.fetchall()
  conn.close()

  if not products:
    await message.answer("📦 Hozircha omborda mahsulotlar mavjud emas.")
    return

  for item in products:
    p_id, name, price, stock, photo_id = item
    caption = (
        f"🏷 <b>{name}</b>\n"
        f"💰 Narxi: {price:,.0f} so'm\n"
        f"📦 Qoldiq: {stock} ta/metr"
    )
    if photo_id:
      await message.answer_photo(
          photo=photo_id, caption=caption, parse_mode="HTML"
      )
    else:
      await message.answer(caption, parse_mode="HTML")


@dp.message(F.text == "📞 Biz bilan aloqa")
async def contact_handler(message: types.Message):
  await message.answer(
      "📞 <b>STROY SENTR Aloqa markazi:</b>\n\n"
      "📱 Telefon: +998 97 105 16 56\n"
      "💬 Admin: @\DataCrafterss\n"
      "⏰ Ish vaqti: 08:00 - 19:00",
      parse_mode="HTML",
  )


@dp.message(F.text == "📍 Do'konimiz manzili")
async def location_handler(message: types.Message):
  await message.answer(
      "📍 <b>Do'konimiz manzili:</b>\n\nYaypan shahri, STROY SENTR "
      " 1-maktab yonida.",
      parse_mode="HTML",
  )


# ==========================================
# 6. ADMIN PANEL & OMBOR
# ==========================================
@dp.message(Command("admin"), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: types.Message):
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="➕ Yangi tovar qo'shish", callback_data="add_product"
              )
          ],
          [
              InlineKeyboardButton(
                  text="📦 Ombor va Qoldiqni ko'rish",
                  callback_data="admin_stock",
              )
          ],
      ]
  )
  await message.answer(
      "🏗 <b>STROY SENTR Admin Paneli</b>\n\nBoshqaruv bo'limini tanlang:",
      reply_markup=kb,
      parse_mode="HTML",
  )


@dp.callback_query(F.data == "add_product", F.from_user.id.in_(ADMIN_IDS))
async def add_product_start(
    callback: types.CallbackQuery, state: FSMContext
):
  await state.set_state(AddProductFSM.name)
  await callback.message.answer(
      "📝 <b>Yangi tovar nomini kiriting:</b>", parse_mode="HTML"
  )
  await callback.answer()


@dp.message(AddProductFSM.name)
async def process_name(message: types.Message, state: FSMContext):
  await state.update_data(name=message.text)
  await state.set_state(AddProductFSM.price)
  await message.answer(
      "💰 <b>Tovar narxini kiriting (so'mda):</b>", parse_mode="HTML"
  )


@dp.message(AddProductFSM.price)
async def process_price(message: types.Message, state: FSMContext):
  try:
    price = float(message.text)
    await state.update_data(price=price)
    await state.set_state(AddProductFSM.stock)
    await message.answer("📦 <b>Ombordagi miqdorini kiriting:</b>", parse_mode="HTML")
  except ValueError:
    await message.answer("❌ Narxni raqamlarda kiriting!")


@dp.message(AddProductFSM.stock)
async def process_stock(message: types.Message, state: FSMContext):
  try:
    stock = int(message.text)
    await state.update_data(stock=stock)
    await state.set_state(AddProductFSM.photo)
    await message.answer(
        "🖼 <b>Tovar rasmini yuboring (yoki 'yoq' deb yozing):</b>",
        parse_mode="HTML",
    )
  except ValueError:
    await message.answer("❌ Miqdorni butun raqamda kiriting!")


@dp.message(AddProductFSM.photo)
async def process_photo(message: types.Message, state: FSMContext):
  data = await state.get_data()
  photo_id = message.photo[-1].file_id if message.photo else None

  conn = sqlite3.connect("stroy_sentr.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO products (name, price, stock, photo_id) VALUES (?, ?, ?, ?)",
      (data["name"], data["price"], data["stock"], photo_id),
  )
  conn.commit()
  conn.close()

  await message.answer(
      f"✅ <b>{data['name']}</b> omborga muvaffaqiyatli qo'shildi!",
      parse_mode="HTML",
  )
  await state.clear()


@dp.callback_query(F.data == "admin_stock", F.from_user.id.in_(ADMIN_IDS))
async def view_stock(callback: types.CallbackQuery):
  conn = sqlite3.connect("stroy_sentr.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, price, stock FROM products")
  products = cursor.fetchall()
  conn.close()

  if not products:
    await callback.message.answer("📦 Ombor bo'sh!")
    await callback.answer()
    return

  text = "📦 <b>OMBOR QOLDIQLARI:</b>\n\n"
  for item in products:
    text += f"🔹 ID:{item[0]} | <b>{item[1]}</b>\n └ Narx: {item[2]:,.0f} so'm | Qoldiq: {item[3]} ta\n"

  await callback.message.answer(text, parse_mode="HTML")
  await callback.answer()


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_order(callback: types.CallbackQuery):
  await callback.message.edit_caption(
      caption=f"{callback.message.caption}\n\n✅ <b>BUYURTMA TASDIQLANDI!</b>",
      parse_mode="HTML",
  )
  await callback.answer("Buyurtma tasdiqlandi!")


@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(callback: types.CallbackQuery):
  await callback.message.edit_caption(
      caption=f"{callback.message.caption}\n\n❌ <b>BUYURTMA BEKOR QILINDI!</b>",
      parse_mode="HTML",
  )
  await callback.answer("Buyurtma bekor qilindi!")


# ==========================================
# 7. ISHGA TUSHIRISH
# ==========================================
async def main():
  init_db()
  await set_bot_meta_info(bot)
  await start_web_server()
  await bot.delete_webhook(drop_pending_updates=True)
  print("STROY SENTR Boti 24/7 rejimida ishga tushdi!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  try:
    asyncio.run(main())
  except (KeyboardInterrupt, SystemExit):
    pass
