import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# O'zgaruvchilar
BOT_TOKEN = os.getenv("BOT_TOKEN", "8599909804:AAGrZoiDTW-dxkoOgyKCbGNBR841TAcchp4")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6986848905))
GROUP_ID = os.getenv("GROUP_ID", "-1004434264658") # Yetkazuvchilar va xodimlar guruhi

BOT_ADDRESS = "📍 Manzil: Farg'ona viloyati, Yaypan shahri, Stroy Sentr dokoni."
CONTACT_CENTER = "📞 Aloqa markazi: +998 978 105 16 56 \n👨‍💻 Menedjer: @DataCrafterss"
PAYMENT_CARD = "💳 **Karta raqami:** `4097 8300 8361 0556`\n👤 **Karta egasi:** Sadriddin Abduraxmonov"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Bazalar
PRODUCTS_DB = []      # Qo'shilgan mahsulotlar
ORDERS_DB = {}        # Tasdiqlangan buyurtmalar (order_id: data)
ORDER_COUNTER = 100   # Chek raqami uchun boshlang'ich raqam

# FSM holatlari
class AddProduct(StatesGroup):
    title = State()
    price = State()
    stock = State()
    description = State()
    photo = State()

class CheckoutState(StatesGroup):
    waiting_for_quantity = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_region = State()
    waiting_for_receipt = State()

# Savat (foydalanuvchi_id: {product_index: quantity})
USER_CARTS = {}

# 1. /start buyrug'i
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    buttons = [
        [KeyboardButton(text="🛍️ Katalog (Mahsulotlar)")],
        [KeyboardButton(text="🛒 Savatcham"), KeyboardButton(text="📦 Mening buyurtmalarim")],
        [KeyboardButton(text="📍 Do'kon manzili"), KeyboardButton(text="📞 Aloqa markazi")]
    ]
    
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin panel")])

    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer(
        "Assalomu alaykum! **STROY SENTR** online do'koniga xush kelibsiz 🏗\n\n"
        "Kerakli bo'limni tanlang:",
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
async def admin_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Sizda bu bo'limga kirish huquqi yo'q!")
        return

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
    await message.answer("📝 Yangi mahsulot nomini kiriting:")
    await state.set_state(AddProduct.title)

@dp.message(AddProduct.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("💰 Mahsulotning 1 dona narxini kiriting (faqat raqam, masalan: 75000):")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("📦 Omborda bu mahsulotdan nechta borligini kiriting (dona):")
        await state.set_state(AddProduct.stock)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting:")

@dp.message(AddProduct.stock)
async def process_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text)
        await state.update_data(stock=stock)
        await message.answer("📄 Mahsulot haqida qisqacha tavsif yozing:")
        await state.set_state(AddProduct.description)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting:")

@dp.message(AddProduct.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("📸 Mahsulot rasmini yuboring:")
    await state.set_state(AddProduct.photo)

@dp.message(AddProduct.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    product = {
        "title": data.get("title"),
        "price": data.get("price"),
        "stock": data.get("stock"),
        "description": data.get("description"),
        "photo": photo_id
    }
    PRODUCTS_DB.append(product)
    
    await message.answer_photo(photo=photo_id, caption="✅ Mahsulot muvaffaqiyatli qo'shildi!")
    await state.clear()
    await admin_cmd(message)

@dp.message(F.text == "📦 Mahsulotlar ro'yxati")
async def list_products(message: Message):
    if message.from_user.id != ADMIN_ID: return
    if not PRODUCTS_DB:
        await message.answer("📭 Hozircha mahsulotlar yo'q.")
        return
    for i, p in enumerate(PRODUCTS_DB):
        await message.answer_photo(
            photo=p['photo'],
            caption=f"🆔 Indeks: {i}\n📦 Nomi: {p['title']}\n💰 Narxi: {p['price']} so'm\n🔢 Qoldiq: {p['stock']} dona"
        )

@dp.message(F.text == "🗑 Mahsulotlarni tozalash")
async def clear_products(message: Message):
    if message.from_user.id != ADMIN_ID: return
    PRODUCTS_DB.clear()
    await message.answer("🗑 Tozalandi!")

@dp.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await start_cmd(message, state)

# --- KATALOG VA XARID QILISH ---
@dp.message(F.text == "🛍️ Katalog (Mahsulotlar)")
async def show_catalog(message: Message):
    if not PRODUCTS_DB:
        await message.answer("📭 Hozircha do'konda mahsulotlar mavjud emas.")
        return
    
    for i, p in enumerate(PRODUCTS_DB):
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_cart_{i}")]
        ])
        await message.answer_photo(
            photo=p['photo'],
            caption=f"📦 **{p['title']}**\n\n💰 Narxi: {p['price']} so'm\n🔢 Qoldiq: {p['stock']} dona\n📝 {p['description']}",
            reply_markup=markup,
            parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("add_cart_"))
async def add_to_cart_callback(call: CallbackQuery, state: FSMContext):
    idx = int(call.data.split("_")[2])
    user_id = call.from_user.id
    
    if user_id not in USER_CARTS:
        USER_CARTS[user_id] = {}
    
    if idx in USER_CARTS[user_id]:
        USER_CARTS[user_id][idx] += 1
    else:
        USER_CARTS[user_id][idx] = 1
        
    await call.answer("✅ Mahsulot savatga qo'shildi!")

@dp.message(F.text == "🛒 Savatcham")
async def show_cart(message: Message):
    user_id = message.from_user.id
    cart = USER_CARTS.get(user_id, {})
    
    if not cart:
        await message.answer("🛒 Savatingiz bo'sh.")
        return
    
    text = "🛒 **Sizning savatingiz:**\n\n"
    total_sum = 0
    
    for idx, qty in cart.items():
        p = PRODUCTS_DB[idx]
        item_total = p['price'] * qty
        total_sum += item_total
        text += f"• {p['title']} — {qty} dona x {p['price']} = {item_total} so'm\n"
        
    text += f"\n💰 **Jami summa:** {total_sum} so'm"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="start_checkout")],
        [InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart")]
    ])
    
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(call: CallbackQuery):
    USER_CARTS[call.from_user.id] = {}
    await call.message.edit_text("🗑 Savat tozalandi.")

