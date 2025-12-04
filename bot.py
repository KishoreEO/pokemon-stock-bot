import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime
from twilio.rest import Client

# ============================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================

PRODUCT_URL = "https://www.pokemoncenter.com/product/10-10191-109/pokemon-tcg-mega-evolution-phantasmal-flames-booster-bundle-6-packs"
PRODUCT_NAME = "Pokemon TCG Mega Evolution Phantasmal Flames Booster Bundle"
CHECK_INTERVAL = 90  # seconds (90 = 1.5 minutes)

# Twilio Configuration (for SMS notifications)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'your_account_sid_here')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'your_auth_token_here')
TWILIO_PHONE_FROM = os.environ.get('TWILIO_PHONE_FROM', '+1234567890')
TWILIO_PHONE_TO = os.environ.get('TWILIO_PHONE_TO', '+1234567890')

# ============================================
# BOT CODE
# ============================================

class PokemonCenterMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.twilio_client = None
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            except:
                print("⚠️  Twilio credentials invalid")
        
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def send_sms(self, message):
        """Send SMS via Twilio"""
        if not self.twilio_client:
            self.log("❌ SMS not configured")
            return False
        
        try:
            msg = self.twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE_FROM,
                to=TWILIO_PHONE_TO
            )
            self.log(f"✅ SMS sent! SID: {msg.sid}")
            return True
        except Exception as e:
            self.log(f"❌ SMS failed: {str(e)}")
            return False
    
    def check_stock(self):
        """Check if product is in stock"""
        try:
            self.log(f"🔍 Checking: {PRODUCT_NAME}")
            
            response = self.session.get(PRODUCT_URL, headers=self.headers, timeout=15)
            
            if response.status_code == 403:
                self.log("⚠️  Bot protection detected (403). Retrying with delay...")
                time.sleep(5)
                return None
            
            if response.status_code != 200:
                self.log(f"❌ HTTP {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            in_stock = False
            
            # Method 1: Check for "Add to Cart" button
            add_to_cart_btn = soup.find('button', {'class': lambda x: x and 'add-to-cart' in x.lower()})
            if add_to_cart_btn and 'disabled' not in add_to_cart_btn.get('class', []):
                in_stock = True
                self.log("✅ Method 1: Add to cart button found!")
            
            # Method 2: Check availability text
            availability = soup.find('p', {'class': lambda x: x and 'availability' in x.lower()})
            if availability:
                text = availability.get_text().lower()
                if 'in stock' in text or 'available' in text:
                    in_stock = True
                    self.log("✅ Method 2: 'In Stock' text found!")
                elif 'out of stock' in text or 'sold out' in text:
                    self.log("❌ Out of stock")
            
            # Method 3: Check for out of stock indicators
            out_of_stock = soup.find(text=lambda x: x and ('out of stock' in x.lower() or 'sold out' in x.lower()))
            if out_of_stock:
                in_stock = False
                self.log("❌ 'Out of Stock' text detected")
            
            # Method 4: Check structured data (JSON-LD)
            json_ld = soup.find('script', {'type': 'application/ld+json'})
            if json_ld:
                import json
                try:
                    data = json.loads(json_ld.string)
                    if isinstance(data, list):
                        data = data[0]
                    if 'offers' in data:
                        availability_str = data['offers'].get('availability', '').lower()
                        if 'instock' in availability_str:
                            in_stock = True
                            self.log("✅ Method 4: JSON-LD shows in stock!")
                except:
                    pass
            
            return in_stock
            
        except requests.exceptions.Timeout:
            self.log("⏱️  Request timeout")
            return None
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            return None
    
    def notify(self):
        """Send notification when item is in stock"""
        message = f"🚨 IN STOCK ALERT! 🚨\n\n{PRODUCT_NAME}\n\nBUY NOW: {PRODUCT_URL}"
        
        self.log("📢 ITEM IN STOCK! Sending notification...")
        self.send_sms(message)
    
    def run(self):
        """Main monitoring loop"""
        self.log("🤖 Pokemon Center Stock Monitor Starting...")
        self.log(f"📦 Monitoring: {PRODUCT_NAME}")
        self.log(f"⏱️  Check interval: {CHECK_INTERVAL} seconds")
        self.log(f"🔗 URL: {PRODUCT_URL}")
        self.log("=" * 60)
        
        check_count = 0
        
        while True:
            check_count += 1
            self.log(f"Check #{check_count}")
            
            stock_status = self.check_stock()
            
            if stock_status is True:
                self.log("🎉 ITEM IS IN STOCK!")
                self.notify()
                self.log("Waiting 5 minutes before next check...")
                time.sleep(300)
            elif stock_status is False:
                self.log("😔 Still out of stock")
            else:
                self.log("⚠️  Could not determine stock status")
            
            self.log(f"💤 Sleeping for {CHECK_INTERVAL} seconds...")
            self.log("-" * 60)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor = PokemonCenterMonitor()
    monitor.run()
```

5. Scroll down and click **"Commit changes"** (green button)

---

## 📝 **Step 2: Add Requirements File**

1. Click **"Add file"** again → **"Create new file"**
2. **Name:** `requirements.txt`
3. **Paste this:**
```
requests==2.31.0
beautifulsoup4==4.12.2
twilio==8.10.0
