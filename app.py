from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google import genai
from dotenv import load_dotenv
from flask_cors import CORS
import os
import mysql.connector

load_dotenv(dotenv_path=".env")
# Create client
try:
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY missing in .env")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client = None

if not os.getenv("FLASK_SECRET_KEY"):
    raise ValueError("FLASK_SECRET_KEY missing in .env")

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Sridhanya@2156",
        database="quickgpt",
        connection_timeout=5
    )

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return "Passwords do not match!"

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                           (name, email, password))

            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for("login"))
        except Exception as e:
            return f"Database error: {str(e)}"

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                return redirect(url_for("chatbot"))
            else:
                return "Invalid Email or Password!"
        except Exception as e:
            return f"Database error: {str(e)}"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/chatbot")
def chatbot():
    try:
        print("ENTERED CHATBOT")

        if "user_id" not in session:
            return redirect(url_for("login"))

        user_id = session["user_id"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM chats WHERE user_id=%s ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        )

        recent_chats = cursor.fetchall()

        print("Recent chats:", recent_chats)

        if len(recent_chats) == 0:
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
        print("CHATBOT ERROR:", e)
        return f"CHATBOT ERROR: {str(e)}"

@app.route("/new_chat", methods=["POST"])
def new_chat():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    title = request.json.get("title", "New Chat")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO chats (user_id, title) VALUES (%s, %s)", (user_id, title))
        conn.commit()

        chat_id = cursor.lastrowid

        cursor.close()
        conn.close()

        return jsonify({"chat_id": chat_id})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/load_chat/<int:chat_id>")
def load_chat(chat_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM chats WHERE id=%s AND user_id=%s", (chat_id, user_id))
        chat = cursor.fetchone()

        if not chat:
            return "Chat not found"

        cursor.execute("SELECT sender, message FROM messages WHERE chat_id=%s ORDER BY created_at ASC", (chat_id,))
        messages = cursor.fetchall()

        cursor.execute("SELECT * FROM chats WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (user_id,))
        recent_chats = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("chat.html",
                               username=session["user_name"],
                               recent_chats=recent_chats,
                               messages=messages,
                               active_chat_id=chat_id)
    except Exception as e:
        return f"Database error: {str(e)}"
@app.route("/test_db")
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"MySQL Connected Successfully ✅ Result = {result}"
    except Exception as e:
        return f"MySQL Connection Failed ❌ Error: {str(e)}"
@app.route("/chat", methods=["POST"])
def chat_endpoint():
    if "user_id" not in session:
        return jsonify({"reply": "Unauthorized. Please login first."})

    user_message = request.json.get("message", "").strip()
    chat_id = request.json.get("chat_id")

    if not user_message:
        return jsonify({"reply": "Please send a valid message."})

    if chat_id is None:
        return jsonify({"reply": "No chat selected. Please create a new chat first."})

    if client is None:
        reply = "AI service is not available. Please check the API key."
    else:
        # Generate AI response
        try:
           response = client.models.generate_content(
           model="gemini-1.5-flash-latest",
           contents=user_message
           )
           reply = getattr(response, "text", "No response from AI.")
        except Exception as e:
           print("Gemini Error:", e)
           reply = "⚠️ AI is busy or unavailable. Try again."

    # Save messages to DB
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

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"reply": f"Failed to save message. Error: {str(e)}"})

    return jsonify({"reply": reply})
    
@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )