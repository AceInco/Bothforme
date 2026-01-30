"""
Database operations for the Sushi Telegram Bot
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Collections
users_collection = db.users
products_collection = db.products
categories_collection = db.categories
orders_collection = db.orders
admins_collection = db.admins
notification_receivers_collection = db.notification_receivers
counters_collection = db.counters


async def get_next_order_number() -> int:
    """Get next order number"""
    result = await counters_collection.find_one_and_update(
        {"_id": "order_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result["seq"]


# User operations
async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Dict:
    """Get existing user or create new one"""
    user = await users_collection.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user:
        from models import User
        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        user_dict = new_user.model_dump()
        user_dict['created_at'] = user_dict['created_at'].isoformat()
        await users_collection.insert_one(user_dict)
        return new_user.model_dump()
    return user


async def get_user_cart(telegram_id: int) -> List[Dict]:
    """Get user's cart"""
    user = await users_collection.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if user:
        return user.get("cart", [])
    return []


async def add_to_cart(telegram_id: int, product_id: str, product_name: str, quantity: int, price: float):
    """Add item to cart or update quantity"""
    user = await users_collection.find_one({"telegram_id": telegram_id})
    if user:
        cart = user.get("cart", [])
        # Check if product already in cart
        for item in cart:
            if item["product_id"] == product_id:
                item["quantity"] += quantity
                await users_collection.update_one(
                    {"telegram_id": telegram_id},
                    {"$set": {"cart": cart}}
                )
                return
        # Add new item
        cart.append({
            "product_id": product_id,
            "product_name": product_name,
            "quantity": quantity,
            "price": price
        })
        await users_collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"cart": cart}}
        )


async def update_cart_item_quantity(telegram_id: int, product_id: str, quantity: int):
    """Update cart item quantity"""
    user = await users_collection.find_one({"telegram_id": telegram_id})
    if user:
        cart = user.get("cart", [])
        for item in cart:
            if item["product_id"] == product_id:
                if quantity <= 0:
                    cart.remove(item)
                else:
                    item["quantity"] = quantity
                break
        await users_collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"cart": cart}}
        )


async def clear_cart(telegram_id: int):
    """Clear user's cart"""
    await users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"cart": []}}
    )


async def update_user_phone(telegram_id: int, phone: str):
    """Update user's phone"""
    await users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"phone": phone}}
    )


# Category operations
async def get_all_categories() -> List[Dict]:
    """Get all categories"""
    return await categories_collection.find({}, {"_id": 0}).sort("order", 1).to_list(100)


async def get_main_categories() -> List[Dict]:
    """Get main categories (without parent)"""
    return await categories_collection.find({"parent_id": None}, {"_id": 0}).sort("order", 1).to_list(100)


async def get_subcategories(parent_id: str) -> List[Dict]:
    """Get subcategories by parent_id"""
    return await categories_collection.find({"parent_id": parent_id}, {"_id": 0}).sort("order", 1).to_list(100)


async def get_category_by_id(category_id: str) -> Optional[Dict]:
    """Get category by ID"""
    return await categories_collection.find_one({"id": category_id}, {"_id": 0})


async def create_category(name: str, parent_id: str = None, order: int = 0) -> Dict:
    """Create new category"""
    from models import Category
    category = Category(name=name, parent_id=parent_id, order=order)
    cat_dict = category.model_dump()
    cat_dict['created_at'] = cat_dict['created_at'].isoformat()
    await categories_collection.insert_one(cat_dict)
    return category.model_dump()


