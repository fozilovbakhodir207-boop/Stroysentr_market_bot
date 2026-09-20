import os
import logging
import asyncio
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types.input_file import BufferedInputFile

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN", "8599909804:AAFOEBP7SX-ynQllqrqjVQ-tDIh6AsWXNDA")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6986848905))
GROUP_ID = os.getenv("GROUP_ID", "-1004434264658")
RENDER_URL = os.getenv("RENDER_URL", "https://stroysentr-market-bot.onrender.com")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Ma'lumotlar bazasi va do'kon sozlamalari
PRODUCTS_DB = []
ORDER_COUNTER = 100
SHOP_SETTINGS = {
    "card_number": "4097 8300 8361 0556"
}

class AddProductStates(StatesGroup):
    title = State()
    price = State()
    stock = State()
    description = State()
    photo = State()

class EditStockStates(StatesGroup):
    select_product = State()
    new_stock = State()

class EditCardStates(StatesGroup):
    new_card = State()

@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    mini_app_url = f"{RENDER_URL}/"
    buttons = [
        [KeyboardButton(text="🛍️ Katalog (Mini App)", web_app=WebAppInfo(url=mini_app_url))],
        [KeyboardButton(text="📍 Do'kon manzili"), KeyboardButton(text="📞 Aloqa markazi")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin panel")])

    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Assalomu alaykum! **STROY SENTR** qurilish mollari dokoniga xush kelibsiz 🏗", reply_markup=markup, parse_mode="Markdown")

@dp.message(F.text == "📍 Do'kon manzili")
async def show_address(message: Message):
    await message.answer("📍 Manzil: Farg'ona viloyati, Yaypan shahri, Stroy Sentr dokoni.")

@dp.message(F.text == "📞 Aloqa markazi")
async def show_contacts(message: Message):
    await message.answer("📞 Aloqa markazi: +998 97 105 16 56\n👨‍💻 Menedjer: @Fozilov_Bahodirjon")

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
@dp.message(F.text == "⚙️ Admin panel")
async def admin_cmd(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    admin_markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="🔄 Qoldiqni o'zgartirish")],
            [KeyboardButton(text="💳 Karta raqamini o'zgartirish"), KeyboardButton(text="📦 Mahsulotlar ro'yxati")],
            [KeyboardButton(text="🔙 Asosiy menyu")]
        ],
        resize_keyboard=True
    )
    await message.answer(f"🛠 **Admin paneli**:\nJoriy to'lov karta: `{SHOP_SETTINGS['card_number']}`", reply_markup=admin_markup, parse_mode="Markdown")

@dp.message(F.text == "💳 Karta raqamini o'zgartirish")
async def edit_card_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(f"Joriy karta raqami: `{SHOP_SETTINGS['card_number']}`\n\nYangi karta raqami va egasining F.I.O. ni kiriting:", parse_mode="Markdown")
    await state.set_state(EditCardStates.new_card)

@dp.message(EditCardStates.new_card)
async def edit_card_finish(message: Message, state: FSMContext):
    new_card = message.text.strip()
    SHOP_SETTINGS["card_number"] = new_card
    await message.answer(f"✅ Karta raqami muvaffaqiyatli yangilandi:\n`{new_card}`", parse_mode="Markdown")
    await state.clear()

