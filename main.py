import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, 
    WebAppInfo
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# 1. Logging sozlamasi
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

# 2. Tokenlar va sozlamalar
BOT_TOKEN = os.getenv("BOT_TOKEN", "8599909804:AAFOEBP7SX-ynQllqrqjVQ-tDIh6AsWXNDA")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6986848905))
GROUP_ID = os.getenv("GROUP_ID", "-1004434264658")

# RENDER_URL - Render'dagi ilovangizning asosiy manzili (oxirida / belgisi bo'lmasin)
RENDER_URL = os.getenv("RENDER_URL", "https://stroy-sentr-market-bot.onrender.com")

BOT_ADDRESS = "📍 Manzil: Farg'ona viloyati, Yaypan shahri, Stroy Sentr dokoni."
CONTACT_CENTER = "📞 Aloqa markazi: +998 97 1.5 16 56\n👨‍💻 Menedjer: @Fozilov_Bahodir"
PAYMENT_CARD = "💳 **Karta raqami:** `4097 8300 8361 0556`\n👤 **Karta egasi:** Sadriddin Abduraxmonov"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Vaqtinchalik ma'lumotlar bazasi (Xotirada ishlaydi)
PRODUCTS_DB = []
USER_CARTS = {}
ORDERS_DB = {}
ORDER_COUNTER = 100

class AddProductStates(StatesGroup):
    title = State()
    price = State()
    stock = State()
    description = State()
    photo = State()

class CheckoutStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_region = State()
    waiting_for_receipt = State()

# --- BOT BUYRUQLARI VA MENYU ---
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    # Mini App to'g'ridan-to'g'ri Render serveriga ulanadi (404 chiqmaydi)
    mini_app_url = f"{RENDER_URL}/"

    buttons = [
        [KeyboardButton(text="🛍️ Katalog (Mini App)", web_app=WebAppInfo(url=mini_app_url))],
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

# --- ADMIN PANEL: MAHSULOT QO'SHISH ---
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
    await message.answer("🛠 **Admin paneli**ga xush kelibsiz:", reply_markup=admin_markup, parse_mode="Markdown")

@dp.message(F.text == "➕ Mahsulot qo'shish")
async def start_add_product(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📝 Yangi mahsulot **nomini** kiriting:")
    await state.set_state(AddProductStates.title)

@dp.message(AddProductStates.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("💰 Mahsulot narxini kiriting (faqat raqam, masalan: 45000):")
    await state.set_state(AddProductStates.price)

@dp.message(AddProductStates.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0: raise ValueError
        await state.update_data(price=price)
        await message.answer("📦 Omborda nechta borligini (dona) kiriting:")
        await state.set_state(AddProductStates.stock)
    except ValueError:
        await message.answer("❌ Noto'g'ri qiymat! Musbat raqam kiriting:")

@dp.message(AddProductStates.stock)
async def process_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text)
        if stock < 0: raise ValueError
        await state.update_data(stock=stock)
        await message.answer("📄 Mahsulot haqida qisqacha tavsif yozing:")
        await state.set_state(AddProductStates.description)
    except ValueError:
        await message.answer("❌ Noto'g'ri qiymat! Butun son kiriting:")

@dp.message(AddProductStates.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("📸 Endi mahsulot **rasmini** yuboring:")
    await state.set_state(AddProductStates.photo)

@dp.message(AddProductStates.photo, F.photo | F.document)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id if message.photo else message.document.file_id
    data = await state.get_data()
    
    product = {
        "title": data.get("title"),
        "price": data.get("price"),
        "stock": data.get("stock"),
        "description": data.get("description"),
        "photo": photo_id
    }
    PRODUCTS_DB.append(product)
    
    await message.answer(f"✅ **Mahsulot muvaffaqiyatli qo'shildi va Mini App bazasiga joylandi!**", parse_mode="Markdown")
    await state.clear()
    
    admin_markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="🗑 Mahsulotlarni tozalash")],
            [KeyboardButton(text="📦 Mahsulotlar ro'yxati"), KeyboardButton(text="🔙 Asosiy menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer("Boshqaruv menyusi:", reply_markup=admin_markup)

@dp.message(AddProductStates.photo)
async def invalid_product_photo(message: Message):
    await message.answer("❌ Iltimos, mahsulot uchun rasm yuboring!")

@dp.message(F.text == "📦 Mahsulotlar ro'yxati")
async def list_products(message: Message):
    if message.from_user.id != ADMIN_ID: return
    if not PRODUCTS_DB:
        await message.answer("📭 Hozircha bazada mahsulotlar yo'q.")
        return
    for i, p in enumerate(PRODUCTS_DB):
        await message.answer_photo(
            photo=p['photo'], 
            caption=f"🆔 ID: {i}\n📦 Nomi: {p['title']}\n💰 Narxi: {p['price']} so'm\n📦 Qoldiq: {p['stock']} dona"
        )

@dp.message(F.text == "🗑 Mahsulotlarni tozalash")
async def clear_products(message: Message):
    if message.from_user.id != ADMIN_ID: return
    PRODUCTS_DB.clear()
    await message.answer("🗑 Barcha mahsulotlar bazadan tozalandi!")

@dp.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await start_cmd(message, state)

# --- WEB SERVER & API ENDPOINTS (MINI APP UCHUN) ---
async def handle_index(request):
    # index.html faylini to'g'ridan-to'g'ri brauzerga uzatadi (404 xatosini oldini oladi)
    try:
        return web.FileResponse('./index.html')
    except Exception as e:
        return web.Response(text=f"Xatolik: index.html topilmadi! Tafsilot: {e}", content_type="text/plain")

async def handle_api_products(request):
    # Mini App shu API orqali botga qo'shilgan mahsulotlarni oladi
    return web.json_response(PRODUCTS_DB)

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/products", handle_api_products)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
