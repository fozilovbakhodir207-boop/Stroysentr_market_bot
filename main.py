import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiohttp import web

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# O'zgaruvchilar
BOT_TOKEN = os.getenv("BOT_TOKEN", "8599909804:AAGrZoiDTW-dxkoOgyKCBGNBR841TAcchp4")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6986848905))
GROUP_ID = os.getenv("GROUP_ID", -1004434264658)
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://fozilovbakhodir207-boop.github.io/Stroysentr_market_bot/")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 1. /start buyrug'i
@dp.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    
    buttons = [
        [KeyboardButton(text="🛍️ Do'konni ochish", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin panel")])

    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer(
        "Assalomu alaykum! STROY SENTR do'konimizga xush kelibsiz.\n"
        "Do'konni ochish uchun pastdagi tugmani bosing:",
        reply_markup=markup
    )

# 2. Admin panel buyrug'i
@dp.message(Command("admin"))
@dp.message(F.text == "⚙️ Admin panel")
async def admin_cmd(message: Message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("❌ Sizda admin huquqlari yo'q!")
        return

    await message.answer("🛠 **STROY SENTR Admin paneli**\n\nXush kelibsiz!")

# 3. Mini App buyurtmalarini guruhga yuborish (API Endpoint)
async def handle_order(request):
    try:
        data = await request.json()
        
        name = data.get("name", "Noma'lum")
        phone = data.get("phone", "Noma'lum")
        items = data.get("items", [])
        total_price = data.get("total_price", 0)

        order_text = f"📥 **YANGI BUYURTMA!**\n\n"
        order_text += f"👤 **Mijoz:** {name}\n"
        order_text += f"📞 **Tel:** {phone}\n\n"
        order_text += "🛒 **Mahsulotlar:**\n"
        
        for item in items:
            order_text += f"• {item.get('title')} x {item.get('quantity', 1)} - {item.get('price')} so'm\n"
            
        order_text += f"\n💰 **Jami summa:** {total_price} so'm"

        await bot.send_message(chat_id=GROUP_ID, text=order_text)
        return web.json_response({"status": "success"})
    except Exception as e:
        logging.error(f"Order error: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# Web server va Botni parallel ishga tushirish
async def main():
    app = web.Application()
    app.router.add_post("/api/order", handle_order)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render o'zi ajratadigan PORT ni olamiz
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logging.info(f"Web server {port}-portda muvaffaqiyatli ishga tushdi!")
    
    # Bot pollingni boshlash
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
