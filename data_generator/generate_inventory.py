import json
import random
import time
from datetime import datetime, timezone
from faker import Faker
from kafka import KafkaProducer

fake = Faker()

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

PRODUCTS = [
    "PROD-001", "PROD-002", "PROD-003", "PROD-004",
    "PROD-005", "PROD-006", "PROD-007", "PROD-008"
]

WAREHOUSES = ["WH-EAST-01", "WH-WEST-01", "WH-CENTRAL-01"]

CHANGE_REASONS = ["purchase", "restock", "damaged", "returned", "adjustment"]

# Starting stock levels for each product
# We track this so stock levels change realistically over time
stock_levels = {product: random.randint(100, 500) for product in PRODUCTS}

def generate_inventory_update():
    """
    Builds one fake inventory update event.
    Every time an order is placed, stock goes down.
    Every time a restock happens, stock goes up.
    We simulate both here.
    """
    product_id     = random.choice(PRODUCTS)
    previous_stock = stock_levels[product_id]
    reason         = random.choice(CHANGE_REASONS)

    # Stock goes up for restocks and returns, down for everything else
    if reason in ["restock", "returned"]:
        change = random.randint(10, 100)
    else:
        change = -random.randint(1, 10)

    # Make sure stock never goes below zero
    updated_stock = max(0, previous_stock + change)
    stock_levels[product_id] = updated_stock

    return {
        "update_id":          f"INV-{fake.unique.random_int(min=10000, max=99999)}",
        "product_id":         product_id,
        "warehouse_id":       random.choice(WAREHOUSES),
        "previous_stock":     previous_stock,
        "updated_stock":      updated_stock,
        "change_quantity":    updated_stock - previous_stock,
        "change_reason":      reason,
        "triggered_by_order": f"ORD-{random.randint(10000, 99999)}" if reason == "purchase" else None,
        "timestamp":          datetime.now(timezone.utc).isoformat()
    }

def main():
    print("🚀 Inventory producer started — sending events to Kafka...")
    print("Press Ctrl+C to stop.\n")

    while True:
        update = generate_inventory_update()
        producer.send('inventory_updates', value=update)

        direction = "📈" if update['change_quantity'] > 0 else "📉"
        print(f"✅ Inventory update: {update['product_id']} | "
              f"{update['warehouse_id']} | "
              f"{direction} {update['previous_stock']} → {update['updated_stock']} | "
              f"{update['change_reason']}")

        # Inventory updates are less frequent than clicks but more than orders
        time.sleep(random.uniform(2, 5))

if __name__ == "__main__":
    main()