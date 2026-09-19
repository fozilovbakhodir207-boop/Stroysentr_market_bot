import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, 
    InputMediaPhoto, WebAppInfo
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# Sozlamalar
BOT_TOKEN = os.getenv("BOT_TOKEN", "8599909804:AAGrZoiDTW-dxkoOgyKCBGNBR841TAcchp4")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6986848905))
GROUP_ID = os.getenv("GROUP_ID", "-1004434264658")
MINI_APP_URL = "https://fozilovbakhodir207-boop.github.io/Stroysentr_market_bot/"

BOT_ADDRESS = "📍 Manzil: Farg'ona viloyati, Yaypan shahri, Stroy Sentr dokoni."
CONTACT_CENTER = "📞 Aloqa markazi: +998 97 105 16 56\n👨‍💻 Menedjer: @DataCrafterss"
PAYMENT_CARD = "💳 **Karta raqami:** `4097 8300 8361 0556`\n👤 **Karta egasi:** Sadriddin Abduraxmonov"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

PRODUCTS_DB = []
ORDERS_DB = {}
ORDER_COUNTER = 100

class AddProduct(StatesGroup):
    title = State()
    price = State()
    stock = State()
    description = State()
    photo = State()

class CheckoutState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_region = State()
    waiting_for_receipt = State()

USER_CARTS = {}

@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    buttons = [
        [KeyboardButton(text="🛍️ Katalog (Mini App)", web_app=WebAppInfo(url=MINI_APP_URL))],
        [KeyboardButton(text="🛒 Savatcham"), KeyboardButton(text="📦 Mening buyurtmalarim")],
        [KeyboardButton(text="📍 Do'kon manzili"), KeyboardButton(text="📞 Aloqa markazi")]
    ]
    
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin panel")])

    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer(
        "Assalomu alaykum! **STROY SENTR** online do'koniga xush kelibsiz 🏗\n\nKerakli bo'limni tanlang:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.message(F.text == "📍 Do'kon manzili")
async def show_address(message: Message):
    await message.answer(f"{BOT_ADDRESS}\n\nSizni do'konimizda kutib qolamiz!")

@dp.message(F.text == "📞 Aloqa markazi")
async def show_contacts(message: Message):
    await message.answer(f"🛠 **STROY SENTR Yordam xizmati**\n\n{CONTACT_CENTER}", parse_mode="Markdown")

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
@dp.message(F.text == "⚙️ Admin panel")
async def admin_cmd(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Sizda bu bo'limga kirish huquqi yo'q!")
        return

    await state.clear()
    admin_markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="🗑 Mahsulotlarni tozalash")],
            [KeyboardButton(text="📦 Mahsulotlar ro'yxati"), KeyboardButton(text="🔙 Asosiy menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer("🛠 **Admin paneli**", reply_markup=admin_markup, parse_mode="Markdown")

@dp.message(F.text == "➕ Mahsulot qo'shish")
async def start_add_product(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📝 Yangi mahsulot **nomini** kiriting:")
    await state.set_state(AddProduct.title)

@dp.message(AddProduct.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("💰 Mahsulotning 1 dona **narxini** kiriting (faqat raqam):")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("📦 Omborda nechta borligini **dona** ҳisobida kiriting:")
        await state.set_state(AddProduct.stock)
    except ValueError:
        await message.answer("❌ Xato! Faqat raqam kiriting:")

@dp.message(AddProduct.stock)
async def process_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text)
        await state.update_data(stock=stock)
        await message.answer("📄 Mahsulot haqida qisqacha **tavsif** yozing:")
        await state.set_state(AddProduct.description)
    except ValueError:
        await message.answer("❌ Xato! Faqat butun son kiriting:")

@dp.message(AddProduct.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("📸 Endi mahsulot **rasmini** yuboring:")
    await state.set_state(AddProduct.photo)

@dp.message(AddProduct.photo, F.photo | F.document)
async def process_photo(message: Message, state: FSMContext):
   file = await message.bot.get_file(photo_id)
file_path = file.file_path
photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    
product = {
    "title": data.get("title"),
    "price": data.get("price"),
    "stock": data.get("stock"),
    "description": data.get("description"),
    "image_url": photo_url
}
    
    PRODUCTS_DB.append(product)
    
    await message.answer_photo(
        photo=photo_id, 
        caption=f"✅ **Mahsulot muvaffaqiyatli qo'shildi!**\n\n📦 Nomi: {product['title']}\n💰 Narxi: {product['price']} so'm",
        parse_mode="Markdown"
    )
    await state.clear()
    
    admin_markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="🗑 Mahsulotlarni tozalash")],
            [KeyboardButton(text="📦 Mahsulotlar ro'yxati"), KeyboardButton(text="🔙 Asosiy menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer("Admin panelga xush kelibsiz:", reply_markup=admin_markup)

@dp.message(F.text == "📦 Mahsulotlar ro'yxati")
async def list_products(message: Message):
    if message.from_user.id != ADMIN_ID: return
    if not PRODUCTS_DB:
        await message.answer("📭 Hozircha mahsulotlar yo'q.")
        return
    for i, p in enumerate(PRODUCTS_DB):
        await message.answer_photo(photo=p['photo'], caption=f"🆔 Indeks: {i}\n📦 Nomi: {p['title']}\n💰 Narxi: {p['price']} so'm")

@dp.message(F.text == "🗑 Mahsulotlarni tozalash")
async def clear_products(message: Message):
    if message.from_user.id != ADMIN_ID: return
    PRODUCTS_DB.clear()
    await message.answer("🗑 Barcha mahsulotlar tozalandi!")

@dp.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await start_cmd(message, state)

# --- WEB SERVER (Render port talabini qondirish uchun) ---
async def handle(request):
    return web.Response(text="Stroy Sentr Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    # Veb-hooklarni tozalash (xatolik bermasligi uchun)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Veb-server va botni birgalikda ishga tushirish
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
