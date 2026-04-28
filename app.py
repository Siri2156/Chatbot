from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google import genai
from dotenv import load_dotenv
from flask_cors import CORS
import os
import mysql.connector

load_dotenv(dotenv_path=".env")

# Initialize Gemini client
try:
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY missing in .env")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"[WARNING] Gemini client init failed: {e}")
    client = None

if not os.getenv("FLASK_SECRET_KEY"):
    raise ValueError("FLASK_SECRET_KEY missing in .env")

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

@app.after_request
def add_headers(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    return response

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "quickgpt"),
        connection_timeout=5
    )

# ─── Auth Routes ────────────────────────────────────────────────────────────

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("chatbot"))
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, password)
                )
                conn.commit()
                cursor.close()
                conn.close()
                return redirect(url_for("login"))
            except mysql.connector.IntegrityError:
                error = "An account with this email already exists."
            except Exception as e:
                error = f"Database error: {str(e)}"

    return render_template("signup.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM users WHERE email=%s AND password=%s",
                (email, password)
            )
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                return redirect(url_for("chatbot"))
            else:
                error = "Invalid email or password."
        except Exception as e:
            error = f"Database error: {str(e)}"

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── Chat Routes ─────────────────────────────────────────────────────────────

@app.route("/chatbot")
def chatbot():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM chats WHERE user_id=%s ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        )
        recent_chats = cursor.fetchall()

        if not recent_chats:
            cursor.execute(
                "INSERT INTO chats (user_id, title) VALUES (%s, %s)",
                (user_id, "New Chat")
            )
            conn.commit()
            new_chat_id = cursor.lastrowid
            cursor.close()
            conn.close()
            return redirect(url_for("load_chat", chat_id=new_chat_id))

        latest_chat_id = recent_chats[0]["id"]
        cursor.close()
        conn.close()
        return redirect(url_for("load_chat", chat_id=latest_chat_id))

    except Exception as e:
        return f"<h2>Database Error</h2><p>{str(e)}</p>", 500

@app.route("/new_chat", methods=["POST"])
def new_chat():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    title = request.json.get("title", "New Chat")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chats (user_id, title) VALUES (%s, %s)",
            (user_id, title)
        )
        conn.commit()
        chat_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({"chat_id": chat_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/load_chat/<int:chat_id>")
def load_chat(chat_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM chats WHERE id=%s AND user_id=%s",
            (chat_id, user_id)
        )
        chat = cursor.fetchone()
        if not chat:
            cursor.close()
            conn.close()
            return redirect(url_for("chatbot"))

        cursor.execute(
            "SELECT sender, message FROM messages WHERE chat_id=%s ORDER BY created_at ASC",
            (chat_id,)
        )
        messages = cursor.fetchall()

        cursor.execute(
            "SELECT * FROM chats WHERE user_id=%s ORDER BY created_at DESC LIMIT 15",
            (user_id,)
        )
        recent_chats = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "chat.html",
            username=session["user_name"],
            recent_chats=recent_chats,
            messages=messages,
            active_chat_id=chat_id
        )
    except Exception as e:
        return f"<h2>Error</h2><p>{str(e)}</p>", 500

@app.route("/delete_chat/<int:chat_id>", methods=["POST"])
def delete_chat(chat_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM chats WHERE id=%s AND user_id=%s",
            (chat_id, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/rename_chat/<int:chat_id>", methods=["POST"])
def rename_chat(chat_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    new_title = request.json.get("title", "Chat")[:80]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chats SET title=%s WHERE id=%s AND user_id=%s",
            (new_title, chat_id, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    if "user_id" not in session:
        return jsonify({"reply": "Unauthorized. Please login first."})

    user_message = request.json.get("message", "").strip()
    chat_id = request.json.get("chat_id")
    history = request.json.get("history", [])

    if not user_message:
        return jsonify({"reply": "Please send a valid message."})
    if not chat_id:
        return jsonify({"reply": "No active chat. Please create a new chat."})

    # Build conversation context for Gemini
    if client is None:
        reply = "AI service unavailable. Please check your GEMINI_API_KEY in .env"
    else:
        try:
            # Build full conversation for context
            conversation_text = ""
            for msg in history[-10:]:  # last 10 messages for context
                role = "User" if msg["sender"] == "user" else "Assistant"
                conversation_text += f"{role}: {msg['message']}\n"
            conversation_text += f"User: {user_message}"

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=conversation_text
            )
            reply = response.text if hasattr(response, "text") else "No response generated."
        except Exception as e:
            reply = f"Sorry, I couldn't generate a response. Error: {str(e)}"

    # Save to DB
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (chat_id, sender, message) VALUES (%s, %s, %s)",
            (chat_id, "user", user_message)
        )
        cursor.execute(
            "INSERT INTO messages (chat_id, sender, message) VALUES (%s, %s, %s)",
            (chat_id, "bot", reply)
        )
        # Auto-title the chat from first message
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id=%s", (chat_id,)
        )
        count = cursor.fetchone()[0]
        if count <= 2:
            auto_title = user_message[:50] + ("…" if len(user_message) > 50 else "")
            cursor.execute(
                "UPDATE chats SET title=%s WHERE id=%s",
                (auto_title, chat_id)
            )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"reply": reply, "db_error": str(e)})

    return jsonify({"reply": reply})

@app.route("/test_db")
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"✅ MySQL Connected — Version: {version[0]}"
    except Exception as e:
        return f"❌ MySQL Failed: {str(e)}"

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True, use_reloader=False)
