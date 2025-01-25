import sqlite3

def add_phone_code_hash_column():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Tambahkan kolom baru ke tabel users
    try:
        c.execute('ALTER TABLE users ADD COLUMN phone_code_hash TEXT')
        print("Kolom phone_code_hash berhasil ditambahkan.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")

    conn.commit()
    conn.close()

add_phone_code_hash_column()
