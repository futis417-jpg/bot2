from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

## ==========================================
# 🧑‍💻 TECLADOS DE USUARIO (RECUPERADOS PARA EVITAR CRASHEO)
# ==========================================
def main_user_keyboard(*args, **kwargs):
    # Nota: Si tenías otros textos en tus botones originales, puedes cambiarlos aquí.
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🎬 Obtener Cuenta", callback_data="get_account"))
    markup.add(InlineKeyboardButton("👤 Mi Perfil", callback_data="profile"), InlineKeyboardButton("💎 Plan VIP", callback_data="vip"))
    return markup

def countries_keyboard(*args, **kwargs):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🌍 Cuenta Aleatoria", callback_data="country_any"))
    markup.add(InlineKeyboardButton("🔙 Volver", callback_data="back_main"))
    return markup

## ==========================================
# 👑 TECLADOS DE ADMINISTRADOR (Con Botón de Revendedores y Restaurar BD)
# ==========================================
def admin_panel_keyboard(db):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("➕ Añadir Cookie", callback_data="admin_add_cookie"), InlineKeyboardButton("📥 Importar Lote", callback_data="admin_bulk_import"))
    markup.add(InlineKeyboardButton("🎟️ Crear Cupón VIP", callback_data="admin_create_coupon"), InlineKeyboardButton("💎 Gestionar Planes", callback_data="admin_manage_plans"))
    markup.add(InlineKeyboardButton("💳 Gestionar Usuarios", callback_data="admin_manage_users"), InlineKeyboardButton("📊 Estado Cuentas", callback_data="admin_status"))
    markup.add(InlineKeyboardButton("📸 Modo Espía", callback_data="admin_spy_menu"), InlineKeyboardButton("🔍 Diagnóstico Pro", callback_data="admin_check"))
    markup.add(InlineKeyboardButton("👥 Admins", callback_data="admin_manage_admins"), InlineKeyboardButton("🏆 Top Referidos", callback_data="admin_top_refs"))
    markup.add(InlineKeyboardButton("📢 Mensaje Masivo", callback_data="admin_broadcast"), InlineKeyboardButton("🛡️ Panel Baneos", callback_data="admin_bans"))
    markup.add(InlineKeyboardButton("📄 Exportar BD", callback_data="admin_backup"), InlineKeyboardButton("📤 Restaurar BD", callback_data="admin_restore"))
    markup.add(InlineKeyboardButton("📄 Exportar Usuarios", callback_data="admin_export_users"), InlineKeyboardButton("🧹 Limpiar Agotadas", callback_data="admin_clear_dead_cookies"))
    
    # AQUÍ ESTÁ EL BOTÓN DE REVENDEDORES
    markup.add(InlineKeyboardButton("💼 Gestión Resellers", callback_data="admin_reseller_menu"), InlineKeyboardButton("⚙️ Forzar Limpieza", callback_data="admin_clear_cache"))
    
    maint_text = "🔴 Quitar Mantenimiento" if db.get('maintenance_mode', False) else "🟢 Poner Mantenimiento"
    markup.add(InlineKeyboardButton(maint_text, callback_data="admin_toggle_maint"))
    return markup

#def admin_plans_keyboard(db):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✏️ Editar Límite Gratis", callback_data="admin_edit_plan_free"))
    markup.add(InlineKeyboardButton("✏️ Editar Límite VIP", callback_data="admin_edit_plan_vip"))
    markup.add(InlineKeyboardButton("🔙 Volver", callback_data="admin_back_panel"))
    return markup

## ==========================================
# 💼 TECLADOS DE REVENDEDORES (RESELLERS)
# ==========================================
def admin_reseller_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("➕ Añadir/Dar Créditos", callback_data="admin_reseller_add"))
    markup.add(InlineKeyboardButton("📋 Ver Lista Resellers", callback_data="admin_reseller_list"))
    markup.add(InlineKeyboardButton("🔙 Volver al Panel", callback_data="admin_back_panel"))
    return markup

def reseller_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎟️ Crear Cupón 7 Días (Coste: 1 Crédito)", callback_data="reseller_create_7"),
        InlineKeyboardButton("🎟️ Crear Cupón 15 Días (Coste: 2 Créditos)", callback_data="reseller_create_15"),
        InlineKeyboardButton("🎟️ Crear Cupón 30 Días (Coste: 4 Créditos)", callback_data="reseller_create_30"),
        InlineKeyboardButton("📊 Mi Saldo", callback_data="reseller_stats"),
        InlineKeyboardButton("📜 Mi Historial de Cupones", callback_data="reseller_history")
    )
    return markup
