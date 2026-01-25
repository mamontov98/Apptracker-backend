"""
סקריפט פשוט להוספת אירועי דמו ל-Funnel
מוסיף אירועים ריאליסטיים שמדמים משתמשים שעוברים דרך funnel

Usage:
    python scripts/demo_funnel_events.py
    
או עם projectKey אחר:
    python scripts/demo_funnel_events.py --project-key YOUR_PROJECT_KEY
"""

import requests
import random
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Project Key לדמו
DEFAULT_PROJECT_KEY = "f81ef85b4a40"
DEFAULT_API_URL = "http://127.0.0.1:5000"

# אירועים ל-Funnel (בסדר הלוגי)
FUNNEL_EVENTS = [
    "app_open",           # כניסה לאפליקציה
    "screen_view",        # צפייה במסך
    "button_click",       # לחיצה על כפתור
    "login_success",      # התחברות מוצלחת
    "add_to_cart",        # הוספה לעגלה
    "checkout_started",   # התחלת תהליך תשלום
    "purchase_success"    # רכישה מוצלחת
]

# מסכים לדמו
SCREEN_NAMES = ["Home", "Product", "Cart", "Checkout", "Profile", "Search"]
BUTTON_IDS = ["login", "add_to_cart", "checkout", "purchase", "back", "search"]


