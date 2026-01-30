"""
Main Telegram Bot for Sushi Delivery
"""
import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)
from telegram.constants import ParseMode

import database as db

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Conversation states
WAITING_DELIVERY_TYPE = 0
WAITING_ADDRESS = 1
WAITING_NAME = 2
WAITING_PHONE = 3
WAITING_COMMENT = 4
CONFIRM_ORDER = 5
# Admin states
ADMIN_MENU = 6
ADMIN_ADD_ADMIN = 7
ADMIN_REMOVE_ADMIN = 8
ADMIN_ADD_RECEIVER = 9
ADMIN_REMOVE_RECEIVER = 10
ADMIN_ADD_CATEGORY = 11
ADMIN_EDIT_CATEGORY_SELECT = 12
ADMIN_EDIT_CATEGORY_NAME = 13
ADMIN_DELETE_CATEGORY = 14
ADMIN_ADD_PRODUCT_CATEGORY = 15
ADMIN_ADD_PRODUCT_NAME = 16
ADMIN_ADD_PRODUCT_DESC = 17
ADMIN_ADD_PRODUCT_PRICE = 18
ADMIN_ADD_PRODUCT_IMAGE = 19
ADMIN_EDIT_PRODUCT_SELECT = 20
ADMIN_EDIT_PRODUCT_FIELD = 21
ADMIN_EDIT_PRODUCT_VALUE = 22
ADMIN_DELETE_PRODUCT = 23
ADMIN_BROADCAST_MESSAGE = 24
ADMIN_ADD_SUBCATEGORY_PARENT = 25
ADMIN_ADD_SUBCATEGORY_NAME = 26

# Delivery cost
DELIVERY_COST = 4.0
PICKUP_ADDRESS = "Новый Свержень, Железнодорожная 12а"

# Welcome message
WELCOME_MESSAGE = """🍣 *Добро пожаловать в SushiMart!*

Этот бот был создан для заказа суши в г. Столбцы.

🕐 *Время работы:* 9:00 - 22:00

Выберите действие из меню ниже:"""

ABOUT_MESSAGE = """📍 *О нас*

🍣 *SushiMart* - доставка свежих суши и японской кухни в г. Столбцы.

📍 *Адрес:* Новый Свержень, Железнодорожная 12а

🕐 *Время работы:* 9:00 - 22:00

🚗 *Доставка:* 4 BYN
🏃 *Самовывоз:* бесплатно

💳 *Оплата:* наличными при получении"""


