import os
import time
import random
import string
import json
from playwright.sync_api import sync_playwright
import config
import database

def clean_old_screenshots():
    for file in os.listdir():
        if file.endswith('.png') and file.startswith(('error_', 'spy_')):
            try: os.remove(file)
            except: pass

def auto_repair_system():
    """Limpia archivos fantasma y libera RAM sin que el usuario se entere."""
    try:
        clean_old_screenshots()
        # Limpiar diccionario de spam para evitar que crezca infinitamente
        now = time.time()
        for k in list(config.user_last_action.keys()):
            if now - config.user_last_action[k] > 3600:
                del config.user_last_action[k]
    except: pass

def check_rate_limit(user_id):
    if database.is_admin(user_id) or database.check_vip_status(user_id): return True
    now = time.time()
    if user_id in config.user_last_action:
        if now - config.user_last_action[user_id] < config.RATE_LIMIT_SECONDS: return False
    config.user_last_action[user_id] = now
    return True

def generate_coupon_code(days):
    letters_and_digits = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(letters_and_digits) for i in range(8))
    return f"VIP-{code[:4]}-{code[4:]}"

def parse_netscape_cookies(text):
    cookies = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or not line.startswith('.'): continue
        parts = line.split()
        if len(parts) >= 7:
            domain = parts[0]
            path = parts[2]
            secure = parts[3].upper() == 'TRUE'
            name = parts[5]
            value = parts[6]
            cookies.append({"name": name, "value": value, "domain": domain, "path": path, "secure": secure})
    return cookies

def check_cookie_validity(cookie_data):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            context = browser.new_context()
            if isinstance(cookie_data, str): cookies = json.loads(cookie_data)
            else: cookies = cookie_data
            context.add_cookies(cookies)
            page = context.new_page()
            page.goto('https://www.netflix.com/browse', timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)
            is_valid = page.locator('.account-menu-item, [data-uia="header-profile-link"]').is_visible()
            if not is_valid and "login" not in page.url.lower(): is_valid = True
            browser.close()
            return is_valid
    except:
        return False
