import mysql.connector
from dotenv import load_dotenv
import os
import traceback
import time

load_dotenv()

print("Loading database SQL file...")
# Read SQL file
with open("database.sql", "r", encoding="utf-8") as f:
    sql_script = f.read()

# Connect to MySQL
print(f"Connecting to MySQL at {os.getenv('DB_HOST', 'localhost')}...")
print("(This may take a moment...)")

max_retries = 3
for attempt in range(max_retries):
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            connection_timeout=10,
            autocommit=False
        )
        print("✅ Connected to MySQL!")
        cursor = conn.cursor()
        
        # Execute each SQL statement
        for statement in sql_script.split(';'):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except Exception as e:
                    print(f"⚠️  Statement failed (may be normal): {statement[:40]}...")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("\n✅ Database initialized successfully!")
        break
        
    except Exception as e:
        attempt_num = attempt + 1
        print(f"\n❌ Attempt {attempt_num}/{max_retries} failed: {e}")
        if attempt < max_retries - 1:
            print("Retrying in 2 seconds...")
            time.sleep(2)
        else:
            print("\n❌ Failed to initialize database after all retries")
            traceback.print_exc()