async def update_category(category_id: str, name: str = None, order: int = None) -> bool:
    """Update category"""
    update_data = {}
    if name:
        update_data["name"] = name
    if order is not None:
        update_data["order"] = order
    if update_data:
        result = await categories_collection.update_one(
            {"id": category_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    return False


async def delete_category(category_id: str) -> bool:
    """Delete category and its subcategories"""
    # Delete subcategories first
    await categories_collection.delete_many({"parent_id": category_id})
    # Delete main category
    result = await categories_collection.delete_one({"id": category_id})
    # Delete products in this category
    await products_collection.delete_many({"category_id": category_id})
    return result.deleted_count > 0


# Product operations
async def get_products_by_category(category_id: str) -> List[Dict]:
    """Get products by category"""
    return await products_collection.find(
        {"category_id": category_id, "is_active": True}, 
        {"_id": 0}
    ).sort("order", 1).to_list(100)


async def get_product_by_id(product_id: str) -> Optional[Dict]:
    """Get product by ID"""
    return await products_collection.find_one({"id": product_id}, {"_id": 0})


async def create_product(name: str, description: str, price: float, category_id: str, image_url: str = None) -> Dict:
    """Create new product"""
    from models import Product
    product = Product(
        name=name,
        description=description,
        price=price,
        category_id=category_id,
        image_url=image_url
    )
    prod_dict = product.model_dump()
    prod_dict['created_at'] = prod_dict['created_at'].isoformat()
    await products_collection.insert_one(prod_dict)
    return product.model_dump()


async def update_product(product_id: str, **kwargs) -> bool:
    """Update product"""
    update_data = {k: v for k, v in kwargs.items() if v is not None}
    if update_data:
        result = await products_collection.update_one(
            {"id": product_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    return False


async def delete_product(product_id: str) -> bool:
    """Delete product"""
    result = await products_collection.delete_one({"id": product_id})
    return result.deleted_count > 0


async def get_all_products() -> List[Dict]:
    """Get all products"""
    return await products_collection.find({}, {"_id": 0}).to_list(1000)


# Order operations
async def create_order(
    user_telegram_id: int,
    user_name: str,
    phone: str,
    items: List[Dict],
    total: float,
    delivery_type: str,
    delivery_cost: float = 0.0,
    address: str = None,
    comment: str = None
) -> Dict:
    """Create new order"""
    from models import Order
    order_number = await get_next_order_number()
    order = Order(
        order_number=order_number,
        user_telegram_id=user_telegram_id,
        user_name=user_name,
        phone=phone,
        items=items,
        total=total,
        delivery_cost=delivery_cost,
        delivery_type=delivery_type,
        address=address,
        comment=comment
    )
    order_dict = order.model_dump()
    order_dict['created_at'] = order_dict['created_at'].isoformat()
    await orders_collection.insert_one(order_dict)
    return order.model_dump()


async def get_user_orders(telegram_id: int) -> List[Dict]:
    """Get user's orders"""
    return await orders_collection.find(
        {"user_telegram_id": telegram_id}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)


async def update_order_status(order_id: str, status: str) -> bool:
    """Update order status"""
    result = await orders_collection.update_one(
        {"id": order_id},
        {"$set": {"status": status}}
    )
    return result.modified_count > 0


# Admin operations
async def is_admin(telegram_id: int) -> bool:
    """Check if user is admin"""
    admin = await admins_collection.find_one({"telegram_id": telegram_id})
    return admin is not None


async def get_all_admins() -> List[Dict]:
    """Get all admins"""
    return await admins_collection.find({}, {"_id": 0}).to_list(100)


async def add_admin(telegram_id: int, added_by: int, username: str = None, first_name: str = None) -> Dict:
    """Add new admin"""
    from models import Admin
    # Check if already admin
    existing = await admins_collection.find_one({"telegram_id": telegram_id})
    if existing:
        return None
    admin = Admin(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        added_by=added_by
    )
    admin_dict = admin.model_dump()
    admin_dict['created_at'] = admin_dict['created_at'].isoformat()
    await admins_collection.insert_one(admin_dict)
    return admin.model_dump()


async def remove_admin(telegram_id: int) -> bool:
    """Remove admin"""
    result = await admins_collection.delete_one({"telegram_id": telegram_id})
    return result.deleted_count > 0


# Notification receivers operations
async def get_notification_receivers() -> List[Dict]:
    """Get all notification receivers"""
    return await notification_receivers_collection.find({}, {"_id": 0}).to_list(100)


async def add_notification_receiver(telegram_id: int, added_by: int, username: str = None, first_name: str = None) -> Dict:
    """Add notification receiver"""
    from models import NotificationReceiver
    existing = await notification_receivers_collection.find_one({"telegram_id": telegram_id})
    if existing:
        return None
    receiver = NotificationReceiver(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        added_by=added_by
    )
    recv_dict = receiver.model_dump()
    recv_dict['created_at'] = recv_dict['created_at'].isoformat()
    await notification_receivers_collection.insert_one(recv_dict)
    return receiver.model_dump()


async def remove_notification_receiver(telegram_id: int) -> bool:
    """Remove notification receiver"""
    result = await notification_receivers_collection.delete_one({"telegram_id": telegram_id})
    return result.deleted_count > 0


# All subscribers (users who started the bot)
async def get_all_subscribers() -> List[Dict]:
    """Get all users who started the bot"""
    return await users_collection.find({}, {"_id": 0, "telegram_id": 1}).to_list(10000)


# Initialize test data
async def init_test_data():
    """Initialize test categories and products"""
    # Check if data already exists
    existing_cats = await categories_collection.count_documents({})
    if existing_cats > 0:
        return
    
    # Main categories
    sushi_cat = await create_category("🍣 Суши", order=1)
    hot_cat = await create_category("🍲 Горячие блюда", order=2)
    sauces_cat = await create_category("🥫 Соусы", order=3)
    
    # Subcategories for Sushi
    usual_sushi = await create_category("Обычные", parent_id=sushi_cat["id"], order=1)
    baked_sushi = await create_category("Запечёные", parent_id=sushi_cat["id"], order=2)
    tempura_sushi = await create_category("Темпура", parent_id=sushi_cat["id"], order=3)
    
    # Products - Обычные суши
    await create_product(
        name="Филадельфия классик",
        description="Лосось, сливочный сыр, огурец, рис, нори. 8 шт.",
        price=24.90,
        category_id=usual_sushi["id"],
        image_url="https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=400"
    )
    await create_product(
        name="Калифорния с крабом",
        description="Краб, авокадо, огурец, икра тобико, рис. 8 шт.",
        price=22.50,
        category_id=usual_sushi["id"],
        image_url="https://images.unsplash.com/photo-1617196034796-73dfa7b1fd56?w=400"
    )
    
    # Products - Запечёные суши
    await create_product(
        name="Запечёный лосось",
        description="Лосось, сливочный сыр, соус спайси, рис, нори. 8 шт.",
        price=26.90,
        category_id=baked_sushi["id"],
        image_url="https://images.unsplash.com/photo-1611143669185-af224c5e3252?w=400"
    )
    await create_product(
        name="Запечёный угорь",
        description="Угорь, сливочный сыр, соус унаги, кунжут, рис. 8 шт.",
        price=29.90,
        category_id=baked_sushi["id"],
        image_url="https://images.unsplash.com/photo-1553621042-f6e147245754?w=400"
    )
    
    # Products - Темпура суши
    await create_product(
        name="Темпура с креветкой",
        description="Креветка в кляре, авокадо, сливочный сыр, рис. 8 шт.",
        price=27.50,
        category_id=tempura_sushi["id"],
        image_url="https://images.unsplash.com/photo-1559410545-0bdcd187e0a6?w=400"
    )
    await create_product(
        name="Темпура с лососем",
        description="Лосось в кляре, огурец, сливочный сыр, рис, нори. 8 шт.",
        price=25.90,
        category_id=tempura_sushi["id"],
        image_url="https://images.unsplash.com/photo-1534482421-64566f976cfa?w=400"
    )
    
    # Products - Горячие блюда
    await create_product(
        name="Вок с курицей",
        description="Лапша удон, курица, овощи, соус терияки. 350г",
        price=18.90,
        category_id=hot_cat["id"],
        image_url="https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400"
    )
    await create_product(
        name="Рис с морепродуктами",
        description="Рис, креветки, мидии, кальмары, овощи. 400г",
        price=21.50,
        category_id=hot_cat["id"],
        image_url="https://images.unsplash.com/photo-1512058564366-18510be2db19?w=400"
    )
    
    # Products - Соусы
    await create_product(
        name="Соевый соус",
        description="Классический соевый соус. 50мл",
        price=1.50,
        category_id=sauces_cat["id"],
        image_url="https://images.unsplash.com/photo-1585325701165-351af916fbb3?w=400"
    )
    await create_product(
        name="Соус спайси",
        description="Острый соус на основе майонеза. 50мл",
        price=2.00,
        category_id=sauces_cat["id"],
        image_url="https://images.unsplash.com/photo-1472476443507-c7a5948772fc?w=400"
    )
    
    # Add first admin
    await add_admin(1757549785, 1757549785, first_name="Первый админ")
    # Add first notification receiver
    await add_notification_receiver(1757549785, 1757549785, first_name="Первый админ")
