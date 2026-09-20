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

# 1. Loggingni to'g'ri sozlash (Xatoliklarni terminalda aniq ko'rsatish uchun)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

# 2. Konfiguratsiyalar
BOT_TOKEN = os.getenv("BOT_TOKEN", "8599909804:AAFOEBP7SX-ynQllqrqjVQ-tDIh6AsWXNDA")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6986848905))
GROUP_ID = os.getenv("GROUP_ID", "-1004434264658")
MINI_APP_URL = "https://fozilovbahodir207-boop.github.io/Stroysentr_market_bot/"

BOT_ADDRESS = "📍 Manzil: Farg'ona viloyati, Yaypan shahri, Stroy Sentr bozori."
CONTACT_CENTER = "📞 Aloqa markazi: +998 97 105 16 56\n👨‍💻 Menedjer: @DataCrafterss"
PAYMENT_CARD = "💳 **Karta raqami:** `4097 8300 8361 0556`\n👤 **Karta egasi:** Sadriddin Abduraxmonov"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# In-memory storage (Real loyihalarda PostgreSQL/SQLite ishlatiladi, hozircha xotira uchun)
PRODUCTS_DB = []
USER_CARTS = {}
ORDERS_DB = {}
ORDER_COUNTER = 100

# FSM holatlari (State Machine)
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

# --- ASOSIY MENYU ---
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

# --- SAVATCHA VA CHECKOUT MEXANIZMI ---
@dp.message(F.text == "🛒 Savatcham")
async def show_cart(message: Message):
    user_id = message.from_user.id
    cart = USER_CARTS.get(user_id, [])
    
    if not cart:
        await message.answer("🛒 Savatchangiz hozircha bo'sh. Katalogdan mahsulot qo'shishingiz mumkin.")
        return
    
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    text = "🛒 **Sizning savatchangiz:**\n\n"
    for idx, item in enumerate(cart, 1):
        text += f"{idx}. {item['title']} - {item.get('quantity', 1)} dona * {item['price']} so'm\n"
    
    text += f"\n💰 **Jami summa:** {total:,.2f} so'm"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="start_checkout")],
        [InlineKeyboardButton(text="🗑 Savatchani tozalash", callback_data="clear_cart")]
    ])
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(F.data == "clear_cart")
async def clear_cart_cb(callback: CallbackQuery):
    USER_CARTS[callback.from_user.id] = []
    await callback.message.edit_text("🗑 Savatchangiz tozalandi.")
    await callback.answer()

