"""
Script to generate sample analytics data for testing/demo purposes.

This script generates realistic analytics events over a period of 30 days,
with 80-100 events per day, simulating real user behavior.

Usage:
    python scripts/seed_data.py YOUR_PROJECT_KEY
    
    Or with custom API URL:
    python scripts/seed_data.py YOUR_PROJECT_KEY --api-url http://localhost:5000
"""

import requests
import random
import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configuration
DEFAULT_API_URL = "http://127.0.0.1:5000"
DAYS_BACK = 30
MIN_EVENTS_PER_DAY = 80
MAX_EVENTS_PER_DAY = 100

# Event types from your app
EVENT_TYPES = [
    "screen_view",
    "button_click", 
    "view_item",
    "add_to_cart",
    "remove_from_cart",
    "checkout_started",
    "purchase_initiated",
    "view_cart",
    "purchase_success"  # For conversion tracking
]

# Sample data for realistic events
SCREEN_NAMES = ["Home", "Product Details", "Cart", "Checkout", "Profile", "Search", "Categories", "Settings", "About"]
BUTTON_IDS = ["add_to_cart", "checkout", "remove_item", "back", "search", "filter", "sort", "share", "favorite"]
PRODUCTS = [
    {"id": "prod_1", "name": "Laptop Pro", "price": 1299.99},
    {"id": "prod_2", "name": "Smartphone X", "price": 799.99},
    {"id": "prod_3", "name": "Tablet Air", "price": 499.99},
    {"id": "prod_4", "name": "Wireless Headphones", "price": 199.99},
    {"id": "prod_5", "name": "Mechanical Keyboard", "price": 129.99},
    {"id": "prod_6", "name": "Gaming Mouse", "price": 79.99},
    {"id": "prod_7", "name": "4K Monitor", "price": 399.99},
    {"id": "prod_8", "name": "Webcam HD", "price": 99.99},
    {"id": "prod_9", "name": "USB-C Hub", "price": 49.99},
    {"id": "prod_10", "name": "Laptop Stand", "price": 39.99},
    {"id": "prod_11", "name": "Desk Lamp", "price": 29.99},
    {"id": "prod_12", "name": "Cable Organizer", "price": 19.99},
]


def generate_events(days_back: int = DAYS_BACK, min_events: int = MIN_EVENTS_PER_DAY, max_events: int = MAX_EVENTS_PER_DAY) -> List[Dict[str, Any]]:
    """Generate realistic events spread over the last N days"""
    events = []
    now = datetime.utcnow()
    
    # Generate users (more users over time)
    num_users = random.randint(15, 30)
    user_ids = [f"user_{i:03d}" for i in range(1, num_users + 1)]
    anonymous_ids = [f"anon_{i:03d}" for i in range(1, num_users + 1)]
    
    print(f"👥 Generating events for {num_users} users...")
    
    for day_offset in range(days_back):
        # Random number of events for this day (between min and max)
        events_today = random.randint(min_events, max_events)
        base_date = now - timedelta(days=day_offset)
        
        print(f"📅 Day {day_offset + 1}/{days_back}: Generating {events_today} events...", end="\r")
        
        # Events are more active during day hours (9 AM - 9 PM)
        for event_num in range(events_today):
            # Random time during the day (more activity during business hours)
            hour = random.choices(
                range(24),
                weights=[0.5]*7 + [1]*2 + [3]*12 + [1]*2 + [0.5]*1  # More activity 9-21
            )[0]
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            timestamp = base_date.replace(hour=hour, minute=minute, second=second)
            
            # Pick random user (some users are more active)
            user_idx = random.choices(
                range(num_users),
                weights=[3] * (num_users // 3) + [2] * (num_users // 3) + [1] * (num_users - 2 * (num_users // 3))
            )[0]
            user_id = user_ids[user_idx]
            anonymous_id = anonymous_ids[user_idx]
            session_id = f"session_{user_idx:03d}_{day_offset}_{random.randint(1, 8)}"
            
            # Generate event based on type (some events are more common)
            event_type = random.choices(
                EVENT_TYPES,
                weights=[30, 25, 20, 10, 3, 5, 3, 3, 1]  # screen_view most common, purchase_success rare
            )[0]
            
            event = {
                "eventName": event_type,
                "timestamp": timestamp.isoformat() + "Z",
                "userId": user_id,
                "anonymousId": anonymous_id,
                "sessionId": session_id,
                "properties": {}
            }
            
            # Add properties based on event type
            if event_type == "screen_view":
                event["properties"] = {
                    "screen_name": random.choice(SCREEN_NAMES),
                    "screen_class": f"{random.choice(SCREEN_NAMES)}Activity"
                }
            
            elif event_type == "button_click":
                button_id = random.choice(BUTTON_IDS)
                event["properties"] = {
                    "button_id": button_id,
                    "button_text": button_id.replace("_", " ").title(),
                    "screen_name": random.choice(SCREEN_NAMES)
                }
            
            elif event_type == "view_item":
                product = random.choice(PRODUCTS)
                event["properties"] = {
                    "item_id": product["id"],
                    "item_name": product["name"],
                    "item_price": product["price"]
                }
            
            elif event_type == "add_to_cart":
                product = random.choice(PRODUCTS)
                event["properties"] = {
                    "item_id": product["id"],
                    "item_name": product["name"],
                    "item_price": product["price"],
                    "quantity": random.randint(1, 3)
                }
            
            elif event_type == "remove_from_cart":
                product = random.choice(PRODUCTS)
                event["properties"] = {
                    "item_id": product["id"],
                    "item_name": product["name"]
                }
            
            elif event_type == "checkout_started":
                item_count = random.randint(1, 5)
                cart_value = sum([random.choice(PRODUCTS)["price"] for _ in range(item_count)])
                event["properties"] = {
                    "cart_value": round(cart_value, 2),
                    "item_count": item_count
                }
            
            elif event_type == "purchase_initiated":
                product = random.choice(PRODUCTS)
                event["properties"] = {
                    "item_id": product["id"],
                    "item_name": product["name"],
                    "item_price": product["price"]
                }
            
            elif event_type == "purchase_success":
                product = random.choice(PRODUCTS)
                event["properties"] = {
                    "item_id": product["id"],
                    "item_name": product["name"],
                    "item_price": product["price"],
                    "transaction_id": f"txn_{random.randint(100000, 999999)}",
                    "payment_method": random.choice(["credit_card", "paypal", "apple_pay", "google_pay"])
                }
            
            elif event_type == "view_cart":
                item_count = random.randint(1, 5)
                cart_value = sum([random.choice(PRODUCTS)["price"] for _ in range(item_count)])
                event["properties"] = {
                    "item_count": item_count,
                    "cart_value": round(cart_value, 2)
                }
            
            events.append(event)
    
    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])
    print()  # New line after progress
    return events


