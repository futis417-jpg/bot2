import os
import telebot
from flask import Flask
import threading

# Configuración inicial del bot
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'TU_TOKEN_AQUI')
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Datos de Administración y Enlaces
SUPER_ADMIN_ID = 8398522835 
ADMIN_USERNAME = "izi_1244"
ADMIN_LINK = f"https://t.me/{ADMIN_USERNAME}"

# Parámetros del Negocio
MAX_USES_PER_COOKIE = 3
RATE_LIMIT_SECONDS = 60

# Cache y Estados Globales Compartidos
user_last_action = {}
db_lock = threading.Lock()
bot_info = None
