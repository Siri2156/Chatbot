from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
from dotenv import load_dotenv
import os
import pymysql
import time

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = int(os.getenv("DB_PORT") or 3306)
DB_NAME = os.getenv("DB_NAME", "quickgpt")

# Create client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret")


def get_db_connection(use_db=True):
    config = {
        "host": DB_HOST,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "port": DB_PORT,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor
    }

    if use_db:
        config["database"] = DB_NAME

    return pymysql.connect(**config)


def init_db():
    try:
        conn = get_db_connection(use_db=False)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4")
        cursor.close()
        conn.close()
    except pymysql.Error as err:
        print("Database creation failed:", err)
        return
    create_tables()


def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chat_id INT NOT NULL,
            sender ENUM('user','bot') NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    cursor.close()
    conn.close()


def setup_database():
    print("Inside setup_database()")

    try:
        print("Trying MySQL connection...")

        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )

        print("MySQL connected successfully")

        cursor = conn.cursor()

        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`"
        )

        conn.commit()

        print("Database created/check complete")

        cursor.close()
        conn.close()

        print("Connection closed")

        create_tables()

    except Exception as e:
        print("DATABASE EXCEPTION OCCURRED")
        print(type(e))
        print(e)

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def create_chat(user_id, title="New Chat"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chats (user_id, title) VALUES (%s, %s)",
        (user_id, title),
    )
    chat_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return chat_id

@app.route("/")
def index():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, password FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        flash("Login successful. Welcome back!", "success")
        return redirect(url_for("chatbot"))

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not name or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template("signup.html")

        hashed_password = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except pymysql.err.IntegrityError:
            flash("This email is already registered.", "danger")
            return render_template("signup.html")

        flash("Signup successful. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/chatbot")
def chatbot():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user = get_current_user()
    return render_template("chat.html", user=user)

@app.route("/recent-chats")
def recent_chats():
    user = get_current_user()
    if not user:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at FROM chats WHERE user_id = %s ORDER BY created_at DESC LIMIT 15",
        (user["id"],),
    )
    chats = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(chats)

@app.route("/new-chat", methods=["POST"])
def new_chat():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401

    title = request.json.get("title", "New Chat").strip() or "New Chat"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chats (user_id, title) VALUES (%s, %s)",
        (user["id"], title),
    )
    chat_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"chat_id": chat_id, "title": title})

@app.route("/chat-messages/<int:chat_id>")
def chat_messages(chat_id):
    user = get_current_user()
    if not user:
        return jsonify([]), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM chats WHERE id = %s AND user_id = %s",
        (chat_id, user["id"]),
    )
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify([]), 404

    cursor.execute(
        "SELECT sender, message, created_at FROM messages WHERE chat_id = %s ORDER BY created_at ASC",
        (chat_id,),
    )
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(messages)

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    user = get_current_user()

    if not user:
        return jsonify({"reply": "Authentication required."}), 401

    try:
        data = request.get_json() or {}

        user_message = data.get("message", "").strip()
        chat_id = data.get("chat_id")

        if not user_message:
            return jsonify({
                "reply": "Please send a valid message."
            }), 400

        # -------------------------------------------------
        # STEP 1: Validate/create chat and save user message
        # -------------------------------------------------
        conn = get_db_connection()
        cursor = conn.cursor()

        if chat_id:
            cursor.execute(
                """
                SELECT id
                FROM chats
                WHERE id = %s AND user_id = %s
                """,
                (chat_id, user["id"])
            )

            if not cursor.fetchone():
                cursor.close()
                conn.close()

                return jsonify({
                    "reply": "Chat not found."
                }), 404

        else:
            cursor.execute(
                """
                INSERT INTO chats (user_id, title)
                VALUES (%s, %s)
                """,
                (user["id"], "New Chat")
            )

            chat_id = cursor.lastrowid

        # Save user's message
        cursor.execute(
            """
            INSERT INTO messages (chat_id, sender, message)
            VALUES (%s, %s, %s)
            """,
            (chat_id, "user", user_message)
        )

        conn.commit()

        # Close database before calling Gemini
        cursor.close()
        conn.close()

        # -------------------------------------------------
        # STEP 2: Ask Gemini with retry
        # -------------------------------------------------
        reply = None

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=user_message
                )

                reply = response.text if response.text else "No response received."
                break

            except Exception as gemini_error:
                print(f"Gemini attempt {attempt + 1} failed:")
                print(type(gemini_error).__name__)
                print(str(gemini_error))

                if attempt < 2:
                    time.sleep(3)
                else:
                    raise gemini_error

        # -------------------------------------------------
        # STEP 3: Save Gemini response using new connection
        # -------------------------------------------------
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO messages (chat_id, sender, message)
            VALUES (%s, %s, %s)
            """,
            (chat_id, "bot", reply)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "reply": reply,
            "chat_id": chat_id
        })

    except Exception as e:
        print("========== CHAT ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        print("================================")

        return jsonify({
            "reply": f"Error: {str(e)}"
        }), 500
    
@app.route("/delete-chat", methods=["POST"])
def delete_chat():

    user = get_current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    chat_id = data.get("chat_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM chats
        WHERE id = %s AND user_id = %s
        """,
        (chat_id, user["id"])
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"success": True})

@app.route("/update-chat-title", methods=["POST"])
def update_chat_title():

    user = get_current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    chat_id = data.get("chat_id")
    title = data.get("title", "New Chat")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE chats
        SET title = %s
        WHERE id = %s AND user_id = %s
        """,
        (title, chat_id, user["id"])
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"success": True})


setup_database()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)