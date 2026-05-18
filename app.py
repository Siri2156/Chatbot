from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
# Create client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret")

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

        # Basic login handling - accept any credentials for demo
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

        # Basic signup handling - store no data for demo
        flash("Signup successful. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/chatbot")
def chatbot():
    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    try:
        user_message = request.json.get("message", "").strip()

        if not user_message:
            return jsonify({"reply": "Please send a valid message."})

        # Generate response
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=user_message
        )

        reply = response.text if hasattr(response, "text") else "No response"

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)