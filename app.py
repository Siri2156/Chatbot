
import os
import uuid
import traceback
from datetime import timedelta

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_cors import CORS
from google import genai
from mysql.connector import pooling
from mysql.connector.errors import Error
from werkzeug.security import check_password_hash, generate_password_hash

# =========================================================
# LOAD ENV VARIABLES
# =========================================================

load_dotenv()

# =========================================================
# FLASK CONFIG
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

CORS(app)

# =========================================================
# GEMINI CONFIG
# =========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# =========================================================
# MYSQL CONNECTION POOL
# =========================================================

try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="quickgpt_pool",
        pool_size=10,
        pool_reset_session=True,
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
    )

    print("✅ MySQL Connection Pool Created")

except Exception as e:
    print("❌ Database Pool Error:")
    print(str(e))
    raise

# =========================================================
# DATABASE CONNECTION
# =========================================================


def get_db_connection():
    return db_pool.get_connection()


# =========================================================
# DATABASE INIT
# =========================================================


def initialize_database():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # USERS TABLE
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # CHATS TABLE
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(255) DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
            )
            """
        )

        # MESSAGES TABLE
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                chat_id INT NOT NULL,
                sender VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id)
                ON DELETE CASCADE
            )
            """
        )

        conn.commit()

        print("✅ Database initialized")

    except Exception as e:
        print("❌ Database Initialization Error")
        print(str(e))

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


initialize_database()

# =========================================================
# HELPER FUNCTIONS
# =========================================================


def logged_in():
    return "user_id" in session



def generate_chat_title(message):
    title = message[:40].strip()

    if len(message) > 40:
        title += "..."

    return title


# =========================================================
# HOME
# =========================================================


@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# SIGNUP
# =========================================================


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    conn = None
    cursor = None

    try:
        data = request.get_json()

        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not username or not email or not password:
            return jsonify({"error": "All fields required"}), 400

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # CHECK EXISTING USER
        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (email,),
        )

        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({"error": "Email already exists"}), 409

        # CREATE USER
        cursor.execute(
            """
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
            """,
            (username, email, hashed_password),
        )

        conn.commit()

        return jsonify(
            {
                "success": True,
                "message": "Signup successful",
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# LOGIN
# =========================================================


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    conn = None
    cursor = None

    try:
        data = request.get_json()

        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,),
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        if not check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid email or password"}), 401

        session.permanent = True
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return jsonify(
            {
                "success": True,
                "redirect": "/chatbot",
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# LOGOUT
# =========================================================


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================================================
# CHATBOT MAIN
# =========================================================


@app.route("/chatbot")
def chatbot():
    if not logged_in():
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        user_id = session["user_id"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM chats
            WHERE user_id=%s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        )

        latest_chat = cursor.fetchone()

        if not latest_chat:
            cursor.execute(
                """
                INSERT INTO chats (user_id, title)
                VALUES (%s, %s)
                """,
                (user_id, "New Chat"),
            )

            conn.commit()

            latest_chat_id = cursor.lastrowid

        else:
            latest_chat_id = latest_chat["id"]

        return redirect(url_for("load_chat", chat_id=latest_chat_id))

    except Exception as e:
        traceback.print_exc()
        return f"Chatbot Error: {str(e)}", 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# CREATE NEW CHAT
# =========================================================


@app.route("/new_chat", methods=["POST"])
def new_chat():
    if not logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    conn = None
    cursor = None

    try:
        user_id = session["user_id"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO chats (user_id, title) VALUES (%s, %s)",
            (user_id, "New Chat"),
        )

        conn.commit()

        chat_id = cursor.lastrowid

        return jsonify(
            {
                "success": True,
                "chat_id": chat_id,
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# LOAD CHAT
# =========================================================


@app.route("/chat/<int:chat_id>")
def load_chat(chat_id):
    if not logged_in():
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        user_id = session["user_id"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # VERIFY CHAT OWNERSHIP
        cursor.execute(
            "SELECT * FROM chats WHERE id=%s AND user_id=%s",
            (chat_id, user_id),
        )

        chat = cursor.fetchone()

        if not chat:
            return "Chat not found", 404

        # LOAD ALL CHATS
        cursor.execute(
            """
            SELECT *
            FROM chats
            WHERE user_id=%s
            ORDER BY created_at DESC
            """,
            (user_id,),
        )

        chats = cursor.fetchall()

        # LOAD MESSAGES
        cursor.execute(
            """
            SELECT sender, message, created_at
            FROM messages
            WHERE chat_id=%s
            ORDER BY created_at ASC
            """,
            (chat_id,),
        )

        messages = cursor.fetchall()

        return render_template(
            "chatbot.html",
            chats=chats,
            messages=messages,
            active_chat=chat_id,
            username=session.get("username"),
        )

    except Exception as e:
        traceback.print_exc()
        return f"Load Chat Error: {str(e)}", 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# AI MESSAGE API
# =========================================================


@app.route("/send_message", methods=["POST"])
def send_message():
    if not logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    conn = None
    cursor = None

    try:
        data = request.get_json()

        user_message = data.get("message", "").strip()
        chat_id = data.get("chat_id")

        if not user_message:
            return jsonify({"error": "Message required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # VERIFY CHAT OWNERSHIP
        cursor.execute(
            "SELECT * FROM chats WHERE id=%s AND user_id=%s",
            (chat_id, session["user_id"]),
        )

        chat = cursor.fetchone()

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        # SAVE USER MESSAGE
        cursor.execute(
            """
            INSERT INTO messages (chat_id, sender, message)
            VALUES (%s, %s, %s)
            """,
            (chat_id, "user", user_message),
        )

        # AUTO UPDATE CHAT TITLE
        if chat["title"] == "New Chat":
            title = generate_chat_title(user_message)

            cursor.execute(
                "UPDATE chats SET title=%s WHERE id=%s",
                (title, chat_id),
            )

        conn.commit()

        # GEMINI RESPONSE
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
        )

        ai_message = response.text

        # SAVE AI MESSAGE
        cursor.execute(
            """
            INSERT INTO messages (chat_id, sender, message)
            VALUES (%s, %s, %s)
            """,
            (chat_id, "assistant", ai_message),
        )

        conn.commit()

        return jsonify(
            {
                "success": True,
                "response": ai_message,
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# DELETE CHAT
# =========================================================


@app.route("/delete_chat/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    if not logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM chats WHERE id=%s AND user_id=%s",
            (chat_id, session["user_id"]),
        )

        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# HEALTH CHECK
# =========================================================


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "running",
            "service": "QuickGPT AI",
        }
    )


# =========================================================
# TEST DATABASE
# =========================================================


@app.route("/test_db")
def test_db():
    conn = None

    try:
        conn = get_db_connection()

        if conn.is_connected():
            return "✅ MySQL Connected Successfully"

        return "❌ Database not connected"

    except Error as e:
        return f"❌ Database Error: {str(e)}"

    finally:
        if conn:
            conn.close()


# =========================================================
# ERROR HANDLERS
# =========================================================


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Page not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# =========================================================
# RUN SERVER
# =========================================================


if __name__ == "__main__":
    print("Starting Flask Server...")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )