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
    ReplyKeyboardRemove,
)
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# ==========================================
# ⚙️ SOZLAMALAR VA REKVIZITLAR
# ==========================================
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ"  # BotFather bergan token
ADMIN_IDS = [581234567]  # Telegram ID'ingiz
ORDERS_GROUP_ID = -1001234567890  # Buyurtmalar tushadigan guruh ID'si

# 💳 Do'konning plastic karta ma'lumotlari:
CARD_NUMBER = "8600 0000 0000 0000"
CARD_HOLDER = "FOZILOV BAHODIRJON"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ==========================================
# 1. FSM HOLATLARI
# ==========================================
class AddProductFSM(StatesGroup):
  name = State()
  price = State()
  stock = State()
  photo = State()


class CheckoutFSM(StatesGroup):
  items = State()
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
            items TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
  conn.commit()
  conn.close()


# ==========================================
# 3. RENDER VEB-SERVERI (10000 PORT XATOSI TO'G'RILANGAN)
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
  # Render 10000 portini to'g'ri o'qib olishi uchun:
  port = int(os.environ.get("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()


# ==========================================
# 4. MENYULAR VA TUGMALAR
# ==========================================
async def set_bot_meta_info(bot: Bot):
  commands = [
      BotCommand(command="start", description="Botni qayta ishga tushirish"),
      BotCommand(command="admin", description="Admin Panel"),
  ]
  await bot.set_my_commands(commands)


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


# ==========================================
# 5. USER HANDLERLARI VA TO'LOV TIZIMI
# ==========================================
@dp.message(Command("start"))
async def start_handler(message: types.Message):
  await message.answer(
      f"Assalomu alaykum, {message.from_user.full_name}!\n\n"
      "🏗 <b>STROY SENTR</b> rasmiy botiga xush kelibsiz!\n\n"
      "Kerakli bo'limni tanlang 👇",
      parse_mode="HTML",
      reply_markup=main_menu_keyboard(),
  )


@dp.message(F.text == "💳 To'lov usullari")
async def payment_info(message: types.Message):
  text = (
      "💳 <b>STROY SENTR To'lov tizimlari:</b>\n\n"
      f"📌 <b>Karta raqami:</b> <code>{CARD_NUMBER}</code>\n"
      f"👤 <b>Egani:</b> {CARD_HOLDER}\n\n"
      "Bizda quyidagi to'lov usullari mavjud:\n"
      "1. 📱 <b>Click / Payme</b> (Karta raqamiga o'tkazma)\n"
      "2. 💳 <b>Uzcard / Humo</b> karta o'tkazmasi\n"
      "3. 💵 <b>Naqd pul</b> (Mahsulotni yetkazib berilganda)"
  )
  await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🛍 Mahsulotlar katalogi")
async def show_catalog(message: types.Message):
  conn = sqlite3.connect("stroy_sentr.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, price, stock, photo_id FROM products")
  products = cursor.fetchall()
  conn.close()

  if not products:
    await message.answer(
        "📦 Hozircha omborda mahsulotlar mavjud emas. Tez orada qo'shiladi!"
    )
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


# --- BUYURTMA BERISH VA TO'LOV QISMI ---
@dp.message(F.text == "📦 Zakaz berish")
async def start_checkout(message: types.Message, state: FSMContext):
  await state.set_state(CheckoutFSM.items)
  await message.answer(
      "🛒 <b>Qaysi mahsulotlardan qancha kerakligini yozing:</b>\n"
      "<i>(Masalan: 10 dona Gipsokarton, 2 qop Sement)</i>",
      parse_mode="HTML",
      reply_markup=ReplyKeyboardRemove(),
  )


@dp.message(CheckoutFSM.items)
async def process_checkout_items(message: types.Message, state: FSMContext):
  await state.update_data(items=message.text)
  await state.set_state(CheckoutFSM.phone)

  phone_btn = ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
      ],
      resize_keyboard=True,
  )
  await message.answer(
      "📞 **Telefon raqamingizni yuboring:**",
      parse_mode="Markdown",
      reply_markup=phone_btn,
  )


