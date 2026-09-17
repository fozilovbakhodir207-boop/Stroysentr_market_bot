Fozilov_B :
import asyncio import logging import os import sqlite3 from aiogram import Bot, Dispatcher, F, types from aiogram.filters import Command from aiogram.types import ( BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ) from aiohttp import web
logging.basicConfig(level=logging.INFO)
==========================================
⚙️ SOZLAMALAR (TOKEN, ADMIN VA GURUH)
==========================================
🔑 BotFather'dan olgan tokeningiz:
BOT_TOKEN = "8599909804:AAGrZoiDTW-dxkoOgyKCbGNBR841TAcchp4"
👑 @userinfobot orqali olgan shaxsiy Telegram ID raqamingiz:
ADMIN_IDS = [6986848905]
📢 Buyurtmalar tushadigan Telegram guruh ID'si (-100 bilan boshlanadi):
ORDERS_GROUP_ID =-1004434264658
bot = Bot(token=BOT_TOKEN) dp = Dispatcher()
==========================================
1. DATABASE (MA'LUMOTLAR BAZASI)
==========================================
def init_db(): conn = sqlite3.connect("stroy_sentr.db") cursor = conn.cursor() cursor.execute(""" CREATE TABLE IF NOT EXISTS products ( id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL, stock INTEGER DEFAULT 0 ) """) cursor.execute(""" CREATE TABLE IF NOT EXISTS orders ( id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, user_name TEXT, phone TEXT, total_amount REAL, items TEXT, status TEXT DEFAULT 'pending' ) """) conn.commit() conn.close()
==========================================
2. RENDER 24/7 ISHLASHI UCHUN VEB-SERVER
==========================================
async def handle_ping(request): return web.Response( text="STROY SENTR Bot 24/7 rejimda ishlamoqda!", status=200 )
async def start_web_server(): app = web.Application() app.router.add_get("/", handle_ping) runner = web.AppRunner(app) await runner.setup() port = int(os.environ.get("PORT", 8080)) site = web.TCPSite(runner, "0.0.0.0", port) await site.start()
==========================================
3. BOT META MA'LUMOTLARI VA MENYU
==========================================
async def set_bot_meta_info(bot: Bot): description_text = ( "🏗 STROY SENTR — Qurilish mollari, pardozlash mahsulotlari, " "online zakaz qilish va yetkazib berish xizmati.\n\n" "Usta va xaridorlar uchun qulay hamda tezkor do'kon!" ) await bot.set_my_description(description_text)
short_description = ( "Stroy center qurilish mollari, pardozlash mahsulotlari, online zakaz" " qilish va yetkazib berish xizmati." ) await bot.set_my_short_description(short_description)
commands = [ BotCommand(command="start", description="Botni qayta ishga tushirish"), BotCommand(command="admin", description="Admin Panel (Faqat egalari uchun)"), ] await bot.set_my_commands(commands)
def main_menu_keyboard(): kb = [ [ KeyboardButton(text="🛍 Mahsulotlar katalogi"), KeyboardButton(text="📦 Zakaz berish"), ], [ KeyboardButton(text="🚚 Yetkazib berish shartlari"), KeyboardButton(text="📞 Biz bilan aloqa"), ], [KeyboardButton(text="📍 Do'konimiz manzili")], ] return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
==========================================
4. GURUHGA BUYURTMA YUBORISH FUNKSIYASI
==========================================
async def send_order_to_group(bot: Bot, order_data: dict): text = ( f"🚨 <b>YANGI BUYURTMA #{order_data['order_id']}</b>\n" f"━━━━━━━━━━━━━━━━━━\n" f"👤 <b>Mijoz:</b> {order_data['user_name']}\n" f"📞 <b>Tel:</b> {order_data['phone']}\n" f"🛒 <b>Mahsulotlar:</b>\n{order_data['items']}\n\n" f"💰 <b>Jami summa:</b> {order_data['total_price']:,.2f} so'm\n" f"📍 <b>Manzil:</b> {order_data['location']}" )
kb = InlineKeyboardMarkup( inline_keyboard=[ [ InlineKeyboardButton( text="✅ Tasdiqlash", callback_data=f"confirm_{order_data['order_id']}", ), InlineKeyboardButton( text="❌ Bekor qilish", callback_data=f"cancel_{order_data['order_id']}", ), ] ] )
if order_data.get("receipt_photo"): await bot.send_photo( chat_id=ORDERS_GROUP_ID, photo=order_data["receipt_photo"], caption=text, reply_markup=kb, parse_mode="HTML", ) else: await bot.send_message( chat_id=ORDERS_GROUP_ID, text=text, reply_markup=kb, parse_mode="HTML", )
==========================================
5. USER HANDLERLARI

Fozilov_B :
==========================================
@dp.message(Command("start")) async def start_handler(message: types.Message): welcome_text = ( f"Assalomu alaykum, {message.from_user.full_name}!\n\n" "🏗 STROY SENTR rasmiy botiga xush kelibsiz!\n\n" "Bu yerda siz qurilish va pardozlash mahsulotlarini onlayn zakaz qilishingiz " "va manzilingizga yetkazib berish xizmatidan foydalanishingiz mumkin.\n\n" "Kerakli bo'limni tanlang 👇" ) await message.answer( welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard() )
@dp.message(F.text == "📞 Biz bilan aloqa") async def contact_handler(message: types.Message): await message.answer( "📞 STROY SENTR Aloqa markazi:\n\n" "📱 Telefon: +998 90 XXX XX XX\n" "💬 Admin: @stroy_sentr_admin\n" "⏰ Ish vaqti: 08:00 - 19:00", parse_mode="Markdown", )
@dp.message(F.text == "📍 Do'konimiz manzili") async def location_handler(message: types.Message): await message.answer( "📍 Do'konimiz manzili:\n\nYaypan shahri, STROY SENTR qurilish" " do'koni.", parse_mode="Markdown", )
==========================================
6. ADMIN PANEL VA STATUS BOSHGARUVI
==========================================
@dp.message(Command("admin"), F.from_user.id.in_(ADMIN_IDS)) async def admin_panel(message: types.Message): kb = InlineKeyboardMarkup( inline_keyboard=[ [ InlineKeyboardButton( text="📦 Ombor va Qoldiqni boshqarish", callback_data="admin_stock", ) ], [ InlineKeyboardButton( text="📊 Oylik Hisobot", callback_data="admin_report" ) ], ] ) await message.answer( "🏗 <b>STROY SENTR Admin Paneli</b>\n\nBoshqaruv bo'limini tanlang:", reply_markup=kb, parse_mode="HTML", )
@dp.callback_query(F.data.startswith("confirm_")) async def confirm_order(callback: types.CallbackQuery): order_id = callback.data.split("_")[1] await callback.message.edit_caption( caption=f"{callback.message.caption}\n\n✅ <b>BUYURTMA TASDIQLANDI!</b>", parse_mode="HTML", ) await callback.answer("Buyurtma tasdiqlandi!")
@dp.callback_query(F.data.startswith("cancel_")) async def cancel_order(callback: types.CallbackQuery): order_id = callback.data.split("_")[1] await callback.message.edit_caption( caption=f"{callback.message.caption}\n\n❌ <b>BUYURTMA BEKOR QILINDI!</b>", parse_mode="HTML", ) await callback.answer("Buyurtma bekor qilindi!")
==========================================
7. ISHGA TUSHIRISH
==========================================
async def main(): init_db() await set_bot_meta_info(bot) await start_web_server() await bot.delete_webhook(drop_pending_updates=True) print("STROY SENTR Boti 24/7 rejimida ishga tushdi!") await dp.start_polling(bot)
if name == "main": try: asyncio.run(main()) except (KeyboardInterrupt, SystemExit): pass
