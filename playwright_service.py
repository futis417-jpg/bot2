import os
import time
import json
import threading
from playwright.sync_api import sync_playwright
import config
from config import bot
import database
from database import init_db, save_db
from utils import check_cookie_validity

def run_playwright_activation(code, cookie_data):
    screenshot_path = f"error_{int(time.time())}.png"
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            if isinstance(cookie_data, str): cookies = json.loads(cookie_data)
            else: cookies = cookie_data
            
            context.add_cookies(cookies)
            page = context.new_page()
            
            try:
                page.goto('https://www.netflix.com/tv8', timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2)
                
                if "login" in page.url.lower():
                    page.screenshot(path=screenshot_path)
                    return False, "❌ La cookie ha caducado o la cuenta cambió de contraseña.", screenshot_path
                
                input_locator = page.locator('input[type="text"], input[type="tel"], input[type="number"], input[data-uia="pin-number-input"]').first
                input_locator.click(timeout=15000)
                page.keyboard.type(code, delay=100)
                
                button_locator = page.locator('button[type="button"], button[type="submit"], button[data-uia="action-submit"]').first
                button_locator.click(timeout=10000)
                
                time.sleep(4)
                if page.locator('.ui-message-error, [data-uia="error-message-container"]').is_visible():
                    page.screenshot(path=screenshot_path)
                    error_text = page.locator('.ui-message-error, [data-uia="error-message-container"]').first.text_content()
                    return False, f"❌ Netflix rechazó el código: {error_text}", screenshot_path
                
                return True, "🎉 ¡**TV Activada con éxito**! 📺✨\n\nTu televisor ha sido enlazado correctamente.\n¡Disfruta del mejor contenido!", None
            except Exception as e:
                page.screenshot(path=screenshot_path)
                return False, f"❌ Error de lectura en Netflix. Detalles: {str(e)[:80]}", screenshot_path
            finally:
                if browser: browser.close()
    except Exception as e:
        return False, f"❌ Error crítico de servidor. {str(e)[:80]}", None

def background_spy(chat_id, msg_id, cookie_data):
    screenshot_path = f"spy_{int(time.time())}.png"
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            context = browser.new_context(viewport={'width': 1280, 'height': 720})
            if isinstance(cookie_data, str): cookies = json.loads(cookie_data)
            else: cookies = cookie_data
            context.add_cookies(cookies)
            page = context.new_page()
            page.goto('https://www.netflix.com/browse', timeout=40000)
            time.sleep(5) 
            page.screenshot(path=screenshot_path)
            
            with open(screenshot_path, 'rb') as photo:
                bot.send_photo(chat_id, photo, caption="📸 **Captura en Vivo (Modo Espía)**\n_Viendo lo que ve el usuario..._", parse_mode="Markdown")
            bot.delete_message(chat_id, msg_id)
    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"❌ Error en Modo Espía. Detalles: {str(e)[:100]}")
    finally:
        if browser:
            try: browser.close()
            except: pass
        if os.path.exists(screenshot_path):
            try: os.remove(screenshot_path)
            except: pass

def background_check_cookies(chat_id):
    db = init_db()
    buenas = 0; malas = 0
    report = "📋 **REPORTE DE DIAGNÓSTICO INTELIGENTE** 📋\n\n"
    for i, c in enumerate(db['cookies_list']):
        if c['status'] == 'active':
            is_valid = check_cookie_validity(c['data'])
            if not is_valid:
                db['cookies_list'][i]['status'] = 'exhausted'
                malas += 1
                report += f"❌ Cuenta #{i+1} ({c.get('country','N/A')}) ➔ `Sesión Caducada`\n"
            else:
                buenas += 1
                report += f"✅ Cuenta #{i+1} ({c.get('country','N/A')}) ➔ `Operativa`\n"
    save_db(db)
    report += f"\n📊 **Resumen Global:** {buenas} Vivas | {malas} Eliminadas."
    bot.send_message(chat_id, report, parse_mode="Markdown")
