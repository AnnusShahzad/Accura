import sqlite3
import sys

db_path = "accura_dev.db"
email = "talhafarooqgtx960@gmail.com"

try:
    conn = sqlite3.connect(db_path, timeout=5)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id, username FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if not user:
        print(f"No user found with email: {email}")
        sys.exit(0)
        
    user_id = user[0]
    
    # Delete associated profile
    cursor.execute("DELETE FROM user_profiles WHERE user = ?", (user_id,))
    
    # Delete associated settings
    cursor.execute("DELETE FROM user_settings WHERE user = ?", (user_id,))
    
    # Delete user
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    
    conn.commit()
    print(f"Successfully deleted user {user[1]} ({email}) and their profile/settings.")
    
except sqlite3.OperationalError as e:
    if "database is locked" in str(e).lower():
        print("ERROR: The database is locked. Please stop your backend server (Ctrl+C) and run this script again.")
    else:
        print(f"Database error: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if 'conn' in locals():
        conn.close()
