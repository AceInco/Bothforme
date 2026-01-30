#!/usr/bin/env python3
"""
Backend Testing for Telegram Sushi Bot
Tests all database operations and business logic
"""
import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

import database as db
from models import User, Category, Product, Order, Admin, NotificationReceiver

class TelegramBotTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.passed_tests = []

    def log_test(self, name, success, error_msg=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            self.passed_tests.append(name)
            print(f"✅ {name}")
        else:
            self.failed_tests.append({"test": name, "error": error_msg})
            print(f"❌ {name}: {error_msg}")

    async def test_database_connection(self):
        """Test MongoDB connection"""
        try:
            # Test connection by counting documents in any collection
            count = await db.users_collection.count_documents({})
            self.log_test("Database Connection", True)
            return True
        except Exception as e:
            self.log_test("Database Connection", False, str(e))
            return False

    async def test_init_test_data(self):
        """Test initialization of test data"""
        try:
            # Clear existing data first
            await db.categories_collection.delete_many({})
            await db.products_collection.delete_many({})
            await db.admins_collection.delete_many({})
            await db.notification_receivers_collection.delete_many({})
            
            # Initialize test data
            await db.init_test_data()
            
            # Verify categories (should be 6: 3 main + 3 subcategories)
            categories = await db.get_all_categories()
            if len(categories) != 6:
                self.log_test("Init Test Data - Categories Count", False, f"Expected 6 categories, got {len(categories)}")
                return False
            
            # Verify products (should be 10)
            products = await db.get_all_products()
            if len(products) != 10:
                self.log_test("Init Test Data - Products Count", False, f"Expected 10 products, got {len(products)}")
                return False
            
            # Verify admin was created
            admins = await db.get_all_admins()
            if len(admins) != 1 or admins[0]["telegram_id"] != 1757549785:
                self.log_test("Init Test Data - Admin Creation", False, f"Expected 1 admin with ID 1757549785")
                return False
            
            # Verify notification receiver was created
            receivers = await db.get_notification_receivers()
            if len(receivers) != 1 or receivers[0]["telegram_id"] != 1757549785:
                self.log_test("Init Test Data - Notification Receiver", False, f"Expected 1 receiver with ID 1757549785")
                return False
            
            self.log_test("Init Test Data", True)
            return True
        except Exception as e:
            self.log_test("Init Test Data", False, str(e))
            return False

    async def test_category_operations(self):
        """Test category CRUD operations"""
        try:
            # Test create category
            test_cat = await db.create_category("Test Category", order=99)
            if not test_cat or not test_cat.get("id"):
                self.log_test("Category Create", False, "Failed to create category")
                return False
            
            cat_id = test_cat["id"]
            
            # Test get category by ID
            retrieved_cat = await db.get_category_by_id(cat_id)
            if not retrieved_cat or retrieved_cat["name"] != "Test Category":
                self.log_test("Category Get by ID", False, "Failed to retrieve category")
                return False
            
            # Test update category
            updated = await db.update_category(cat_id, name="Updated Category", order=100)
            if not updated:
                self.log_test("Category Update", False, "Failed to update category")
                return False
            
            # Verify update
            updated_cat = await db.get_category_by_id(cat_id)
            if updated_cat["name"] != "Updated Category" or updated_cat["order"] != 100:
                self.log_test("Category Update Verification", False, "Category update not reflected")
                return False
            
            # Test subcategory creation
            subcat = await db.create_category("Test Subcategory", parent_id=cat_id, order=1)
            if not subcat or subcat["parent_id"] != cat_id:
                self.log_test("Subcategory Create", False, "Failed to create subcategory")
                return False
            
            # Test get subcategories
            subcats = await db.get_subcategories(cat_id)
            if len(subcats) != 1 or subcats[0]["name"] != "Test Subcategory":
                self.log_test("Get Subcategories", False, "Failed to retrieve subcategories")
                return False
            
            # Test delete category (should also delete subcategories)
            deleted = await db.delete_category(cat_id)
            if not deleted:
                self.log_test("Category Delete", False, "Failed to delete category")
                return False
            
            # Verify deletion
            deleted_cat = await db.get_category_by_id(cat_id)
            if deleted_cat is not None:
                self.log_test("Category Delete Verification", False, "Category still exists after deletion")
                return False
            
            self.log_test("Category CRUD Operations", True)
            return True
        except Exception as e:
            self.log_test("Category CRUD Operations", False, str(e))
            return False

    async def test_product_operations(self):
        """Test product CRUD operations"""
        try:
            # Get a category to use for testing
            categories = await db.get_all_categories()
            if not categories:
                self.log_test("Product Operations - No Categories", False, "No categories available for testing")
                return False
            
            cat_id = categories[0]["id"]
            
            # Test create product
            test_product = await db.create_product(
                name="Test Product",
                description="Test Description",
                price=15.99,
                category_id=cat_id,
                image_url="https://example.com/image.jpg"
            )
            if not test_product or not test_product.get("id"):
                self.log_test("Product Create", False, "Failed to create product")
                return False
            
            prod_id = test_product["id"]
            
            # Test get product by ID
            retrieved_prod = await db.get_product_by_id(prod_id)
            if not retrieved_prod or retrieved_prod["name"] != "Test Product":
                self.log_test("Product Get by ID", False, "Failed to retrieve product")
                return False
            
            # Test get products by category
            category_products = await db.get_products_by_category(cat_id)
            found_product = any(p["id"] == prod_id for p in category_products)
            if not found_product:
                self.log_test("Get Products by Category", False, "Product not found in category")
                return False
            
            # Test update product
            updated = await db.update_product(prod_id, name="Updated Product", price=19.99)
            if not updated:
                self.log_test("Product Update", False, "Failed to update product")
                return False
            
            # Verify update
            updated_prod = await db.get_product_by_id(prod_id)
            if updated_prod["name"] != "Updated Product" or updated_prod["price"] != 19.99:
                self.log_test("Product Update Verification", False, "Product update not reflected")
                return False
            
            # Test delete product
            deleted = await db.delete_product(prod_id)
            if not deleted:
                self.log_test("Product Delete", False, "Failed to delete product")
                return False
            
            # Verify deletion
            deleted_prod = await db.get_product_by_id(prod_id)
            if deleted_prod is not None:
                self.log_test("Product Delete Verification", False, "Product still exists after deletion")
                return False
            
            self.log_test("Product CRUD Operations", True)
            return True
        except Exception as e:
            self.log_test("Product CRUD Operations", False, str(e))
            return False

    async def test_user_operations(self):
        """Test user operations"""
        try:
            test_telegram_id = 123456789
            
            # Test get or create user (create)
            user = await db.get_or_create_user(
                telegram_id=test_telegram_id,
                username="testuser",
                first_name="Test",
                last_name="User"
            )
            if not user or user["telegram_id"] != test_telegram_id:
                self.log_test("User Create", False, "Failed to create user")
                return False
            
            # Test get or create user (get existing)
            existing_user = await db.get_or_create_user(telegram_id=test_telegram_id)
            if not existing_user or existing_user["telegram_id"] != test_telegram_id:
                self.log_test("User Get Existing", False, "Failed to get existing user")
                return False
            
            # Test update user phone
            await db.update_user_phone(test_telegram_id, "+375291234567")
            
            self.log_test("User Operations", True)
            return True
        except Exception as e:
            self.log_test("User Operations", False, str(e))
            return False

    async def test_cart_operations(self):
        """Test cart operations"""
        try:
            test_telegram_id = 123456789
            
            # Ensure user exists
            await db.get_or_create_user(telegram_id=test_telegram_id)
            
            # Get a product for testing
            products = await db.get_all_products()
            if not products:
                self.log_test("Cart Operations - No Products", False, "No products available for testing")
                return False
            
            product = products[0]
            
            # Test add to cart
            await db.add_to_cart(
                telegram_id=test_telegram_id,
                product_id=product["id"],
                product_name=product["name"],
                quantity=2,
                price=product["price"]
            )
            
            # Test get cart
            cart = await db.get_user_cart(test_telegram_id)
            if len(cart) != 1 or cart[0]["product_id"] != product["id"] or cart[0]["quantity"] != 2:
                self.log_test("Cart Add Item", False, "Failed to add item to cart")
                return False
            
            # Test add same product again (should update quantity)
            await db.add_to_cart(
                telegram_id=test_telegram_id,
                product_id=product["id"],
                product_name=product["name"],
                quantity=1,
                price=product["price"]
            )
            
            cart = await db.get_user_cart(test_telegram_id)
            if len(cart) != 1 or cart[0]["quantity"] != 3:
                self.log_test("Cart Update Quantity", False, "Failed to update cart item quantity")
                return False
            
            # Test update cart item quantity
            await db.update_cart_item_quantity(test_telegram_id, product["id"], 5)
            cart = await db.get_user_cart(test_telegram_id)
            if cart[0]["quantity"] != 5:
                self.log_test("Cart Update Item Quantity", False, "Failed to update item quantity")
                return False
            
            # Test remove item from cart (set quantity to 0)
            await db.update_cart_item_quantity(test_telegram_id, product["id"], 0)
            cart = await db.get_user_cart(test_telegram_id)
            if len(cart) != 0:
                self.log_test("Cart Remove Item", False, "Failed to remove item from cart")
                return False
            
            # Add item back for clear test
            await db.add_to_cart(
                telegram_id=test_telegram_id,
                product_id=product["id"],
                product_name=product["name"],
                quantity=1,
                price=product["price"]
            )
            
            # Test clear cart
            await db.clear_cart(test_telegram_id)
            cart = await db.get_user_cart(test_telegram_id)
            if len(cart) != 0:
                self.log_test("Cart Clear", False, "Failed to clear cart")
                return False
            
            self.log_test("Cart Operations", True)
            return True
        except Exception as e:
            self.log_test("Cart Operations", False, str(e))
            return False

    async def test_order_operations(self):
        """Test order operations and order number counter"""
        try:
            test_telegram_id = 123456789
            
            # Get a product for testing
            products = await db.get_all_products()
            if not products:
                self.log_test("Order Operations - No Products", False, "No products available for testing")
                return False
            
            product = products[0]
            cart_items = [{
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": 2,
                "price": product["price"]
            }]
            
            # Test create order and order number counter
            order1 = await db.create_order(
                user_telegram_id=test_telegram_id,
                user_name="Test User",
                phone="+375291234567",
                items=cart_items,
                total=product["price"] * 2,
                delivery_type="pickup",
                delivery_cost=0.0,
                address="Test Address",
                comment="Test comment"
            )
            
            if not order1 or not order1.get("order_number"):
                self.log_test("Order Create", False, "Failed to create order")
                return False
            
            # Test order number counter - create second order
            order2 = await db.create_order(
                user_telegram_id=test_telegram_id,
                user_name="Test User 2",
                phone="+375291234568",
                items=cart_items,
                total=product["price"] * 2,
                delivery_type="delivery",
                delivery_cost=4.0,
                address="Test Address 2"
            )
            
            if not order2 or order2["order_number"] != order1["order_number"] + 1:
                self.log_test("Order Number Counter", False, f"Order numbers not sequential: {order1['order_number']} -> {order2['order_number']}")
                return False
            
            # Test get user orders
            user_orders = await db.get_user_orders(test_telegram_id)
            if len(user_orders) != 2:
                self.log_test("Get User Orders", False, f"Expected 2 orders, got {len(user_orders)}")
                return False
            
            # Test update order status
            updated = await db.update_order_status(order1["id"], "confirmed")
            if not updated:
                self.log_test("Update Order Status", False, "Failed to update order status")
                return False
            
            self.log_test("Order Operations", True)
            return True
        except Exception as e:
            self.log_test("Order Operations", False, str(e))
            return False

    async def test_admin_operations(self):
        """Test admin operations"""
        try:
            test_admin_id = 987654321
            added_by_id = 1757549785  # First admin
            
            # Test is_admin (should be false initially)
            is_admin_before = await db.is_admin(test_admin_id)
            if is_admin_before:
                self.log_test("Is Admin - Before Add", False, "User should not be admin initially")
                return False
            
            # Test add admin
            admin = await db.add_admin(
                telegram_id=test_admin_id,
                added_by=added_by_id,
                username="testadmin",
                first_name="Test Admin"
            )
            if not admin or admin["telegram_id"] != test_admin_id:
                self.log_test("Add Admin", False, "Failed to add admin")
                return False
            
            # Test is_admin (should be true now)
            is_admin_after = await db.is_admin(test_admin_id)
            if not is_admin_after:
                self.log_test("Is Admin - After Add", False, "User should be admin after adding")
                return False
            
            # Test add duplicate admin (should return None)
            duplicate_admin = await db.add_admin(test_admin_id, added_by_id)
            if duplicate_admin is not None:
                self.log_test("Add Duplicate Admin", False, "Should not allow duplicate admin")
                return False
            
            # Test get all admins
            all_admins = await db.get_all_admins()
            admin_ids = [a["telegram_id"] for a in all_admins]
            if test_admin_id not in admin_ids:
                self.log_test("Get All Admins", False, "New admin not in admin list")
                return False
            
            # Test remove admin
            removed = await db.remove_admin(test_admin_id)
            if not removed:
                self.log_test("Remove Admin", False, "Failed to remove admin")
                return False
            
            # Test is_admin (should be false again)
            is_admin_final = await db.is_admin(test_admin_id)
            if is_admin_final:
                self.log_test("Is Admin - After Remove", False, "User should not be admin after removal")
                return False
            
            self.log_test("Admin Operations", True)
            return True
        except Exception as e:
            self.log_test("Admin Operations", False, str(e))
            return False

    async def test_notification_receiver_operations(self):
        """Test notification receiver operations"""
        try:
            test_receiver_id = 555666777
            added_by_id = 1757549785  # First admin
            
            # Test add notification receiver
            receiver = await db.add_notification_receiver(
                telegram_id=test_receiver_id,
                added_by=added_by_id,
                username="testreceiver",
                first_name="Test Receiver"
            )
            if not receiver or receiver["telegram_id"] != test_receiver_id:
                self.log_test("Add Notification Receiver", False, "Failed to add notification receiver")
                return False
            
            # Test add duplicate receiver (should return None)
            duplicate_receiver = await db.add_notification_receiver(test_receiver_id, added_by_id)
            if duplicate_receiver is not None:
                self.log_test("Add Duplicate Receiver", False, "Should not allow duplicate receiver")
                return False
            
            # Test get notification receivers
            all_receivers = await db.get_notification_receivers()
            receiver_ids = [r["telegram_id"] for r in all_receivers]
            if test_receiver_id not in receiver_ids:
                self.log_test("Get Notification Receivers", False, "New receiver not in receiver list")
                return False
            
            # Test remove notification receiver
            removed = await db.remove_notification_receiver(test_receiver_id)
            if not removed:
                self.log_test("Remove Notification Receiver", False, "Failed to remove notification receiver")
                return False
            
            # Verify removal
            final_receivers = await db.get_notification_receivers()
            final_receiver_ids = [r["telegram_id"] for r in final_receivers]
            if test_receiver_id in final_receiver_ids:
                self.log_test("Verify Receiver Removal", False, "Receiver still exists after removal")
                return False
            
            self.log_test("Notification Receiver Operations", True)
            return True
        except Exception as e:
            self.log_test("Notification Receiver Operations", False, str(e))
            return False

    async def test_order_number_counter(self):
        """Test order number counter functionality"""
        try:
            # Clear counters collection to test from scratch
            await db.counters_collection.delete_many({})
            
            # Test get next order number (should start from 1)
            order_num1 = await db.get_next_order_number()
            if order_num1 != 1:
                self.log_test("Order Number Counter - First", False, f"Expected 1, got {order_num1}")
                return False
            
            # Test sequential order numbers
            order_num2 = await db.get_next_order_number()
            if order_num2 != 2:
                self.log_test("Order Number Counter - Second", False, f"Expected 2, got {order_num2}")
                return False
            
            order_num3 = await db.get_next_order_number()
            if order_num3 != 3:
                self.log_test("Order Number Counter - Third", False, f"Expected 3, got {order_num3}")
                return False
            
            self.log_test("Order Number Counter", True)
            return True
        except Exception as e:
            self.log_test("Order Number Counter", False, str(e))
            return False

    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting Telegram Sushi Bot Backend Tests")
        print("=" * 50)
        
        # Test database connection first
        if not await self.test_database_connection():
            print("❌ Database connection failed. Stopping tests.")
            return False
        
        # Run all tests
        await self.test_init_test_data()
        await self.test_category_operations()
        await self.test_product_operations()
        await self.test_user_operations()
        await self.test_cart_operations()
        await self.test_order_operations()
        await self.test_admin_operations()
        await self.test_notification_receiver_operations()
        await self.test_order_number_counter()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for failed in self.failed_tests:
                print(f"  - {failed['test']}: {failed['error']}")
        
        if self.passed_tests:
            print(f"\n✅ Passed Tests ({len(self.passed_tests)}):")
            for passed in self.passed_tests:
                print(f"  - {passed}")
        
        return len(self.failed_tests) == 0

async def main():
    """Main test function"""
    tester = TelegramBotTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)