@dp.callback_query(F.data == "start_checkout")
async def start_checkout_cb(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not USER_CARTS.get(user_id):
        await callback.answer("Savatchangiz bo'sh!", show_alert=True)
        return
        
    await callback.message.answer("📝 Buyurtmani rasmiylashtirish uchun Iltimos, **Ism va familiyangizni** kiriting:")
    await state.set_state(CheckoutStates.waiting_for_name)
    await callback.answer()

@dp.message(CheckoutStates.waiting_for_name)
async def process_checkout_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📞 Bog'lanish uchun **telefon raqamingizni** kiriting (masalan: +998901234567):")
    await state.set_state(CheckoutStates.waiting_for_phone)

@dp.message(CheckoutStates.waiting_for_phone)
async def process_checkout_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("📍 Yetkazib berish **manzilingizni** (viloyat, tuman, ko'cha, uy raqami) yozing:")
    await state.set_state(CheckoutStates.waiting_for_region)

@dp.message(CheckoutStates.waiting_for_region)
async def process_checkout_region(message: Message, state: FSMContext):
    await state.update_data(region=message.text)
    
    payment_text = (
        "💳 **To'lov qilish uchun ma'lumotlar:**\n\n"
        f"{PAYMENT_CARD}\n\n"
        "Iltimos, to'lovni amalga oshirgach, **to'lov cheki (skrinshot) rasmini** shu yerga yuboring:"
    )
    await message.answer(payment_text, parse_mode="Markdown")
    await state.set_state(CheckoutStates.waiting_for_receipt)

@dp.message(CheckoutStates.waiting_for_receipt, F.photo | F.document)
async def process_checkout_receipt(message: Message, state: FSMContext):
    global ORDER_COUNTER
    ORDER_COUNTER += 1
    order_id = ORDER_COUNTER
    
    user_id = message.from_user.id
    cart = USER_CARTS.get(user_id, [])
    data = await state.get_data()
    
    receipt_photo = message.photo[-1].file_id if message.photo else message.document.file_id
    total_sum = sum(item['price'] * item.get('quantity', 1) for item in cart)
    
    order_info = {
        "order_id": order_id,
        "user_id": user_id,
        "name": data.get("name"),
        "phone": data.get("phone"),
        "region": data.get("region"),
        "items": cart,
        "total": total_sum,
        "receipt": receipt_photo
    }
    ORDERS_DB[order_id] = order_info
    
    # Guruhga yuboriladigan xabar
    group_text = (
        f"🚨 **YANGI BUYURTMA #{order_id}**\n\n"
        f"👤 Mijoz: {data.get('name')}\n"
        f"📞 Telefon: {data.get('phone')}\n"
        f"📍 Manzil: {data.get('region')}\n\n"
        f"🛍 **Mahsulotlar:**\n"
    )
    for itm in cart:
        group_text += f"▪️ {itm['title']} ({itm.get('quantity', 1)} dona) - {itm['price']} so'm\n"
    group_text += f"\n💰 **Jami summa:** {total_sum:,.2f} so'm"
    
    # Xavfsiz guruhga jo'natish bloki
    try:
        await bot.send_photo(
            chat_id=GROUP_ID,
            photo=receipt_photo,
            caption=group_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Guruhga buyurtma yuborishda xatolik yuz berdi: {e}")
    
    # Mijozga tasdiqnoma
    await message.answer(
        f"✅ **Buyurtmangiz muvaffaqiyatli qabul qilindi!**\n\n"
        f"📦 Buyurtma raqami: **#{order_id}**\n"
        f"Tez orada menejerlarimiz siz bilan bog'lanishadi.",
        parse_mode="Markdown"
    )
    
    # Tozalash
    USER_CARTS[user_id] = []
    await state.clear()

@dp.message(CheckoutStates.waiting_for_receipt)
async def invalid_receipt_type(message: Message):
    await message.answer("❌ Iltimos, faqat to'lov cheki **rasmini** yoki hujjatini yuboring!")

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
    await message.answer("🛠 **Admin paneli**ga xush kelibsiz:", reply_markup=admin_markup, parse_mode="Markdown")

@dp.message(F.text == "➕ Mahsulot qo'shish")
async def start_add_product(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📝 Yangi mahsulot **nomini** kiriting:")
    await state.set_state(AddProductStates.title)

@dp.message(AddProductStates.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("💰 Mahsulotning 1 dona **narxini** kiriting (faqat raqam, masalan: 45000):")
    await state.set_state(AddProductStates.price)

@dp.message(AddProductStates.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
        await state.update_data(price=price)
        await message.answer("📦 Omborda nechta borligini **dona** hisobida kiriting (faqat butun son):")
        await state.set_state(AddProductStates.stock)
    except ValueError:
        await message.answer("❌ Noto'g'ri qiymat! Iltimos, musbat raqam kiriting:")

@dp.message(AddProductStates.stock)
async def process_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text)
        if stock < 0:
            raise ValueError
        await state.update_data(stock=stock)
        await message.answer("📄 Mahsulot haqida qisqacha **tavsif** yozing:")
        await state.set_state(AddProductStates.description)
    except ValueError:
        await message.answer("❌ Noto'g'ri qiymat! Faqat butun son kiriting:")

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
    
    # Adminga tasdiq
    await message.answer_photo(
        photo=photo_id, 
        caption=f"✅ **Mahsulot muvaffaqiyatli qo'shildi!**\n\n📦 Nomi: {product['title']}\n💰 Narxi: {product['price']} so'm",
        parse_mode="Markdown"
    )
    
    # Guruhga yangi mahsulot haqida xabar berish
    try:
        await bot.send_photo(
            chat_id=GROUP_ID,
            photo=photo_id,
            caption=f"🚨 **Yangi mahsulot qo'shildi!**\n\n📦 Nomi: {product['title']}\n💰 Narxi: {product['price']} so'm\n📄 {product['description']}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Guruhga mahsulot yuborishda xatolik: {e}")

    await state.clear()
    
    admin_markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="🗑 Mahsulotlarni tozalash")],
            [KeyboardButton(text="📦 Mahsulotlar ro'yxati"), KeyboardButton(text="🔙 Asosiy menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer("Admin panel boshqaruvi:", reply_markup=admin_markup)

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
            caption=f"🆔 Indeks: {i}\n📦 Nomi: {p['title']}\n💰 Narxi: {p['price']} so'm\n📦 Qoldiq: {p['stock']} dona"
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

# --- RENDER WEB SERVER & BOT POLLING (ASYNCHRONOUS ENGINE) ---
async def handle(request):
    return web.Response(text="Stroy Sentr Bot is active and running smoothly!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    # Eski xabarlarni tozalab yuborish (Conflict chiqishining oldini oladi)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Web server va bot pollingni bir vaqtning o'zida ishga tushirish
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
