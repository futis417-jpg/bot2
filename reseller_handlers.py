import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import bot
from database import init_db, save_db
from keyboards import reseller_main_keyboard
from utils import generate_coupon_code
from datetime import datetime

# Cuando un revendedor escribe el comando o pulsa un botón con este texto
@bot.message_handler(commands=['reseller'])
@bot.message_handler(func=lambda m: m.text == "💼 Panel Reseller")
def reseller_panel_start(message):
    db = init_db()
    uid = str(message.from_user.id)
    
    # Comprobamos si tiene autorización
    if 'resellers' not in db or uid not in db['resellers']:
        bot.reply_to(message, "❌ *Acceso Denegado*\n\nNo tienes permisos de Revendedor. Contacta al administrador si deseas adquirir una franquicia para vender cupones.", parse_mode="Markdown")
        return
        
    bot.send_message(
        message.chat.id, 
        "💼 **CENTRO DE MANDOS REVENDEDOR** 💼\n\nBienvenido a tu panel privado. Aquí puedes generar códigos VIP al instante usando tus créditos.\n\nElige una opción:", 
        reply_markup=reseller_main_keyboard(), 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("reseller_"))
def reseller_callbacks(call):
    db = init_db()
    uid = str(call.from_user.id)
    
    # Doble seguridad
    if 'resellers' not in db or uid not in db['resellers']:
        bot.answer_callback_query(call.id, "❌ No eres revendedor.", show_alert=True)
        return
        
    r_data = db['resellers'][uid]
    
    if call.data == "reseller_stats":
        texto = f"📊 **TUS ESTADÍSTICAS** 📊\n\n💰 **Créditos disponibles:** {r_data.get('credits', 0)}\n🎟️ **Cupones creados en total:** {r_data.get('total_created', 0)}\n\n_1 Crédito = 7 Días VIP_"
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto, reply_markup=reseller_main_keyboard(), parse_mode="Markdown")
        
    elif call.data.startswith("reseller_create_"):
        days = int(call.data.split("_")[2])
        
        # Calcular el coste en créditos
        if days == 7: cost = 1
        elif days == 15: cost = 2
        elif days == 30: cost = 4
        else: cost = 10
        
        # Comprobar saldo
        if r_data.get('credits', 0) < cost:
            bot.answer_callback_query(call.id, f"❌ Saldo insuficiente. Necesitas {cost} créditos para generar este cupón.", show_alert=True)
            return
            
        # Descontar créditos
        db['resellers'][uid]['credits'] -= cost
        db['resellers'][uid]['total_created'] = r_data.get('total_created', 0) + 1
        
        # Generar e inyectar cupón real en la BD
        code = generate_coupon_code(days)
        if 'coupons' not in db: db['coupons'] = {}
        db['coupons'][code] = {'days': days, 'created_by': uid}
        
        # Guardar en el historial del revendedor
        if 'history' not in db['resellers'][uid]: db['resellers'][uid]['history'] = []
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        db['resellers'][uid]['history'].insert(0, f"[{fecha}] Cupón {days}D: `{code}`")
        db['resellers'][uid]['history'] = db['resellers'][uid]['history'][:10] # Solo guarda los 10 últimos para no saturar memoria
        
        save_db(db)
        
        texto = f"✅ **¡CUPÓN GENERADO CON ÉXITO!**\n\n🎟️ **Código VIP:** `{code}`\n⏳ **Duración:** {days} Días\n\n💎 **Coste:** -{cost} créditos\n💰 **Saldo Restante:** {db['resellers'][uid]['credits']} créditos\n\n_Envía este código a tu cliente para que lo canjee en el bot._"
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto, reply_markup=reseller_main_keyboard(), parse_mode="Markdown")
        
    elif call.data == "reseller_history":
        historial = r_data.get('history', [])
        if not historial:
            texto = "📜 No has generado ningún cupón todavía."
        else:
            texto = "📜 **TUS ÚLTIMOS 10 CUPONES CREADOS** 📜\n\n" + "\n".join(historial)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto, reply_markup=reseller_main_keyboard(), parse_mode="Markdown")
