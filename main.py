import asyncio
import base64
import io
import json
import logging
import os
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import os
import uuid

# Rasmlar saqlanadigan papka
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==========================================
# CONFIGURE LOGGING & CONFIG
# ==========================================
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get(
    "BOT_TOKEN", "8599909804:AAGrZoiDTW-dxkoOgyKCbGNBR841TAcchp4"
)  # BotFather bergan Token
ADMIN_ID = int(
    os.environ.get("ADMIN_ID", "6986848905")
)  # O'zingizning Telegram ID-ingiz
ORDERS_GROUP_ID = int(
    os.environ.get("ORDERS_GROUP_ID", "-1004434264658")
)  # Zakazlar tushadigan guruh ID-si

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ==========================================
# DATABASE INITIALIZATION
# ==========================================
def init_db():
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()

  # Mahsulotlar jadvali (soni/stock bilan)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            image_url TEXT
        )
    """)

  # Buyurtmalar jadvali
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            items TEXT,
            total_price REAL,
            status TEXT DEFAULT 'pending'
        )
    """)

  conn.commit()
  conn.close()


init_db()


# ==========================================
# AIOHTTP WEB SERVER & API FOR MINI APP
# ==========================================
async def handle_get_products(request):
  """Mini App ichiga barcha aktiv mahsulotlarni qaytaradi"""
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, title, price, stock, image_url FROM products WHERE stock > 0"
  )
  rows = cursor.fetchall()
  conn.close()

  products = [
      {
          "id": r[0],
          "title": r[1],
          "price": r[2],
          "stock": r[3],
          "image_url": r[4],
      }
      for r in rows
  ]
  return web.json_response({"status": "success", "products": products})


async def handle_add_product(request):
    try:
        if request.content_type == 'application/json':
            data = await request.json()
        else:
            data = await request.post()

        user_id = str(data.get('user_id', ''))
        title = data.get('title')
        price = data.get('price')
        stock = data.get('stock')
        image_url = data.get('image_url', '')

        if user_id != str(ADMIN_ID):
            return web.json_response({'status': 'error', 'message': 'Ruxsat berilmagan'}, status=403)

        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (title, price, stock, image_url) VALUES (?, ?, ?, ?)",
            (title, price, stock, image_url)
        )
        conn.commit()
        conn.close()

        return web.json_response({'status': 'success'})
    except Exception as e:
        logging.error(f"Add product error: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)
        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (title, price, stock, image_url) VALUES (?, ?, ?, ?)",
            (title, price, stock, image_url)
        )
        conn.commit()
        conn.close()

        return web.json_response({'status': 'success'})
    except Exception as e:
        logging.error(f"Add product error: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)
    stock = int(data.get("stock"))
    image_url = data.get("image_url", "")

    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (title, price, stock, image_url) VALUES (?, ?,"
        " ?, ?)",
        (title, price, stock, image_url),
    )
    conn.commit()
    conn.close()

return web.json_response(
        {"status": "success", "message": "Mahsulot qo'shildi!"}
    )
except Exception as e:
    return web.json_response({"status": "error", "message": str(e)}, status=500)


async def handle_create_order(request):
  """Mini App'dan chek rasmi bilan birga kelgan buyurtmani qabul qilish"""
  try:
    data = await request.json()
    user_id = data.get("user_id")
    user_name = data.get("user_name")
    items = data.get("items")  # List of {id, title, qty, price}
    total_price = data.get("total_price")
    receipt_base64 = data.get("receipt_base64")  # Chek rasmi (Base64)

    items_str = ", ".join([f"{i['title']} ({i['qty']} ta)" for i in items])

    # Bazaga zakazni yozamiz
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, user_name, items, total_price, status)"
        " VALUES (?, ?, ?, ?, 'pending')",
        (user_id, user_name, items_str, total_price),
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Admin guruhga xabar va chek rasmini yuborish
    caption = (
        f"🛍 <b>YANGI BUYURTMA #{order_id} (UZUM STYLE)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Mijoz:</b> {user_name} (ID: {user_id})\n"
        f"📦 <b>Tavarlar:</b> {items_str}\n"
        f"💰 <b>Jami summa:</b> {total_price:,.0f} so'm\n"
        f"📑 <b>Holati:</b> Chek tekshirilmoqda..."
    )

    # Inline Keyboard tasdiqlash uchun
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text="✅ To'lovni tasdiqlash",
                callback_data=f"confirm_{order_id}_{user_id}",
            ),
            types.InlineKeyboardButton(
                text="❌ Rad etish", callback_data=f"reject_{order_id}_{user_id}"
            ),
        ]]
    )

    if receipt_base64:
      header, encoded = receipt_base64.split(",", 1)
      image_data = base64.b64decode(encoded)
      photo = types.BufferedInputFile(image_data, filename="receipt.jpg")

      await bot.send_photo(
          chat_id=ORDERS_GROUP_ID,
          photo=photo,
          caption=caption,
          parse_mode="HTML",
          reply_markup=keyboard,
      )
    else:
      await bot.send_message(
          chat_id=ORDERS_GROUP_ID,
          text=caption,
          parse_mode="HTML",
          reply_markup=keyboard,
      )

    return web.json_response(
        {"status": "success", "message": "Buyurtma qabul qilindi!"}
    )

  except Exception as e:
    logging.error(f"Order API error: {e}")
    return web.json_response({"status": "error", "message": str(e)}, status=500)


