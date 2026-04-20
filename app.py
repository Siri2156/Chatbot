from flask import Flask, render_template, request, jsonify, redirect, url_for
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
# Create client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # TEMP validation (replace with database later)
        if email == "admin@gmail.com" and password == "1234":
            return redirect(url_for("chatbot"))
        else:
            return "Invalid Login"

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # TEMP registration (replace with database later)
        if email and password:
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
        return jsonify({"reply": f"Error: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)