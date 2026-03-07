import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "accura_dev.db")
print(f"Connecting to {db_path}...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN otp_code VARCHAR(6) DEFAULT '';")
    print("Added otp_code column.")
except sqlite3.OperationalError as e:
    print(f"otp_code column might already exist: {e}")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN otp_expires_at TIMESTAMP NULL;")
    print("Added otp_expires_at column.")
except sqlite3.OperationalError as e:
    print(f"otp_expires_at column might already exist: {e}")

conn.commit()
conn.close()
print("Done!")