def send_events(events: List[Dict[str, Any]], project_key: str, api_url: str, batch_size: int = 50):
    """Send events to the API in batches"""
    url = f"{api_url}/v1/events/batch"
    
    total_sent = 0
    total_batches = (len(events) + batch_size - 1) // batch_size
    
    print(f"\n📤 Sending {len(events)} events in {total_batches} batches...\n")
    
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        batch_num = i // batch_size + 1
        payload = {
            "projectKey": project_key,
            "events": batch
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                inserted = result.get("inserted", 0)
                total_sent += inserted
                print(f"✅ Batch {batch_num}/{total_batches}: {inserted}/{len(batch)} events inserted", end="\r")
            else:
                print(f"\n❌ Error in batch {batch_num}: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Connection error: Could not connect to {api_url}")
            print("   Make sure the backend server is running!")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Exception in batch {batch_num}: {str(e)}")
    
    print()  # New line after progress
    return total_sent


def verify_project(project_key: str, api_url: str) -> bool:
    """Verify that the project exists and is active"""
    try:
        url = f"{api_url}/v1/projects"
        response = requests.get(url, params={"projectKey": project_key}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            projects = data.get("projects", [])
            if projects:
                project = projects[0]
                if project.get("isActive", True):
                    print(f"✅ Project verified: {project.get('name')} ({project_key})")
                    return True
                else:
                    print(f"❌ Project {project_key} is not active")
                    return False
            else:
                print(f"❌ Project {project_key} not found")
                return False
        else:
            print(f"❌ Error verifying project: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {api_url}")
        print("   Make sure the backend server is running!")
        return False
    except Exception as e:
        print(f"❌ Error verifying project: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample analytics data for AppTracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/seed_data.py abc123def456
  python scripts/seed_data.py abc123def456 --api-url http://localhost:5000
        """
    )
    parser.add_argument(
        "project_key",
        help="Your project key (get it from the dashboard or API)"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 AppTracker Data Seeding Script")
    print("=" * 60)
    print(f"📊 Project Key: {args.project_key}")
    print(f"🌐 API URL: {args.api_url}")
    print(f"📅 Generating data for {DAYS_BACK} days")
    print(f"📈 Events per day: {MIN_EVENTS_PER_DAY}-{MAX_EVENTS_PER_DAY}")
    print("=" * 60)
    print()
    
    # Verify project exists
    print("🔍 Verifying project...")
    if not verify_project(args.project_key, args.api_url):
        print("\n❌ Project verification failed. Please check your project key.")
        sys.exit(1)
    
    print()
    
    # Generate events
    print("📝 Generating events...")
    events = generate_events(days_back=DAYS_BACK, min_events=MIN_EVENTS_PER_DAY, max_events=MAX_EVENTS_PER_DAY)
    print(f"✅ Generated {len(events)} events\n")
    
    # Send events
    total_sent = send_events(events, args.project_key, args.api_url, batch_size=50)
    
    # Summary
    print("\n" + "=" * 60)
    print("✨ Summary")
    print("=" * 60)
    print(f"📊 Total events generated: {len(events)}")
    print(f"✅ Total events inserted: {total_sent}")
    print(f"📅 Date range: {(datetime.utcnow() - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')} to {datetime.utcnow().strftime('%Y-%m-%d')}")
    print("=" * 60)
    print("\n🎉 Done! Check your dashboard to see the new data.")
    print(f"   Open your dashboard and select project: {args.project_key}")


if __name__ == "__main__":
    main()
