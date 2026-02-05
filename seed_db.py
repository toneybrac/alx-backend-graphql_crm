#!/usr/bin/env python
"""
Script to seed the database with sample data
"""
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

from crm.models import Customer, Product, Order
import uuid

def clear_database():
    """Clear existing data"""
    print("Clearing existing data...")
    Order.objects.all().delete()
    Customer.objects.all().delete()
    Product.objects.all().delete()

def seed_customers():
    """Seed customers"""
    print("Seeding customers...")
    customers = [
        {"name": "Alice Johnson", "email": "alice@example.com", "phone": "+1234567890"},
        {"name": "Bob Smith", "email": "bob@example.com", "phone": "123-456-7890"},
        {"name": "Carol Davis", "email": "carol@example.com", "phone": "+9876543210"},
        {"name": "David Wilson", "email": "david@example.com", "phone": "987-654-3210"},
        {"name": "Eva Brown", "email": "eva@example.com", "phone": "+1122334455"},
    ]
    
    for data in customers:
        Customer.objects.create(**data)
    
    print(f"Created {len(customers)} customers")

def seed_products():
    """Seed products"""
    print("Seeding products...")
    products = [
        {"name": "Laptop", "price": 999.99, "stock": 10},
        {"name": "Smartphone", "price": 699.99, "stock": 25},
        {"name": "Tablet", "price": 399.99, "stock": 15},
        {"name": "Headphones", "price": 149.99, "stock": 30},
        {"name": "Keyboard", "price": 79.99, "stock": 50},
        {"name": "Mouse", "price": 29.99, "stock": 100},
        {"name": "Monitor", "price": 299.99, "stock": 20},
        {"name": "Printer", "price": 199.99, "stock": 12},
    ]
    
    for data in products:
        Product.objects.create(**data)
    
    print(f"Created {len(products)} products")

def seed_orders():
    """Seed orders"""
    print("Seeding orders...")
    
    customers = list(Customer.objects.all())
    products = list(Product.objects.all())
    
    if not customers or not products:
        print("Need customers and products first")
        return
    
    orders_data = [
        {
            "customer": customers[0],
            "products": [products[0], products[1], products[2]],
        },
        {
            "customer": customers[1],
            "products": [products[3], products[4]],
        },
        {
            "customer": customers[2],
            "products": [products[5], products[6], products[7]],
        },
        {
            "customer": customers[3],
            "products": [products[0], products[3], products[6]],
        },
        {
            "customer": customers[4],
            "products": [products[1], products[4], products[7]],
        },
    ]
    
    for data in orders_data:
        total_amount = sum(product.price for product in data["products"])
        order = Order.objects.create(
            customer=data["customer"],
            total_amount=total_amount
        )
        order.products.set(data["products"])
    
    print(f"Created {len(orders_data)} orders")

def main():
    """Main seeding function"""
    print("Starting database seeding...")
    
    clear_database()
    seed_customers()
    seed_products()
    seed_orders()
    
    print("\nDatabase seeding completed!")
    print("\nSummary:")
    print(f"Customers: {Customer.objects.count()}")
    print(f"Products: {Product.objects.count()}")
    print(f"Orders: {Order.objects.count()}")
    
    # Show sample data
    print("\nSample Customer:")
    if Customer.objects.exists():
        customer = Customer.objects.first()
        print(f"  Name: {customer.name}, Email: {customer.email}")
    
    print("\nSample Product:")
    if Product.objects.exists():
        product = Product.objects.first()
        print(f"  Name: {product.name}, Price: ${product.price}, Stock: {product.stock}")
    
    print("\nSample Order:")
    if Order.objects.exists():
        order = Order.objects.first()
        print(f"  ID: {order.id}, Customer: {order.customer.name}, Total: ${order.total_amount}")
        print(f"  Products: {', '.join([p.name for p in order.products.all()])}")

if __name__ == "__main__":
    main()