@dp.callback_query(F.data == "start_checkout")
async def start_checkout(call: CallbackQuery, state: FSMContext):
    await call.message.answer("👤 Iltimos, ism va familiyangizni kiriting:")
    await state.set_state(CheckoutState.waiting_for_name)
    await call.answer()

@dp.message(CheckoutState.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📞 Telefon raqamingizni yuboring (masalan: +998901234567):")
    await state.set_state(CheckoutState.waiting_for_phone)

@dp.message(CheckoutState.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("📍 Yetkazish manzilini (viloyat, tuman, ko'cha) kiriting:")
    await state.set_state(CheckoutState.waiting_for_region)

@dp.message(CheckoutState.waiting_for_region)
async def get_region(message: Message, state: FSMContext):
    await state.update_data(region=message.text)
    
    text = (
        f"💳 **To'lovni amalga oshirish:**\n\n"
        f"{PAYMENT_CARD}\n\n"
        f"Pulni o'tkazgach, to'lov **chekining rasmini** shu yerga yuboring:"
    )
    await message.answer(text, parse_mode="Markdown")
    await state.set_state(CheckoutState.waiting_for_receipt)

@dp.message(CheckoutState.waiting_for_receipt, F.photo)
async def get_receipt(message: Message, state: FSMContext):
    global ORDER_COUNTER
    user_id = message.from_user.id
    data = await state.get_data()
    cart = USER_CARTS.get(user_id, {})
    
    if not cart:
        await message.answer("❌ Savatingiz bo'sh.")
        await state.clear()
        return

    order_id = ORDER_COUNTER
    ORDER_COUNTER += 1
    
    receipt_photo = message.photo[-1].file_id
    
    items_list = []
    total_price = 0
    for idx, qty in cart.items():
        p = PRODUCTS_DB[idx]
        item_total = p['price'] * qty
        total_price += item_total
        items_list.append({
            "title": p['title'],
            "price": p['price'],
            "quantity": qty,
            "total": item_total,
            "photo": p['photo']
        })
        
        # Ombor qoldig'ini kamaytirish
        if isinstance(p['stock'], int):
            p['stock'] = max(0, p['stock'] - qty)

    order_data = {
        "order_id": order_id,
        "user_id": user_id,
        "name": data.get("name"),
        "phone": data.get("phone"),
        "region": data.get("region"),
        "items": items_list,
        "total_price": total_price,
        "receipt": receipt_photo
    }
    
    ORDERS_DB[order_id] = order_data
    USER_CARTS[user_id] = {} # Savatni tozalaymiz
    
    # Guruhga yuboriladigan xabar va tugma
    group_text = (
        f"📥 **YANGI BUYURTMA! [Chek №{order_id}]**\n\n"
        f"👤 Mijoz: {data.get('name')}\n"
        f"📞 Telefon: {data.get('phone')}\n"
        f"📍 Manzil: {data.get('region')}\n"
        f"💰 Jami summa: {total_price} so'm\n\n"
        f"👇 *Mahsulotlarni ko'rish uchun quyidagi tugmani bosing:*"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📦 Mahsulotlarni ko'rish (Chek #{order_id})", callback_data=f"view_order_{order_id}")]
    ])
    
    # Guruhga chek rasmi va ma'lumotni tashlaymiz
    await bot.send_photo(
        chat_id=GROUP_ID,
        photo=receipt_photo,
        caption=group_text,
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
    await message.answer(f"✅ **Buyurtmangiz qabul qilindi!**\n\nChek raqamingiz: **#{order_id}**. Xodimlarimiz tez orada aloqaga chiqishadi.")
    await state.clear()

# --- YETKAZUVCHILAR UCHUN MAHSULOTLARNI RASMI BILAN KETMA-KET CHIQARISH ---
@dp.callback_query(F.data.startswith("view_order_"))
async def view_order_items(call: CallbackQuery):
    order_id = int(call.data.split("_")[2])
    order = ORDERS_DB.get(order_id)
    
    if not order:
        await call.answer("❌ Buyurtma topilmadi!", show_alert=True)
        return
    
    await call.message.answer(f"📦 **Buyurtma #{order_id} bo'yicha mahsulotlar ro'yxati:**")
    
    # Telegram albomi (MediaGroup) orqali rasmlarni va nomlarini ketma-ket chiqarish
    media_group = []
    for i, item in enumerate(order['items']):
        caption = f"{i+1}. {item['title']}\nMiqdori: {item['quantity']} dona\nNarxi: {item['price']} so'm\nJami: {item['total']} so'm"
        media_group.append(InputMediaPhoto(media=item['photo'], caption=caption if i == 0 else ""))
        
    if media_group:
        await bot.send_media_group(chat_id=call.message.chat.id, media=media_group)
        
    await call.answer()

# Botni ishga tushirish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
