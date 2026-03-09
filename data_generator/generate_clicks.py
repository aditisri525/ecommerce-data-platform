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

PAGES = [
    "home", "category", "product_detail",
    "cart", "checkout", "order_confirmation"
]

ACTIONS = [
    "page_view", "product_click", "add_to_cart",
    "remove_from_cart", "begin_checkout", "search"
]

DEVICES   = ["mobile", "desktop", "tablet"]
REFERRALS = ["google_ads", "organic_search", "direct", "social_media", "email_campaign"]

def generate_click():
    """
    Builds one fake clickstream event.
    Clickstream tracks what users do on the website —
    which pages they visit, what they click, what device they use.
    This data is gold for understanding user behaviour.
    """
    return {
        "event_id":       f"EVT-{fake.unique.random_int(min=100000, max=999999)}",
        "session_id":     f"SESS-{random.randint(10000, 99999)}",
        "user_id":        f"USR-{random.randint(1000, 9999)}",
        "page":           random.choice(PAGES),
        "product_id":     random.choice(PRODUCTS) if random.random() > 0.3 else None,
        "referral_source": random.choice(REFERRALS),
        "device_type":    random.choice(DEVICES),
        "action":         random.choice(ACTIONS),
        "timestamp":      datetime.now(timezone.utc).isoformat()
    }

def main():
    print("🚀 Clickstream producer started — sending events to Kafka...")
    print("Press Ctrl+C to stop.\n")

    while True:
        click = generate_click()
        producer.send('clickstream', value=click)

        print(f"✅ Click sent: {click['event_id']} | "
              f"{click['action']} on {click['page']} | "
              f"{click['device_type']}")

        # Clicks happen more frequently than orders
        # so we send them faster — every 0.5 to 1.5 seconds
        time.sleep(random.uniform(0.5, 1.5))

if __name__ == "__main__":
    main()