@dp.message(F.text == "➕ Mahsulot qo'shish")
async def start_add_product(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📝 Mahsulot nomini kiriting:")
    await state.set_state(AddProductStates.title)

@dp.message(AddProductStates.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("💰 Narxini kiriting (so'mda):")
    await state.set_state(AddProductStates.price)

@dp.message(AddProductStates.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("📦 Ombordagi sonini (dona) kiriting:")
        await state.set_state(AddProductStates.stock)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting:")

@dp.message(AddProductStates.stock)
async def process_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text)
        await state.update_data(stock=stock)
        await message.answer("📄 Tavsif yozing:")
        await state.set_state(AddProductStates.description)
    except ValueError:
        await message.answer("❌ Faqat butun son kiriting:")

@dp.message(AddProductStates.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("📸 Mahsulot rasmini yuboring:")
    await state.set_state(AddProductStates.photo)

@dp.message(AddProductStates.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    file = await bot.get_file(photo_file_id)
    photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    
    data = await state.get_data()
    product = {
        "title": data.get("title"),
        "price": data.get("price"),
        "stock": data.get("stock"),
        "description": data.get("description"),
        "photo_id": photo_file_id,
        "image_url": photo_url
    }
    PRODUCTS_DB.append(product)
    await message.answer("✅ Mahsulot muvaffaqiyatli qo'shildi!")
    await state.clear()

@dp.message(F.text == "📦 Mahsulotlar ro'yxati")
async def list_products(message: Message):
    if message.from_user.id != ADMIN_ID: return
    if not PRODUCTS_DB:
        await message.answer("📭 Hozircha mahsulotlar yo'q.")
        return
    for idx, p in enumerate(PRODUCTS_DB):
        await message.answer_photo(p['photo_id'], caption=f"🆔 ID: {idx}\n📦 {p['title']}\n💰 {p['price']} so'm\n📦 Omborda: {p['stock']} dona")

@dp.message(F.text == "🔄 Qoldiqni o'zgartirish")
async def edit_stock_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    if not PRODUCTS_DB:
        await message.answer("📭 Mahsulotlar mavjud emas.")
        return
    text = "Qaysi mahsulot qoldig'ini o'zgartirmoqchisiz? ID raqamini yuboring:\n\n"
    for idx, p in enumerate(PRODUCTS_DB):
        text += f"{idx}: {p['title']} (Omborda: {p['stock']} dona)\n"
    await message.answer(text)
    await state.set_state(EditStockStates.select_product)

@dp.message(EditStockStates.select_product)
async def edit_stock_select(message: Message, state: FSMContext):
    try:
        idx = int(message.text)
        if idx < 0 or idx >= len(PRODUCTS_DB): raise ValueError
        await state.update_data(product_idx=idx)
        await message.answer(f"📦 '{PRODUCTS_DB[idx]['title']}' uchun yangi qoldiq miqdorini kiriting:")
        await state.set_state(EditStockStates.new_stock)
    except ValueError:
        await message.answer("❌ Noto'g'ri ID:")

@dp.message(EditStockStates.new_stock)
async def edit_stock_finish(message: Message, state: FSMContext):
    try:
        new_stock = int(message.text)
        data = await state.get_data()
        idx = data.get("product_idx")
        PRODUCTS_DB[idx]['stock'] = new_stock
        await message.answer(f"✅ Muvaffaqiyatli! Qoldiq {new_stock} taga o'zgartirildi.")
        await state.clear()
    except ValueError:
        await message.answer("❌ Faqat butun son kiriting:")

@dp.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await start_cmd(message, state)

@dp.callback_query(F.data.startswith("complete_order_"))
async def complete_order_callback(callback: CallbackQuery):
    order_id = callback.data.split("_")[2]
    new_text = callback.message.caption + f"\n\n✅ **STATUS: Yig'ildi va yuborildi!** (Mas'ul: @{callback.from_user.username or callback.from_user.first_name})"
    await callback.message.edit_caption(caption=new_text, parse_mode="Markdown", reply_markup=None)
    await callback.answer("Buyurtma bajarildi deb belgilandi!")

# --- WEB SERVER & API ---
async def handle_index(request):
    try:
        return web.FileResponse('./index.html')
    except Exception as e:
        return web.Response(text=f"Xatolik: {e}", content_type="text/plain")

async def handle_api_data(request):
    return web.json_response({
        "products": PRODUCTS_DB,
        "card_number": SHOP_SETTINGS["card_number"]
    })

async def handle_api_order(request):
    global ORDER_COUNTER
    try:
        reader = await request.multipart()
        
        name = ""
        phone = ""
        address = ""
        items_raw = "{}"
        receipt_bytes = None
        
        async for field in reader:
            if field.name == 'name':
                name = await field.text()
            elif field.name == 'phone':
                phone = await field.text()
            elif field.name == 'address':
                address = await field.text()
            elif field.name == 'items':
                items_raw = await field.text()
            elif field.name == 'receipt':
                receipt_bytes = await field.read()

        if not receipt_bytes:
            return web.json_response({"success": False, "error": "To'lov cheki majburiy!"}, status=400)

        ORDER_COUNTER += 1
        order_id = ORDER_COUNTER
        items = json.loads(items_raw)
        
        total_sum = 0
        order_details_text = f"🚨 **CHEK RAQAMI #{order_id} (TO'LOV QILINGAN)**\n\n"
        order_details_text += f"👤 Mijoz: {name}\n📞 Telefon: {phone}\n📍 Manzil: {address}\n\n🛍 **Mahsulotlar:**\n"
        
        for key, item in items.items():
            idx = int(item.get("originalIndex", 0))
            qty = int(item.get("quantity", 1))
            
            if idx < len(PRODUCTS_DB):
                PRODUCTS_DB[idx]["stock"] = max(0, PRODUCTS_DB[idx]["stock"] - qty)
                subtotal = PRODUCTS_DB[idx]["price"] * qty
                total_sum += subtotal
                order_details_text += f"▪️ {PRODUCTS_DB[idx]['title']} - {qty} dona * {PRODUCTS_DB[idx]['price']:,.0f} so'm = {subtotal:,.0f} so'm\n"

        order_details_text += f"\n💰 **Jami to'langan summa:** {total_sum:,.0f} so'm"
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Yig'ib yuborildi", callback_data=f"complete_order_{order_id}")]
        ])
        
        receipt_photo = BufferedInputFile(receipt_bytes, filename=f"check_{order_id}.jpg")
        await bot.send_photo(
            chat_id=GROUP_ID, 
            photo=receipt_photo, 
            caption=order_details_text, 
            parse_mode="Markdown", 
            reply_markup=markup
        )
            
        return web.json_response({"success": True, "order_id": order_id})
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=400)

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/data", handle_api_data)
    app.router.add_router_add_post = app.router.add_post
    app.router.add_post("/api/order", handle_api_order)
    
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
        logging.info("To'xtatildi.")
