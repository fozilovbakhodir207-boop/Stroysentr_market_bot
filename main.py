import os
import sqlite3
import logging
import uuid
from pathlib import Path
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Environment o'zgaruvchilari
BOT_TOKEN = os.getenv("BOT_TOKEN", "8599909804:AAGrZoiDTW-dxkoOgyKCbGNBR841TAcchp4")
ADMIN_ID = os.getenv("ADMIN_ID", "6986848905")
GROUP_ID = os.getenv("GROUP_ID", "-1004434264658")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://stroysentr-market-bot.onrender.com")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Papkalarga absolyut (aniq va to'liq) yo'l ko'rsatish
BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
UPLOAD_DIR = BASE_DIR / "uploads"

# Papkalarni avtomatik yaratish
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# SQLite bazasini ulash
def init_db():
    db_path = BASE_DIR / "store.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            image_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- BOT HANDLERS ---
@dp.message(F.text == "/start")
async def start_cmd(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Do'konni ochish",
                    web_app=WebAppInfo(url=WEB_APP_URL)
                )
            ]
        ]
    )
    await message.answer("Assalomu alaykum! STROY SENTR do'konimizga xush kelibsiz. Do'konni ochish uchun pastdagi tugmani bosing:", reply_markup=keyboard)

# --- API ENDPOINTS ---

# 1. Bosh sahifa (index.html uzatish)
async def handle_index(request):
    index_file = PUBLIC_DIR / "index.html"
    if index_file.exists():
        return web.FileResponse(index_file)
    return web.Response(text=f"index.html topilmadi (Manzil: {index_file})", status=404)

# 2. Mahsulotlarni olish
async def handle_get_products(request):
    try:
        db_path = BASE_DIR / "store.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, price, stock, image_url FROM products ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        products = [
            {
                "id": r[0],
                "title": r[1],
                "price": r[2],
                "stock": r[3],
                "image_url": r[4]
            }
            for r in rows
        ]

        return web.json_response({"status": "success", "products": products})
    except Exception as e:
        logging.error(f"Get products error: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# 3. Admin uchun: Galereyadan rasm bilan mahsulot qo'shish
async def handle_add_product(request):
    try:
        reader = await request.multipart()
        
        user_id = None
        title = None
        price = None
        stock = 0
        image_url = ""

        while True:
            field = await reader.next()
            if field is None:
                break

            if field.name == 'user_id':
                user_id = (await field.read()).decode('utf-8')
            elif field.name == 'title':
                title = (await field.read()).decode('utf-8')
            elif field.name == 'price':
                price_str = (await field.read()).decode('utf-8')
                price = float(price_str) if price_str else 0.0
            elif field.name == 'stock':
                stock_str = (await field.read()).decode('utf-8')
                stock = int(stock_str) if stock_str else 0
            elif field.name == 'image':
                filename = field.filename
                if filename:
                    ext = Path(filename).suffix
                    unique_filename = f"{uuid.uuid4().hex}{ext}"
                    filepath = UPLOAD_DIR / unique_filename
                    
                    with open(filepath, 'wb') as f:
                        while True:
                            chunk = await field.read_chunk()
                            if not chunk:
                                break
                            f.write(chunk)
                    
                    image_url = f"/uploads/{unique_filename}"

        if str(user_id) != str(ADMIN_ID):
            return web.json_response({"status": "error", "message": "Ruxsat berilmagan!"}, status=403)

        if not title or price is None:
            return web.json_response({"status": "error", "message": "Ma'lumotlar to'liq emas!"}, status=400)

        db_path = BASE_DIR / "store.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (title, price, stock, image_url) VALUES (?, ?, ?, ?)",
            (title, price, stock, image_url)
        )
        conn.commit()
        conn.close()

        return web.json_response({"status": "success", "message": "Mahsulot muvaffaqiyatli qo'shildi!"})

    except Exception as e:
        logging.error(f"Add product error: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# 4. Buyurtmani guruhga yuborish
async def handle_create_order(request):
    try:
        data = await request.json()
        
        user_name = data.get('user_name', 'Xaridor')
        phone = data.get('phone', 'Ko\'rsatilmadi')
        address = data.get('address', 'Kelishiladi')
        items = data.get('items', [])
        total_price = data.get('total_price', 0)

        if not items:
            return web.json_response({"status": "error", "message": "Savat bo'sh!"}, status=400)

        text = f"🛍 <b>YANGI BUYURTMA!</b>\n\n"
        text += f"👤 <b>Xaridor:</b> {user_name}\n"
        text += f"📞 <b>Tel:</b> {phone}\n"
        text += f"📍 <b>Manzil:</b> {address}\n\n"
        text += f"📦 <b>Mahsulotlar:</b>\n"

        for item in items:
            text += f"• {item['title']} - {item['quantity']} dona x {int(item['price']):,} so'm\n"

        text += f"\n💰 <b>Jami summa:</b> {int(total_price):,} so'm"

        await bot.send_message(chat_id=GROUP_ID, text=text, parse_mode="HTML")

        return web.json_response({"status": "success", "message": "Buyurtma qabul qilindi!"})

    except Exception as e:
        logging.error(f"Order error: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# SERVERNI SOZLASH VA ISHGA TUSHIRISH
async def init_app():
    app = web.Application()

    app.router.add_get('/', handle_index)
    app.router.add_get('/api/products', handle_get_products)
    app.router.add_post('/api/products/add', handle_add_product)
    app.router.add_post('/api/orders/create', handle_create_order)

    app.router.add_static('/public/', path=str(PUBLIC_DIR), name='public')
    app.router.add_static('/uploads/', path=str(UPLOAD_DIR), name='uploads')

    return app

async def main():
    app = await init_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