# ==========================================
# CALLBACK HANDLERS (ADMIN CONFIRMATION)
# ==========================================
@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_order(call: types.CallbackQuery):
  _, order_id, user_id = call.data.split("_")

  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()

  # Zakaz holatini update qilish
  cursor.execute(
      "UPDATE orders SET status = 'completed' WHERE id = ?", (order_id,)
  )
  conn.commit()
  conn.close()

  await call.message.edit_caption(
      caption=call.message.caption
      + "\n\n✅ <b>TO'LOV TASDIQLANDI VA OMBORDANT AYIRILDI!</b>",
      parse_mode="HTML",
  )

  # Mijozga bildirishnoma yuborish
  try:
    await bot.send_message(
        chat_id=int(user_id),
        text=(
            f"🎉 <b>Buyurtmangiz #{order_id} tasdiqlandi!</b>\n\nTo'lovingiz"
            " qabul qilindi. Mahsulotlaringiz tez orada yetkazib beriladi!"
        ),
        parse_mode="HTML",
    )
  except Exception as e:
    logging.error(f"User notify error: {e}")

  await call.answer("Buyurtma tasdiqlandi!")


@dp.callback_query(F.data.startswith("reject_"))
async def reject_order(call: types.CallbackQuery):
  _, order_id, user_id = call.data.split("_")

  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE orders SET status = 'rejected' WHERE id = ?", (order_id,)
  )
  conn.commit()
  conn.close()

  await call.message.edit_caption(
      caption=call.message.caption + "\n\n❌ <b>TO'LOV RAD ETILDI!</b>",
      parse_mode="HTML",
  )

  try:
    await bot.send_message(
        chat_id=int(user_id),
        text=(
            f"❌ <b>Buyurtmangiz #{order_id} rad etildi.</b>\n\nIltimos,"
            " to'lov chekini qayta tekshirib ko'ring yoki admin bilan bog'laning."
        ),
        parse_mode="HTML",
    )
  except Exception as e:
    logging.error(f"User notify error: {e}")

  await call.answer("Buyurtma rad etildi!")


# ==========================================
# BOT START COMMAND
# ==========================================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
  kb = types.ReplyKeyboardMarkup(
      keyboard=[[
          types.KeyboardButton(
              text="🛍 Uzum Market (Mini App)",
              web_app=types.WebAppInfo(
                  url="https://stroysentr-market-bot.onrender.com"
              ),
          )
      ]],
      resize_keyboard=True,
  )
  await message.answer(
      f"Assalomu alaykum, {message.from_user.full_name}!\nSTROY SENTR do'koniga"
      " xush kelibsiz. Do'konni ochish uchun pastdagi tugmani bosing.",
      reply_markup=kb,
  )


# ==========================================
# SERVER RUNNER
# ==========================================
async def start_server():
  app = web.Application()
  # API routelari
  app.router.add_get("/api/products", handle_get_products)
async def handle_add_product(request):
  try:
    reader = await request.multipart()
    title, price, stock, user_id = None, None, None, None
    filename_saved = ""

    while True:
      part = await reader.next()
      if part is None:
        break

      if part.name == "user_id":
        user_id = int(await part.text())
      elif part.name == "title":
        title = await part.text()
      elif part.name == "price":
        price = float(await part.text())
      elif part.name == "stock":
        stock = int(await part.text())
      elif part.name == "image" and part.filename:
        ext = os.path.splitext(part.filename)[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        # Rasmni uploads papkasiga saqlash
        with open(file_path, "wb") as f:
          while True:
            chunk = await part.read_chunk()
            if not chunk:
              break
            f.write(chunk)

        filename_saved = f"/uploads/{unique_name}"

    if user_id != ADMIN_ID:
      return web.json_response(
          {"status": "error", "message": "Ruxsat berilmagan!"}, status=403
      )

    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (title, price, stock, image_url) VALUES (?, ?,"
        " ?, ?)",
        (title, price, stock, filename_saved),
    )
    conn.commit()
    conn.close()

    return web.json_response(
        {"status": "success", "message": "Mahsulot muvaffaqiyatli saqlandi!"}
    )

  except Exception as e:
    logging.error(f"Add product error: {e}")
    return web.json_response({"status": "error", "message": str(e)}, status=500) 
  app.router.add_post("/api/order", handle_create_order)

  # HTML faylni static berish
  async def index(request):
    return web.FileResponse("./index.html")

  app.router.add_get("/", index)

  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.environ.get("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()
  logging.info(f"Server started on port {port}")


async def start_server():
  app = web.Application()
  app.router.add_static("/uploads", UPLOAD_DIR)
  app.router.add_get("/api/products", handle_get_products)
  app.router.add_post("/api/products", handle_add_product)
  app.router.add_post("/api/order", handle_create_order)

  async def index(request):
    return web.FileResponse("./index.html")

  app.router.add_get("/", index)

  runner = web.AppRunner(app)
  await runner.setup()

  # Render beradigan PORT ni o'qiymiz
  port = int(os.getenv("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()
  logging.info(f"Server started on port {port}")




async def main():
    # 1. BIRINCHI: Veb-serverni ishga tushiramiz
    await start_server()
    # 2. IKKINCHI: Bot pollingini yoqamiz
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