def get_main_keyboard():
    """Get main menu keyboard"""
    keyboard = [
        [KeyboardButton("🍣 Меню"), KeyboardButton("🛒 Корзина")],
        [KeyboardButton("📋 История заказов"), KeyboardButton("ℹ️ О нас")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_keyboard():
    """Get admin menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("👥 Администраторы", callback_data="admin_admins")],
        [InlineKeyboardButton("🔔 Получатели уведомлений", callback_data="admin_receivers")],
        [InlineKeyboardButton("📁 Категории", callback_data="admin_categories")],
        [InlineKeyboardButton("📦 Товары", callback_data="admin_products")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    await db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard()
    )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu categories"""
    categories = await db.get_main_categories()
    
    if not categories:
        await update.message.reply_text("😔 Меню пока пусто")
        return
    
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat["name"], callback_data=f"cat_{cat['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    
    await update.message.reply_text(
        "🍣 *Выберите категорию:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_main":
        try:
            await query.message.delete()
        except:
            pass
        return
    
    if data.startswith("cat_"):
        category_id = data[4:]
        category = await db.get_category_by_id(category_id)
        
        if not category:
            try:
                await query.message.edit_text("❌ Категория не найдена")
            except:
                await query.message.reply_text("❌ Категория не найдена")
            return
        
        # Check for subcategories
        subcategories = await db.get_subcategories(category_id)
        
        if subcategories:
            # Show subcategories
            keyboard = []
            for subcat in subcategories:
                keyboard.append([InlineKeyboardButton(subcat["name"], callback_data=f"cat_{subcat['id']}")])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
            
            try:
                await query.message.edit_text(
                    f"*{category['name']}*\n\nВыберите подкатегорию:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                # Message has photo, delete and send new
                try:
                    await query.message.delete()
                except:
                    pass
                await query.message.chat.send_message(
                    f"*{category['name']}*\n\nВыберите подкатегорию:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            # Show products in category
            await show_products_in_category(query, category_id, category["name"])
    
    elif data == "back_to_menu":
        categories = await db.get_main_categories()
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(cat["name"], callback_data=f"cat_{cat['id']}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
        
        try:
            await query.message.edit_text(
                "🍣 *Выберите категорию:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            # Message has photo, delete and send new
            try:
                await query.message.delete()
            except:
                pass
            await query.message.chat.send_message(
                "🍣 *Выберите категорию:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif data.startswith("back_to_cat_"):
        parent_id = data[12:]
        category = await db.get_category_by_id(parent_id)
        subcategories = await db.get_subcategories(parent_id)
        
        keyboard = []
        for subcat in subcategories:
            keyboard.append([InlineKeyboardButton(subcat["name"], callback_data=f"cat_{subcat['id']}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        
        try:
            await query.message.edit_text(
                f"*{category['name']}*\n\nВыберите подкатегорию:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            # Message has photo, delete and send new
            try:
                await query.message.delete()
            except:
                pass
            await query.message.chat.send_message(
                f"*{category['name']}*\n\nВыберите подкатегорию:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


async def show_products_in_category(query, category_id: str, category_name: str):
    """Show all products in a category on one page"""
    products = await db.get_products_by_category(category_id)
    
    category = await db.get_category_by_id(category_id)
    parent_id = category.get("parent_id") if category else None
    back_data = f"back_to_cat_{parent_id}" if parent_id else "back_to_menu"
    
    if not products:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=back_data)]]
        try:
            await query.message.edit_text(
                f"*{category_name}*\n\n😔 В этой категории пока нет товаров",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            try:
                await query.message.delete()
            except:
                pass
            await query.message.chat.send_message(
                f"*{category_name}*\n\n😔 В этой категории пока нет товаров",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Build product list text
    text = f"*{category_name}*\n\n"
    
    keyboard = []
    for i, product in enumerate(products):
        text += f"*{i+1}. {product['name']}*\n"
        text += f"📝 {product['description']}\n"
        text += f"💰 *{product['price']:.2f} BYN*\n\n"
        
        # Add buttons for each product: quantity selector and add to cart
        keyboard.append([
            InlineKeyboardButton("➖", callback_data=f"qty_minus_{product['id']}_0"),
            InlineKeyboardButton("1", callback_data=f"qty_show_{product['id']}"),
            InlineKeyboardButton("➕", callback_data=f"qty_plus_{product['id']}_0"),
            InlineKeyboardButton("🛒", callback_data=f"add_cart_{product['id']}_0")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=back_data)])
    
    # Delete old message and send new (to handle photo messages)
    try:
        await query.message.delete()
    except:
        pass
    
    await query.message.chat.send_message(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def send_product_card(query, product: dict, category_id: str, index: int, total: int):
    """Send product card with photo"""
    category = await db.get_category_by_id(category_id)
    parent_id = category.get("parent_id") if category else None
    back_data = f"back_to_cat_{parent_id}" if parent_id else "back_to_menu"
    
    text = f"*{product['name']}*\n\n"
    text += f"📝 {product['description']}\n\n"
    text += f"💰 *{product['price']:.2f} BYN*"
    
    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data=f"qty_minus_{product['id']}_{index}"),
            InlineKeyboardButton("1", callback_data=f"qty_show_{product['id']}"),
            InlineKeyboardButton("➕", callback_data=f"qty_plus_{product['id']}_{index}")
        ],
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"add_cart_{product['id']}_{index}")],
    ]
    
    # Navigation buttons
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"prod_prev_{category_id}_{index}"))
    nav_buttons.append(InlineKeyboardButton(f"{index + 1}/{total}", callback_data="noop"))
    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"prod_next_{category_id}_{index}"))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=back_data)])
    
    try:
        await query.message.delete()
    except:
        pass
    
    if product.get("image_url"):
        try:
            await query.message.chat.send_photo(
                photo=product["image_url"],
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            await query.message.chat.send_message(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await query.message.chat.send_message(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product interactions"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # Initialize quantity in context if not exists
    if "quantities" not in context.user_data:
        context.user_data["quantities"] = {}
    
    if data.startswith("qty_minus_"):
        parts = data.split("_")
        product_id = parts[2]
        
        current_qty = context.user_data["quantities"].get(product_id, 1)
        if current_qty > 1:
            context.user_data["quantities"][product_id] = current_qty - 1
        
        await update_quantity_button(query, product_id, context.user_data["quantities"].get(product_id, 1), context)
    
    elif data.startswith("qty_plus_"):
        parts = data.split("_")
        product_id = parts[2]
        
        current_qty = context.user_data["quantities"].get(product_id, 1)
        context.user_data["quantities"][product_id] = current_qty + 1
        
        await update_quantity_button(query, product_id, context.user_data["quantities"][product_id], context)
    
    elif data.startswith("add_cart_"):
        parts = data.split("_")
        product_id = parts[2]
        
        product = await db.get_product_by_id(product_id)
        if product:
            qty = context.user_data["quantities"].get(product_id, 1)
            await db.add_to_cart(user_id, product_id, product["name"], qty, product["price"])
            await query.answer(f"✅ {product['name']} x{qty} добавлено в корзину!", show_alert=True)
            # Reset quantity
            context.user_data["quantities"][product_id] = 1
            # Update display
            await update_quantity_button(query, product_id, 1, context)
    
    elif data == "noop":
        pass


async def update_quantity_button(query, product_id: str, quantity: int, index: int):
    """Update quantity button in product list"""
    product = await db.get_product_by_id(product_id)
    if not product:
        return
    
    category_id = product["category_id"]
    category = await db.get_category_by_id(category_id)
    category_name = category.get("name", "") if category else ""
    parent_id = category.get("parent_id") if category else None
    back_data = f"back_to_cat_{parent_id}" if parent_id else "back_to_menu"
    
    products = await db.get_products_by_category(category_id)
    
    # Rebuild the entire keyboard with updated quantity for this product
    text = f"*{category_name}*\n\n"
    keyboard = []
    
    # Get all quantities from context (we need to preserve them)
    for i, prod in enumerate(products):
        text += f"*{i+1}. {prod['name']}*\n"
        text += f"📝 {prod['description']}\n"
        text += f"💰 *{prod['price']:.2f} BYN*\n\n"
        
        # Use updated quantity for the changed product
        if prod['id'] == product_id:
            qty_display = str(quantity)
        else:
            qty_display = "1"  # Default, will be updated dynamically
        
        keyboard.append([
            InlineKeyboardButton("➖", callback_data=f"qty_minus_{prod['id']}_0"),
            InlineKeyboardButton(qty_display if prod['id'] == product_id else "1", callback_data=f"qty_show_{prod['id']}"),
            InlineKeyboardButton("➕", callback_data=f"qty_plus_{prod['id']}_0"),
            InlineKeyboardButton("🛒", callback_data=f"add_cart_{prod['id']}_0")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=back_data)])
    
    try:
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        pass


async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's cart"""
    user_id = update.effective_user.id
    cart = await db.get_user_cart(user_id)
    
    if not cart:
        await update.message.reply_text(
            "🛒 *Ваша корзина пуста*\n\nВыберите товары в меню!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "🛒 *Ваша корзина:*\n\n"
    total = 0
    
    keyboard = []
    for i, item in enumerate(cart):
        item_total = item["price"] * item["quantity"]
        total += item_total
        text += f"{i+1}. {item['product_name']}\n"
        text += f"   {item['quantity']} x {item['price']:.2f} = *{item_total:.2f} BYN*\n\n"
        
        keyboard.append([
            InlineKeyboardButton("➖", callback_data=f"cart_minus_{item['product_id']}"),
            InlineKeyboardButton(f"{item['product_name'][:15]}... ({item['quantity']})", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"cart_plus_{item['product_id']}"),
            InlineKeyboardButton("🗑", callback_data=f"cart_remove_{item['product_id']}")
        ])
    
    text += f"━━━━━━━━━━━━━━━\n*Итого: {total:.2f} BYN*"
    
    keyboard.append([InlineKeyboardButton("🗑 Очистить корзину", callback_data="cart_clear")])
    keyboard.append([InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")])
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cart interactions"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("cart_minus_"):
        product_id = data[11:]
        cart = await db.get_user_cart(user_id)
        for item in cart:
            if item["product_id"] == product_id:
                new_qty = item["quantity"] - 1
                await db.update_cart_item_quantity(user_id, product_id, new_qty)
                break
        await refresh_cart(query, user_id)
    
    elif data.startswith("cart_plus_"):
        product_id = data[10:]
        cart = await db.get_user_cart(user_id)
        for item in cart:
            if item["product_id"] == product_id:
                new_qty = item["quantity"] + 1
                await db.update_cart_item_quantity(user_id, product_id, new_qty)
                break
        await refresh_cart(query, user_id)
    
    elif data.startswith("cart_remove_"):
        product_id = data[12:]
        await db.update_cart_item_quantity(user_id, product_id, 0)
        await query.answer("✅ Товар удалён из корзины")
        await refresh_cart(query, user_id)
    
    elif data == "cart_clear":
        await db.clear_cart(user_id)
        await query.message.edit_text(
            "🛒 *Корзина очищена*",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "checkout":
        cart = await db.get_user_cart(user_id)
        if not cart:
            await query.answer("Корзина пуста!", show_alert=True)
            return
        
        context.user_data["checkout_cart"] = cart
        
        keyboard = [
            [InlineKeyboardButton("🏃 Самовывоз (бесплатно)", callback_data="delivery_pickup")],
            [InlineKeyboardButton(f"🚗 Доставка (+{DELIVERY_COST:.2f} BYN)", callback_data="delivery_delivery")],
            [InlineKeyboardButton("❌ Отмена", callback_data="checkout_cancel")]
        ]
        
        await query.message.edit_text(
            "🚚 *Выберите способ получения:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_DELIVERY_TYPE


async def refresh_cart(query, user_id: int):
    """Refresh cart display"""
    cart = await db.get_user_cart(user_id)
    
    if not cart:
        await query.message.edit_text(
            "🛒 *Ваша корзина пуста*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "🛒 *Ваша корзина:*\n\n"
    total = 0
    
    keyboard = []
    for i, item in enumerate(cart):
        item_total = item["price"] * item["quantity"]
        total += item_total
        text += f"{i+1}. {item['product_name']}\n"
        text += f"   {item['quantity']} x {item['price']:.2f} = *{item_total:.2f} BYN*\n\n"
        
        keyboard.append([
            InlineKeyboardButton("➖", callback_data=f"cart_minus_{item['product_id']}"),
            InlineKeyboardButton(f"{item['product_name'][:15]}... ({item['quantity']})", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"cart_plus_{item['product_id']}"),
            InlineKeyboardButton("🗑", callback_data=f"cart_remove_{item['product_id']}")
        ])
    
    text += f"━━━━━━━━━━━━━━━\n*Итого: {total:.2f} BYN*"
    
    keyboard.append([InlineKeyboardButton("🗑 Очистить корзину", callback_data="cart_clear")])
    keyboard.append([InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")])
    
    await query.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def delivery_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delivery type selection"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "checkout_cancel":
        await query.message.edit_text("❌ *Оформление отменено*", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    
    if data == "delivery_pickup":
        context.user_data["delivery_type"] = "pickup"
        context.user_data["delivery_cost"] = 0
        context.user_data["address"] = PICKUP_ADDRESS
        
        await query.message.edit_text(
            f"🏃 *Самовывоз*\n\n📍 Адрес: {PICKUP_ADDRESS}\n\n✏️ Введите ваше имя:",
            parse_mode=ParseMode.MARKDOWN
        )
        return WAITING_NAME
    
    elif data == "delivery_delivery":
        context.user_data["delivery_type"] = "delivery"
        context.user_data["delivery_cost"] = DELIVERY_COST
        
        await query.message.edit_text(
            "🚗 *Доставка*\n\n📍 Введите адрес доставки:",
            parse_mode=ParseMode.MARKDOWN
        )
        return WAITING_ADDRESS


async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive delivery address"""
    context.user_data["address"] = update.message.text
    
    await update.message.reply_text(
        "✏️ Введите ваше имя:",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive customer name"""
    context.user_data["customer_name"] = update.message.text
    
    keyboard = [[KeyboardButton("📱 Отправить номер телефона", request_contact=True)]]
    
    await update.message.reply_text(
        "📱 Отправьте ваш номер телефона или введите вручную:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return WAITING_PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive phone number"""
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text
    
    context.user_data["phone"] = phone
    await db.update_user_phone(update.effective_user.id, phone)
    
    keyboard = [
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip_comment")],
    ]
    
    await update.message.reply_text(
        "💬 Добавьте комментарий к заказу (или нажмите пропустить):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_COMMENT


async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive order comment"""
    context.user_data["comment"] = update.message.text
    return await show_order_confirmation(update, context)


async def skip_comment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip comment"""
    query = update.callback_query
    await query.answer()
    
    context.user_data["comment"] = None
    return await show_order_confirmation_query(query, context)


async def show_order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show order confirmation"""
    cart = context.user_data.get("checkout_cart", [])
    delivery_type = context.user_data.get("delivery_type")
    delivery_cost = context.user_data.get("delivery_cost", 0)
    address = context.user_data.get("address")
    customer_name = context.user_data.get("customer_name")
    phone = context.user_data.get("phone")
    comment = context.user_data.get("comment")
    
    total = sum(item["price"] * item["quantity"] for item in cart)
    final_total = total + delivery_cost
    
    text = "📋 *Подтверждение заказа:*\n\n"
    text += "*Товары:*\n"
    for item in cart:
        text += f"• {item['product_name']} x{item['quantity']} = {item['price'] * item['quantity']:.2f} BYN\n"
    
    text += f"\n━━━━━━━━━━━━━━━\n"
    text += f"*Сумма товаров:* {total:.2f} BYN\n"
    
    if delivery_type == "delivery":
        text += f"*Доставка:* {delivery_cost:.2f} BYN\n"
    else:
        text += f"*Самовывоз:* бесплатно\n"
    
    text += f"*ИТОГО:* {final_total:.2f} BYN\n"
    text += f"\n━━━━━━━━━━━━━━━\n"
    text += f"👤 *Имя:* {customer_name}\n"
    text += f"📱 *Телефон:* {phone}\n"
    text += f"📍 *Адрес:* {address}\n"
    
    if comment:
        text += f"💬 *Комментарий:* {comment}\n"
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_order")]
    ]
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_ORDER


async def show_order_confirmation_query(query, context: ContextTypes.DEFAULT_TYPE):
    """Show order confirmation from callback query"""
    cart = context.user_data.get("checkout_cart", [])
    delivery_type = context.user_data.get("delivery_type")
    delivery_cost = context.user_data.get("delivery_cost", 0)
    address = context.user_data.get("address")
    customer_name = context.user_data.get("customer_name")
    phone = context.user_data.get("phone")
    comment = context.user_data.get("comment")
    
    total = sum(item["price"] * item["quantity"] for item in cart)
    final_total = total + delivery_cost
    
    text = "📋 *Подтверждение заказа:*\n\n"
    text += "*Товары:*\n"
    for item in cart:
        text += f"• {item['product_name']} x{item['quantity']} = {item['price'] * item['quantity']:.2f} BYN\n"
    
    text += f"\n━━━━━━━━━━━━━━━\n"
    text += f"*Сумма товаров:* {total:.2f} BYN\n"
    
    if delivery_type == "delivery":
        text += f"*Доставка:* {delivery_cost:.2f} BYN\n"
    else:
        text += f"*Самовывоз:* бесплатно\n"
    
    text += f"*ИТОГО:* {final_total:.2f} BYN\n"
    text += f"\n━━━━━━━━━━━━━━━\n"
    text += f"👤 *Имя:* {customer_name}\n"
    text += f"📱 *Телефон:* {phone}\n"
    text += f"📍 *Адрес:* {address}\n"
    
    if comment:
        text += f"💬 *Комментарий:* {comment}\n"
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_order")]
    ]
    
    await query.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_ORDER


async def confirm_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and create order"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    if data == "cancel_order":
        await query.message.edit_text("❌ *Заказ отменён*", parse_mode=ParseMode.MARKDOWN)
        # Restore main keyboard
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    cart = context.user_data.get("checkout_cart", [])
    delivery_type = context.user_data.get("delivery_type")
    delivery_cost = context.user_data.get("delivery_cost", 0)
    address = context.user_data.get("address")
    customer_name = context.user_data.get("customer_name")
    phone = context.user_data.get("phone")
    comment = context.user_data.get("comment")
    
    total = sum(item["price"] * item["quantity"] for item in cart)
    
    # Create order
    order = await db.create_order(
        user_telegram_id=user.id,
        user_name=customer_name,
        phone=phone,
        items=cart,
        total=total,
        delivery_type=delivery_type,
        delivery_cost=delivery_cost,
        address=address,
        comment=comment
    )
    
    # Clear cart
    await db.clear_cart(user.id)
    
    # Send confirmation to user
    await query.message.edit_text(
        f"✅ *Заказ #{order['order_number']} успешно оформлен!*\n\n"
        f"Ожидайте звонка для подтверждения.\n"
        f"Спасибо за заказ! 🍣",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Restore main keyboard
    await query.message.reply_text(
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    
    # Notify receivers
    await notify_new_order(context.bot, order, customer_name, phone, address, comment, delivery_type, delivery_cost)
    
    return ConversationHandler.END


async def notify_new_order(bot, order: dict, customer_name: str, phone: str, address: str, comment: str, delivery_type: str, delivery_cost: float):
    """Notify admins about new order"""
    receivers = await db.get_notification_receivers()
    
    total = sum(item["price"] * item["quantity"] for item in order["items"])
    final_total = total + delivery_cost
    
    text = f"🆕 *Новый заказ #{order['order_number']}!*\n\n"
    text += "*Товары:*\n"
    for item in order["items"]:
        text += f"• {item['product_name']} x{item['quantity']} = {item['price'] * item['quantity']:.2f} BYN\n"
    
    text += f"\n━━━━━━━━━━━━━━━\n"
    text += f"*Сумма:* {total:.2f} BYN\n"
    
    if delivery_type == "delivery":
        text += f"*Доставка:* {delivery_cost:.2f} BYN\n"
        text += f"*Тип:* 🚗 Доставка\n"
    else:
        text += f"*Тип:* 🏃 Самовывоз\n"
    
    text += f"*ИТОГО:* {final_total:.2f} BYN\n"
    text += f"\n━━━━━━━━━━━━━━━\n"
    text += f"👤 *Клиент:* {customer_name}\n"
    text += f"📱 *Телефон:* {phone}\n"
    text += f"📍 *Адрес:* {address}\n"
    
    if comment:
        text += f"💬 *Комментарий:* {comment}\n"
    
    for receiver in receivers:
        try:
            await bot.send_message(
                chat_id=receiver["telegram_id"],
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to notify receiver {receiver['telegram_id']}: {e}")


async def show_order_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's order history"""
    user_id = update.effective_user.id
    orders = await db.get_user_orders(user_id)
    
    if not orders:
        await update.message.reply_text(
            "📋 *История заказов*\n\nУ вас пока нет заказов.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "📋 *История заказов:*\n\n"
    
    for order in orders[:10]:  # Last 10 orders
        total = order["total"] + order.get("delivery_cost", 0)
        status_emoji = {
            "new": "🆕",
            "confirmed": "✅",
            "preparing": "👨‍🍳",
            "delivering": "🚗",
            "completed": "✔️",
            "cancelled": "❌"
        }.get(order["status"], "❓")
        
        text += f"*Заказ #{order['order_number']}* {status_emoji}\n"
        text += f"💰 {total:.2f} BYN\n"
        
        # Parse date
        created_at = order.get("created_at", "")
        if isinstance(created_at, str):
            text += f"📅 {created_at[:10]}\n"
        
        text += "\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show about information"""
    await update.message.reply_text(ABOUT_MESSAGE, parse_mode=ParseMode.MARKDOWN)


# Admin handlers
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel command"""
    user_id = update.effective_user.id
    
    if not await db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    await update.message.reply_text(
        "🔧 *Панель администратора*\n\nВыберите действие:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_admin_keyboard()
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not await db.is_admin(user_id):
        await query.message.edit_text("❌ У вас нет прав администратора.")
        return
    
    data = query.data
    
    if data == "admin_close":
        await query.message.delete()
        return
    
    if data == "admin_admins":
        admins = await db.get_all_admins()
        text = "👥 *Администраторы:*\n\n"
        for admin in admins:
            name = admin.get("first_name") or admin.get("username") or str(admin["telegram_id"])
            text += f"• {name} (ID: {admin['telegram_id']})\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data="admin_add_admin")],
            [InlineKeyboardButton("➖ Удалить", callback_data="admin_del_admin")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_receivers":
        receivers = await db.get_notification_receivers()
        text = "🔔 *Получатели уведомлений:*\n\n"
        for recv in receivers:
            name = recv.get("first_name") or recv.get("username") or str(recv["telegram_id"])
            text += f"• {name} (ID: {recv['telegram_id']})\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data="admin_add_receiver")],
            [InlineKeyboardButton("➖ Удалить", callback_data="admin_del_receiver")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_categories":
        categories = await db.get_all_categories()
        text = "📁 *Категории:*\n\n"
        
        main_cats = [c for c in categories if c.get("parent_id") is None]
        for cat in main_cats:
            text += f"📂 *{cat['name']}*\n"
            subcats = [c for c in categories if c.get("parent_id") == cat["id"]]
            for subcat in subcats:
                text += f"  └ {subcat['name']}\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить категорию", callback_data="admin_add_category")],
            [InlineKeyboardButton("➕ Добавить подкатегорию", callback_data="admin_add_subcategory")],
            [InlineKeyboardButton("✏️ Редактировать", callback_data="admin_edit_category")],
            [InlineKeyboardButton("🗑 Удалить", callback_data="admin_delete_category")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_products":
        keyboard = [
            [InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")],
            [InlineKeyboardButton("✏️ Редактировать товар", callback_data="admin_edit_product")],
            [InlineKeyboardButton("🗑 Удалить товар", callback_data="admin_delete_product")],
            [InlineKeyboardButton("📋 Список товаров", callback_data="admin_list_products")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            "📦 *Управление товарами:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_broadcast":
        await query.message.edit_text(
            "📢 *Рассылка*\n\nВведите сообщение для рассылки всем подписчикам:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_BROADCAST_MESSAGE
    
    elif data == "admin_back":
        await query.message.edit_text(
            "🔧 *Панель администратора*\n\nВыберите действие:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_keyboard()
        )
    
    elif data == "admin_add_admin":
        await query.message.edit_text(
            "➕ *Добавление администратора*\n\nВведите Telegram ID нового администратора:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_ADD_ADMIN
    
    elif data == "admin_del_admin":
        admins = await db.get_all_admins()
        keyboard = []
        for admin in admins:
            name = admin.get("first_name") or admin.get("username") or str(admin["telegram_id"])
            keyboard.append([InlineKeyboardButton(
                f"❌ {name}",
                callback_data=f"remove_admin_{admin['telegram_id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_admins")])
        
        await query.message.edit_text(
            "➖ *Удаление администратора*\n\nВыберите администратора для удаления:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("remove_admin_"):
        admin_id = int(data[13:])
        if admin_id == user_id:
            await query.answer("Нельзя удалить себя!", show_alert=True)
            return
        await db.remove_admin(admin_id)
        await query.answer("✅ Администратор удалён")
        # Refresh admin list
        await admin_callback(update, context)
    
    elif data == "admin_add_receiver":
        await query.message.edit_text(
            "➕ *Добавление получателя*\n\nВведите Telegram ID:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_ADD_RECEIVER
    
    elif data == "admin_del_receiver":
        receivers = await db.get_notification_receivers()
        keyboard = []
        for recv in receivers:
            name = recv.get("first_name") or recv.get("username") or str(recv["telegram_id"])
            keyboard.append([InlineKeyboardButton(
                f"❌ {name}",
                callback_data=f"remove_receiver_{recv['telegram_id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_receivers")])
        
        await query.message.edit_text(
            "➖ *Удаление получателя*\n\nВыберите для удаления:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("remove_receiver_"):
        recv_id = int(data[16:])
        await db.remove_notification_receiver(recv_id)
        await query.answer("✅ Получатель удалён")
        await admin_callback(update, context)
    
    elif data == "admin_add_category":
        await query.message.edit_text(
            "➕ *Добавление категории*\n\nВведите название новой категории:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_ADD_CATEGORY
    
    elif data == "admin_add_subcategory":
        categories = await db.get_main_categories()
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(
                cat["name"],
                callback_data=f"subcat_parent_{cat['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_categories")])
        
        await query.message.edit_text(
            "➕ *Добавление подкатегории*\n\nВыберите родительскую категорию:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("subcat_parent_"):
        parent_id = data[14:]
        context.user_data["subcat_parent_id"] = parent_id
        await query.message.edit_text(
            "➕ *Добавление подкатегории*\n\nВведите название подкатегории:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_ADD_SUBCATEGORY_NAME
    
    elif data == "admin_edit_category":
        categories = await db.get_all_categories()
        keyboard = []
        for cat in categories:
            prefix = "  └ " if cat.get("parent_id") else "📂 "
            keyboard.append([InlineKeyboardButton(
                f"{prefix}{cat['name']}",
                callback_data=f"edit_cat_{cat['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_categories")])
        
        await query.message.edit_text(
            "✏️ *Редактирование категории*\n\nВыберите категорию:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("edit_cat_"):
        cat_id = data[9:]
        context.user_data["edit_category_id"] = cat_id
        await query.message.edit_text(
            "✏️ *Редактирование категории*\n\nВведите новое название:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_EDIT_CATEGORY_NAME
    
    elif data == "admin_delete_category":
        categories = await db.get_all_categories()
        keyboard = []
        for cat in categories:
            prefix = "  └ " if cat.get("parent_id") else "📂 "
            keyboard.append([InlineKeyboardButton(
                f"🗑 {prefix}{cat['name']}",
                callback_data=f"del_cat_{cat['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_categories")])
        
        await query.message.edit_text(
            "🗑 *Удаление категории*\n\n⚠️ Все товары в категории будут удалены!\n\nВыберите категорию:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("del_cat_"):
        cat_id = data[8:]
        await db.delete_category(cat_id)
        await query.answer("✅ Категория удалена")
        # Go back to categories
        context.user_data["callback_data"] = "admin_categories"
        await admin_callback(update, context)
    
    elif data == "admin_add_product":
        categories = await db.get_all_categories()
        keyboard = []
        # Show only categories that don't have subcategories (leaf categories)
        for cat in categories:
            subcats = await db.get_subcategories(cat["id"])
            if not subcats:
                prefix = "  └ " if cat.get("parent_id") else "📂 "
                keyboard.append([InlineKeyboardButton(
                    f"{prefix}{cat['name']}",
                    callback_data=f"add_prod_cat_{cat['id']}"
                )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_products")])
        
        await query.message.edit_text(
            "➕ *Добавление товара*\n\nВыберите категорию:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("add_prod_cat_"):
        cat_id = data[13:]
        context.user_data["new_product_category"] = cat_id
        await query.message.edit_text(
            "➕ *Добавление товара*\n\nВведите название товара:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_ADD_PRODUCT_NAME
    
    elif data == "admin_list_products":
        products = await db.get_all_products()
        text = "📦 *Список товаров:*\n\n"
        for prod in products[:20]:
            status = "✅" if prod.get("is_active", True) else "❌"
            text += f"{status} {prod['name']} - {prod['price']:.2f} BYN\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_products")]]
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_edit_product":
        products = await db.get_all_products()
        keyboard = []
        for prod in products[:15]:
            keyboard.append([InlineKeyboardButton(
                f"✏️ {prod['name']}",
                callback_data=f"edit_prod_{prod['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_products")])
        
        await query.message.edit_text(
            "✏️ *Редактирование товара*\n\nВыберите товар:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("edit_prod_field_"):
        field = data[16:]
        context.user_data["edit_product_field"] = field
        
        field_names = {
            "name": "название",
            "description": "описание",
            "price": "цену (только число)",
            "image": "URL изображения"
        }
        
        await query.message.edit_text(
            f"✏️ Введите новое {field_names.get(field, field)}:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_EDIT_PRODUCT_VALUE
    
    elif data.startswith("edit_prod_"):
        prod_id = data[10:]
        context.user_data["edit_product_id"] = prod_id
        product = await db.get_product_by_id(prod_id)
        
        if not product:
            await query.answer("❌ Товар не найден", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("📝 Название", callback_data="edit_prod_field_name")],
            [InlineKeyboardButton("📄 Описание", callback_data="edit_prod_field_description")],
            [InlineKeyboardButton("💰 Цена", callback_data="edit_prod_field_price")],
            [InlineKeyboardButton("🖼 Изображение", callback_data="edit_prod_field_image")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_edit_product")]
        ]
        
        await query.message.edit_text(
            f"✏️ *Редактирование товара*\n\n"
            f"*{product['name']}*\n"
            f"📄 {product['description']}\n"
            f"💰 {product['price']:.2f} BYN\n\n"
            f"Выберите поле для редактирования:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_delete_product":
        products = await db.get_all_products()
        keyboard = []
        for prod in products[:15]:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {prod['name']}",
                callback_data=f"del_prod_{prod['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_products")])
        
        await query.message.edit_text(
            "🗑 *Удаление товара*\n\nВыберите товар для удаления:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("del_prod_"):
        prod_id = data[9:]
        await db.delete_product(prod_id)
        await query.answer("✅ Товар удалён")
        context.user_data["callback_data"] = "admin_products"
        await admin_callback(update, context)


async def admin_add_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding new admin"""
    try:
        new_admin_id = int(update.message.text)
        result = await db.add_admin(new_admin_id, update.effective_user.id)
        if result:
            await update.message.reply_text(
                f"✅ Администратор с ID {new_admin_id} добавлен!",
                reply_markup=get_admin_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Этот пользователь уже администратор",
                reply_markup=get_admin_keyboard()
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат ID. Введите числовой Telegram ID.",
            reply_markup=get_admin_keyboard()
        )
    return ConversationHandler.END


async def admin_add_receiver_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding notification receiver"""
    try:
        recv_id = int(update.message.text)
        result = await db.add_notification_receiver(recv_id, update.effective_user.id)
        if result:
            await update.message.reply_text(
                f"✅ Получатель с ID {recv_id} добавлен!",
                reply_markup=get_admin_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Этот пользователь уже в списке получателей",
                reply_markup=get_admin_keyboard()
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат ID",
            reply_markup=get_admin_keyboard()
        )
    return ConversationHandler.END


async def admin_add_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding new category"""
    name = update.message.text
    await db.create_category(name)
    await update.message.reply_text(
        f"✅ Категория '{name}' создана!",
        reply_markup=get_admin_keyboard()
    )
    return ConversationHandler.END


async def admin_add_subcategory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding new subcategory"""
    name = update.message.text
    parent_id = context.user_data.get("subcat_parent_id")
    await db.create_category(name, parent_id=parent_id)
    await update.message.reply_text(
        f"✅ Подкатегория '{name}' создана!",
        reply_markup=get_admin_keyboard()
    )
    return ConversationHandler.END


async def admin_edit_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing category"""
    new_name = update.message.text
    cat_id = context.user_data.get("edit_category_id")
    await db.update_category(cat_id, name=new_name)
    await update.message.reply_text(
        f"✅ Категория переименована в '{new_name}'!",
        reply_markup=get_admin_keyboard()
    )
    return ConversationHandler.END


async def admin_add_product_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product name input"""
    context.user_data["new_product_name"] = update.message.text
    await update.message.reply_text("📄 Введите описание товара:")
    return ADMIN_ADD_PRODUCT_DESC


async def admin_add_product_desc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product description input"""
    context.user_data["new_product_desc"] = update.message.text
    await update.message.reply_text("💰 Введите цену (только число, например 25.90):")
    return ADMIN_ADD_PRODUCT_PRICE


async def admin_add_product_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product price input"""
    try:
        price = float(update.message.text.replace(",", "."))
        context.user_data["new_product_price"] = price
        
        keyboard = [[InlineKeyboardButton("⏭ Пропустить", callback_data="skip_product_image")]]
        await update.message.reply_text(
            "🖼 Отправьте фото товара или URL изображения (или нажмите пропустить):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_ADD_PRODUCT_IMAGE
    except ValueError:
        await update.message.reply_text("❌ Неверный формат цены. Введите число:")
        return ADMIN_ADD_PRODUCT_PRICE


async def admin_add_product_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product image input - text URL"""
    image_url = update.message.text
    await create_product_from_context(update, context, image_url)
    return ConversationHandler.END


async def admin_add_product_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product image input - photo file"""
    photo = update.message.photo[-1]  # Get largest photo
    file = await photo.get_file()
    image_url = file.file_path  # Telegram file URL
    await create_product_from_context(update, context, image_url)
    return ConversationHandler.END


async def skip_product_image_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip product image"""
    query = update.callback_query
    await query.answer()
    await create_product_from_context(query, context, None)
    return ConversationHandler.END


async def create_product_from_context(update_or_query, context: ContextTypes.DEFAULT_TYPE, image_url: str):
    """Create product from collected data"""
    name = context.user_data.get("new_product_name")
    desc = context.user_data.get("new_product_desc")
    price = context.user_data.get("new_product_price")
    cat_id = context.user_data.get("new_product_category")
    
    await db.create_product(name, desc, price, cat_id, image_url)
    
    if hasattr(update_or_query, "message"):
        await update_or_query.message.reply_text(
            f"✅ Товар '{name}' создан!",
            reply_markup=get_admin_keyboard()
        )
    else:
        await update_or_query.message.edit_text(
            f"✅ Товар '{name}' создан!"
        )
        await update_or_query.message.reply_text(
            "🔧 Панель администратора",
            reply_markup=get_admin_keyboard()
        )


async def admin_edit_product_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product field edit - text"""
    value = update.message.text
    prod_id = context.user_data.get("edit_product_id")
    field = context.user_data.get("edit_product_field")
    
    if field == "price":
        try:
            value = float(value.replace(",", "."))
        except ValueError:
            await update.message.reply_text("❌ Неверный формат цены")
            return ConversationHandler.END
    
    if field == "image":
        field = "image_url"
    
    await db.update_product(prod_id, **{field: value})
    await update.message.reply_text(
        f"✅ Товар обновлён!",
        reply_markup=get_admin_keyboard()
    )
    return ConversationHandler.END


async def admin_edit_product_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product image edit - photo file"""
    prod_id = context.user_data.get("edit_product_id")
    field = context.user_data.get("edit_product_field")
    
    if field != "image":
        await update.message.reply_text("❌ Ожидался текст, а не фото")
        return ConversationHandler.END
    
    photo = update.message.photo[-1]  # Get largest photo
    file = await photo.get_file()
    image_url = file.file_path  # Telegram file URL
    
    await db.update_product(prod_id, image_url=image_url)
    await update.message.reply_text(
        f"✅ Изображение товара обновлено!",
        reply_markup=get_admin_keyboard()
    )
    return ConversationHandler.END


async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message"""
    message = update.message.text
    subscribers = await db.get_all_subscribers()
    
    success_count = 0
    for sub in subscribers:
        try:
            await context.bot.send_message(
                chat_id=sub["telegram_id"],
                text=f"📢 *Новость от SushiMart:*\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {sub['telegram_id']}: {e}")
    
    await update.message.reply_text(
        f"✅ Сообщение отправлено {success_count} из {len(subscribers)} подписчиков!",
        reply_markup=get_admin_keyboard()
    )
    return ConversationHandler.END


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from main keyboard"""
    text = update.message.text
    
    if text == "🍣 Меню":
        await show_menu(update, context)
    elif text == "🛒 Корзина":
        await show_cart(update, context)
    elif text == "📋 История заказов":
        await show_order_history(update, context)
    elif text == "ℹ️ О нас":
        await show_about(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    await update.message.reply_text(
        "❌ Операция отменена",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


def main():
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Checkout conversation handler
    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cart_callback, pattern="^checkout$")],
        states={
            WAITING_DELIVERY_TYPE: [
                CallbackQueryHandler(delivery_type_callback, pattern="^(delivery_|checkout_)")
            ],
            WAITING_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)
            ],
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)
            ],
            WAITING_PHONE: [
                MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), receive_phone)
            ],
            WAITING_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment),
                CallbackQueryHandler(skip_comment_callback, pattern="^skip_comment$")
            ],
            CONFIRM_ORDER: [
                CallbackQueryHandler(confirm_order_callback, pattern="^(confirm_order|cancel_order)$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )
    
    # Admin conversation handler
    admin_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_command),
            CallbackQueryHandler(admin_callback, pattern="^admin_"),
            CallbackQueryHandler(admin_callback, pattern="^edit_prod_field_"),
            CallbackQueryHandler(admin_callback, pattern="^edit_prod_"),
            CallbackQueryHandler(admin_callback, pattern="^del_prod_"),
            CallbackQueryHandler(admin_callback, pattern="^edit_cat_"),
            CallbackQueryHandler(admin_callback, pattern="^del_cat_"),
            CallbackQueryHandler(admin_callback, pattern="^remove_"),
            CallbackQueryHandler(admin_callback, pattern="^subcat_parent_"),
            CallbackQueryHandler(admin_callback, pattern="^add_prod_cat_"),
        ],
        states={
            ADMIN_ADD_ADMIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_admin_handler)
            ],
            ADMIN_ADD_RECEIVER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_receiver_handler)
            ],
            ADMIN_ADD_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_category_handler)
            ],
            ADMIN_ADD_SUBCATEGORY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_subcategory_handler)
            ],
            ADMIN_EDIT_CATEGORY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_category_handler)
            ],
            ADMIN_ADD_PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_product_name_handler)
            ],
            ADMIN_ADD_PRODUCT_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_product_desc_handler)
            ],
            ADMIN_ADD_PRODUCT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_product_price_handler)
            ],
            ADMIN_ADD_PRODUCT_IMAGE: [
                MessageHandler(filters.PHOTO, admin_add_product_photo_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_product_image_handler),
                CallbackQueryHandler(skip_product_image_callback, pattern="^skip_product_image$")
            ],
            ADMIN_EDIT_PRODUCT_VALUE: [
                MessageHandler(filters.PHOTO, admin_edit_product_photo_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_product_value_handler)
            ],
            ADMIN_BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(admin_callback, pattern="^admin_")
        ],
        per_message=False
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(checkout_conv)
    application.add_handler(admin_conv)
    application.add_handler(CallbackQueryHandler(category_callback, pattern="^(cat_|back_)"))
    application.add_handler(CallbackQueryHandler(product_callback, pattern="^(qty_|add_cart_|prod_|noop)"))
    application.add_handler(CallbackQueryHandler(cart_callback, pattern="^cart_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Initialize test data on startup
    async def post_init(app):
        await db.init_test_data()
        logger.info("✅ Test data initialized")
    
    application.post_init = post_init
    
    # Run the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Initialize test data
    import asyncio
    asyncio.get_event_loop().run_until_complete(db.init_test_data())
    main()