def generate_funnel_events(num_users: int = 50, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    יוצר אירועים שמדמים משתמשים שעוברים דרך funnel
    לא כל המשתמשים מגיעים עד הסוף - יש drop-off ריאליסטי
    """
    events = []
    now = datetime.utcnow()
    
    print(f"👥 יוצר אירועים עבור {num_users} משתמשים...")
    
    for user_num in range(1, num_users + 1):
        user_id = f"user_{user_num:03d}"
        anonymous_id = f"anon_{user_num:03d}"
        
        # כל משתמש מתחיל ביום אקראי ב-7 הימים האחרונים
        day_offset = random.randint(0, days_back - 1)
        base_time = now - timedelta(days=day_offset)
        
        # כל משתמש מתחיל בשעה אקראית ביום
        hour = random.randint(9, 21)  # שעות פעילות
        minute = random.randint(0, 59)
        current_time = base_time.replace(hour=hour, minute=minute, second=0)
        
        session_id = f"session_{user_num:03d}_{day_offset}"
        
        # Drop-off rates ריאליסטיים (כמה משתמשים ממשיכים מכל שלב)
        # 100% מתחילים ב-app_open
        # 90% ממשיכים ל-screen_view
        # 70% ממשיכים ל-button_click
        # 50% ממשיכים ל-login_success
        # 40% ממשיכים ל-add_to_cart
        # 30% ממשיכים ל-checkout_started
        # 20% מגיעים ל-purchase_success
        
        drop_off_rates = {
            "app_open": 1.0,        # 100% מתחילים
            "screen_view": 0.9,     # 90% ממשיכים
            "button_click": 0.7,    # 70% ממשיכים
            "login_success": 0.5,   # 50% ממשיכים
            "add_to_cart": 0.4,     # 40% ממשיכים
            "checkout_started": 0.3, # 30% ממשיכים
            "purchase_success": 0.2  # 20% מגיעים
        }
        
        previous_event_time = current_time
        
        for i, event_name in enumerate(FUNNEL_EVENTS):
            # בדוק אם המשתמש ממשיך לשלב הזה
            if random.random() > drop_off_rates[event_name]:
                break  # המשתמש נשר - לא ממשיך
            
            # הוסף זמן בין אירועים (30 שניות עד 5 דקות)
            seconds_between = random.randint(30, 300)
            event_time = previous_event_time + timedelta(seconds=seconds_between)
            
            event = {
                "eventName": event_name,
                "timestamp": event_time.isoformat() + "Z",
                "userId": user_id,
                "anonymousId": anonymous_id,
                "sessionId": session_id,
                "properties": {}
            }
            
            # הוסף properties לפי סוג האירוע
            if event_name == "app_open":
                event["properties"] = {
                    "app_version": "1.2.3",
                    "platform": random.choice(["android", "ios", "web"])
                }
            
            elif event_name == "screen_view":
                screen = random.choice(SCREEN_NAMES)
                event["properties"] = {
                    "screen_name": screen,
                    "screen_class": f"{screen}Activity"
                }
            
            elif event_name == "button_click":
                button_id = random.choice(BUTTON_IDS)
                event["properties"] = {
                    "button_id": button_id,
                    "button_text": button_id.replace("_", " ").title(),
                    "screen_name": random.choice(SCREEN_NAMES)
                }
            
            elif event_name == "login_success":
                event["properties"] = {
                    "method": random.choice(["email", "google", "facebook"]),
                    "is_new_user": random.choice([True, False])
                }
            
            elif event_name == "add_to_cart":
                event["properties"] = {
                    "item_id": f"prod_{random.randint(1, 10)}",
                    "item_name": f"Product {random.randint(1, 10)}",
                    "item_price": round(random.uniform(10, 500), 2),
                    "quantity": random.randint(1, 3)
                }
            
            elif event_name == "checkout_started":
                event["properties"] = {
                    "cart_value": round(random.uniform(50, 1000), 2),
                    "item_count": random.randint(1, 5),
                    "payment_method": random.choice(["credit_card", "paypal"])
                }
            
            elif event_name == "purchase_success":
                event["properties"] = {
                    "transaction_id": f"txn_{random.randint(100000, 999999)}",
                    "total_value": round(random.uniform(50, 1000), 2),
                    "payment_method": random.choice(["credit_card", "paypal", "apple_pay"]),
                    "items_count": random.randint(1, 5)
                }
            
            events.append(event)
            previous_event_time = event_time
        
        # הוסף כמה אירועים נוספים אקראיים (לא חלק מה-funnel)
        # כדי שהדמו יראה יותר ריאליסטי
        for _ in range(random.randint(2, 5)):
            random_event_time = previous_event_time + timedelta(seconds=random.randint(60, 600))
            random_event = random.choice(["screen_view", "button_click"])
            
            event = {
                "eventName": random_event,
                "timestamp": random_event_time.isoformat() + "Z",
                "userId": user_id,
                "anonymousId": anonymous_id,
                "sessionId": session_id,
                "properties": {}
            }
            
            if random_event == "screen_view":
                event["properties"] = {
                    "screen_name": random.choice(SCREEN_NAMES),
                    "screen_class": f"{random.choice(SCREEN_NAMES)}Activity"
                }
            else:
                event["properties"] = {
                    "button_id": random.choice(BUTTON_IDS),
                    "button_text": random.choice(BUTTON_IDS).replace("_", " ").title()
                }
            
            events.append(event)
    
    # מיון לפי timestamp
    events.sort(key=lambda x: x["timestamp"])
    return events


def send_events(events: List[Dict[str, Any]], project_key: str, api_url: str, batch_size: int = 50):
    """שולח אירועים ל-API בקבוצות"""
    url = f"{api_url}/v1/events/batch"
    
    total_sent = 0
    total_batches = (len(events) + batch_size - 1) // batch_size
    
    print(f"\n📤 שולח {len(events)} אירועים ב-{total_batches} קבוצות...\n")
    
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
                print(f"✅ קבוצה {batch_num}/{total_batches}: {inserted}/{len(batch)} אירועים נוספו", end="\r")
            else:
                print(f"\n❌ שגיאה בקבוצה {batch_num}: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            print(f"\n❌ שגיאת חיבור: לא ניתן להתחבר ל-{api_url}")
            print("   ודא שהשרת רץ!")
            return 0
        except Exception as e:
            print(f"\n❌ שגיאה בקבוצה {batch_num}: {str(e)}")
    
    print()  # שורה חדשה אחרי התקדמות
    return total_sent


def verify_project(project_key: str, api_url: str) -> bool:
    """מוודא שהפרויקט קיים ופעיל"""
    try:
        url = f"{api_url}/v1/projects"
        response = requests.get(url, params={"projectKey": project_key}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            projects = data.get("projects", [])
            if projects:
                project = projects[0]
                if project.get("isActive", True):
                    print(f"✅ פרויקט מאומת: {project.get('name')} ({project_key})")
                    return True
                else:
                    print(f"❌ הפרויקט {project_key} לא פעיל")
                    return False
            else:
                print(f"❌ פרויקט {project_key} לא נמצא")
                return False
        else:
            print(f"❌ שגיאה באימות פרויקט: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ לא ניתן להתחבר ל-{api_url}")
        print("   ודא שהשרת רץ!")
        return False
    except Exception as e:
        print(f"❌ שגיאה באימות פרויקט: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="הוסף אירועי דמו ל-Funnel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
דוגמאות:
  python scripts/demo_funnel_events.py
  python scripts/demo_funnel_events.py --project-key YOUR_PROJECT_KEY
  python scripts/demo_funnel_events.py --users 100 --days 14
        """
    )
    parser.add_argument(
        "--project-key",
        default=DEFAULT_PROJECT_KEY,
        help=f"מפתח הפרויקט (ברירת מחדל: {DEFAULT_PROJECT_KEY})"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"כתובת ה-API (ברירת מחדל: {DEFAULT_API_URL})"
    )
    parser.add_argument(
        "--users",
        type=int,
        default=50,
        help="מספר משתמשים ליצור (ברירת מחדל: 50)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="מספר ימים אחורה (ברירת מחדל: 7)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 סקריפט הוספת אירועי דמו ל-Funnel")
    print("=" * 60)
    print(f"📊 מפתח פרויקט: {args.project_key}")
    print(f"🌐 כתובת API: {args.api_url}")
    print(f"👥 מספר משתמשים: {args.users}")
    print(f"📅 ימים אחורה: {args.days}")
    print("=" * 60)
    print()
    
    # אימות פרויקט
    print("🔍 מאמת פרויקט...")
    if not verify_project(args.project_key, args.api_url):
        print("\n❌ אימות פרויקט נכשל. בדוק את מפתח הפרויקט.")
        return
    
    print()
    
    # יצירת אירועים
    print("📝 יוצר אירועים...")
    events = generate_funnel_events(num_users=args.users, days_back=args.days)
    print(f"✅ נוצרו {len(events)} אירועים\n")
    
    # סטטיסטיקות
    event_counts = {}
    for event in events:
        event_name = event["eventName"]
        event_counts[event_name] = event_counts.get(event_name, 0) + 1
    
    print("📊 סטטיסטיקות אירועים:")
    for event_name in FUNNEL_EVENTS:
        count = event_counts.get(event_name, 0)
        print(f"   {event_name}: {count}")
    print()
    
    # שליחת אירועים
    total_sent = send_events(events, args.project_key, args.api_url, batch_size=50)
    
    # סיכום
    print("\n" + "=" * 60)
    print("✨ סיכום")
    print("=" * 60)
    print(f"📊 סך הכל אירועים שנוצרו: {len(events)}")
    print(f"✅ סך הכל אירועים שנוספו: {total_sent}")
    print(f"📅 טווח תאריכים: {(datetime.utcnow() - timedelta(days=args.days)).strftime('%Y-%m-%d')} עד {datetime.utcnow().strftime('%Y-%m-%d')}")
    print("=" * 60)
    print("\n🎉 סיום! בדוק את הדשבורד כדי לראות את הנתונים החדשים.")
    print(f"   פתח את הדשבורד ובחר פרויקט: {args.project_key}")
    print("\n💡 טיפ: עכשיו תוכל לראות Funnel יפה עם drop-off rates ריאליסטיים!")


if __name__ == "__main__":
    main()
