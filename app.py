from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
# Create client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("home.html")

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