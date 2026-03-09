import json
import random
import time
from datetime import datetime, timezone
from faker import Faker
from kafka import KafkaProducer

# Faker generates realistic fake data for us
fake = Faker()

# This is our connection to Kafka
# We tell it where Kafka is running (localhost:9092)
# and how to serialize our data (convert Python dict → JSON string → bytes)
# Kafka only understands bytes, so we need to convert our data before sending
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# A fixed list of products our fake store sells
# In a real system this would come from a database
PRODUCTS = [
    {"product_id": "PROD-001", "name": "Wireless Headphones",  "category": "Electronics", "price": 49.99},
    {"product_id": "PROD-002", "name": "Running Shoes",         "category": "Sports",      "price": 89.99},
    {"product_id": "PROD-003", "name": "Coffee Maker",          "category": "Kitchen",     "price": 34.99},
    {"product_id": "PROD-004", "name": "Yoga Mat",              "category": "Sports",      "price": 24.99},
    {"product_id": "PROD-005", "name": "Bluetooth Speaker",     "category": "Electronics", "price": 59.99},
    {"product_id": "PROD-006", "name": "Water Bottle",          "category": "Kitchen",     "price": 14.99},
    {"product_id": "PROD-007", "name": "Laptop Stand",          "category": "Electronics", "price": 39.99},
    {"product_id": "PROD-008", "name": "Resistance Bands",      "category": "Sports",      "price": 19.99},
]

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "upi", "net_banking"]
ORDER_STATUSES  = ["placed", "confirmed", "processing"]

def generate_order():
    """
    Builds one fake order event as a Python dictionary.
    Every field mirrors what a real e-commerce order would have.
    """
    product  = random.choice(PRODUCTS)
    quantity = random.randint(1, 5)

    return {
        "order_id":       f"ORD-{fake.unique.random_int(min=10000, max=99999)}",
        "user_id":        f"USR-{random.randint(1000, 9999)}",
        "product_id":     product["product_id"],
        "product_name":   product["name"],
        "category":       product["category"],
        "quantity":       quantity,
        "unit_price":     product["price"],
        "total_price":    round(product["price"] * quantity, 2),
        "currency":       "USD",
        "status":         random.choice(ORDER_STATUSES),
        "payment_method": random.choice(PAYMENT_METHODS),
        "timestamp":      datetime.now(timezone.utc).isoformat()
    }

def main():
    print("🚀 Order producer started — sending events to Kafka...")
    print("Press Ctrl+C to stop.\n")

    while True:
        order = generate_order()

        # Send the event to the 'orders' topic in Kafka
        # This is the actual moment data enters your pipeline!
        producer.send('orders', value=order)

        print(f"✅ Order sent: {order['order_id']} | "
              f"{order['product_name']} x{order['quantity']} | "
              f"${order['total_price']}")

        # Wait 1-3 seconds before sending the next order
        # This simulates realistic traffic instead of flooding Kafka
        time.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    main()