@dp.message(CheckoutFSM.phone)
async def process_checkout_phone(message: types.Message, state: FSMContext):
  phone = (
      message.contact.phone_number if message.contact else message.text
  )
  await state.update_data(phone=phone)
  await state.set_state(CheckoutFSM.payment_method)

  pay_kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📱 Click / Payme / Karta", callback_data="pay_card"
              )
          ],
          [
              InlineKeyboardButton(
                  text="💵 Naqd pul (Qabul qilganda)", callback_data="pay_cash"
              )
          ],
      ]
  )
  await message.answer(
      "💳 <b>To'lov usulini tanlang:</b>", parse_mode="HTML", reply_markup=pay_kb
  )


@dp.callback_query(CheckoutFSM.payment_method, F.data == "pay_card")
async def pay_card_selected(callback: types.CallbackQuery, state: FSMContext):
  await state.update_data(payment_method="Karta / Click / Payme")
  await state.set_state(CheckoutFSM.receipt)

  text = (
      f"💳 <b>To'lov uchun karta raqamimiz:</b>\n\n"
      f"📌 <code>{CARD_NUMBER}</code>\n"
      f"👤 <b>Egani:</b> {CARD_HOLDER}\n\n"
      "To'lovni amalga oshirgach, **chek rasmini** (yoki skrinshotini) shu yerga yuboring 👇"
  )
  await callback.message.answer(text, parse_mode="HTML")
  await callback.answer()


@dp.callback_query(CheckoutFSM.payment_method, F.data == "pay_cash")
async def pay_cash_selected(callback: types.CallbackQuery, state: FSMContext):
  data = await state.get_data()
  user_name = callback.from_user.full_name

  text = (
      f"🚨 <b>YANGI BUYURTMA (Naqd pul)</b>\n"
      f"━━━━━━━━━━━━━━━━━━\n"
      f"👤 <b>Mijoz:</b> {user_name}\n"
      f"📞 <b>Tel:</b> {data['phone']}\n"
      f"🛒 <b>Buyurtma:</b>\n{data['items']}\n"
      f"💳 <b>To'lov turi:</b> Naqd pul"
  )

  await bot.send_message(chat_id=ORDERS_GROUP_ID, text=text, parse_mode="HTML")
  await callback.message.answer(
      "✅ Buyurtmangiz qabul qilindi! Tez orada operatorlarimiz bog'lanishadi.",
      reply_markup=main_menu_keyboard(),
  )
  await state.clear()
  await callback.answer()


@dp.message(CheckoutFSM.receipt, F.photo)
async def process_receipt(message: types.Message, state: FSMContext):
  data = await state.get_data()
  user_name = message.from_user.full_name
  photo_id = message.photo[-1].file_id

  text = (
      f"🚨 <b>YANGI BUYURTMA (Karta / Click)</b>\n"
      f"━━━━━━━━━━━━━━━━━━\n"
      f"👤 <b>Mijoz:</b> {user_name}\n"
      f"📞 <b>Tel:</b> {data['phone']}\n"
      f"🛒 <b>Buyurtma:</b>\n{data['items']}\n"
      f"💳 <b>To'lov turi:</b> Karta (Chek rasmi biriktirilgan)"
  )

  await bot.send_photo(
      chat_id=ORDERS_GROUP_ID, photo=photo_id, caption=text, parse_mode="HTML"
  )
  await message.answer(
      "✅ Chek va buyurtmangiz qabul qilindi! Tez orada operatorlarimiz bog'lanishadi.",
      reply_markup=main_menu_keyboard(),
  )
  await state.clear()


@dp.message(F.text == "📞 Biz bilan aloqa")
async def contact_handler(message: types.Message):
  await message.answer(
      "📞 <b>STROY SENTR Aloqa markazi:</b>\n\n"
      "📱 Telefon: +998 90 XXX XX XX\n"
      "💬 Admin: @stroy_sentr_admin\n"
      "⏰ Ish vaqti: 08:00 - 19:00",
      parse_mode="HTML",
  )


@dp.message(F.text == "📍 Do'konimiz manzili")
async def location_handler(message: types.Message):
  await message.answer(
      "📍 <b>Do'konimiz manzili:</b>\n\nYaypan shahri, STROY SENTR qurilish"
      " do'koni.",
      parse_mode="HTML",
  )


# ==========================================
# 6. ADMIN PANEL
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
