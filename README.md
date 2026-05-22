# 🤖 QuickGPT – AI Chatbot using Flask, Gemini API & MySQL

QuickGPT is a modern AI-powered chatbot application built using **Flask**, **Google Gemini API**, and **MySQL**.

It provides a beautiful real-time chat experience with authentication, chat history management, recent chats, animated UI, and database integration.

---

# ✨ Features

* 💬 Real-time AI chat responses
* 🧠 Powered by Google Gemini API
* 🔐 User Authentication (Signup/Login/Logout)
* 🗂️ Chat history stored in MySQL database
* 📌 Recent chat sidebar
* ✏️ Auto chat title generation
* 🗑️ Delete chat functionality
* ⚡ Typing animation
* 🎨 Modern responsive UI
* 📱 Mobile-friendly layout
* 🔄 Persistent conversations
* 🌈 Beautiful gradient interface

---

# 🛠️ Tech Stack

## Backend

* Python
* Flask
* MySQL
* Flask Sessions

## AI

* Google Gemini API

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript
* jQuery

## Database

* MySQL

## Deployment

* Render
* Railway

---

# 📂 Project Structure

```bash
ChatBot/
│
├── app.py
├── requirements.txt
├── .env
├── templates/
│   ├── home.html
│   ├── login.html
│   ├── signup.html
│   └── chat.html
│
├── database.sql
│
└── README.md
```

---

# ⚙️ Installation & Setup

## 1️⃣ Clone Repository

```bash
git clone https://github.com/Siri2156/chatbot.git

cd chatbot
```

---

## 2️⃣ Create Virtual Environment

### Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

### Mac/Linux

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🗄️ MySQL Database Setup

Make sure MySQL Server is installed and running.

Create a database manually OR let the app create it automatically.

Default database name:

```sql
quickgpt
```

# ▶️ Run the Application

```bash
python app.py
```

Open browser:

```bash
http://127.0.0.1:5000
```

---

# 🧩 Database Tables

The application automatically creates these tables:

## Users Table

Stores:

* User accounts
* Email
* Password hashes

## Chats Table

Stores:

* Chat titles
* User chat sessions

## Messages Table

Stores:

* User messages
* AI responses
* Chat history

---

# 🌐 Application Pages

| Route                | Description          |
| -------------------- | -------------------- |
| `/`                  | Home page            |
| `/signup`            | User registration    |
| `/login`             | User login           |
| `/logout`            | Logout               |
| `/chatbot`           | AI chatbot interface |
| `/recent-chats`      | Fetch recent chats   |
| `/chat`              | Send messages        |
| `/delete-chat`       | Delete chat          |
| `/update-chat-title` | Rename chat          |

---

# 🎨 UI Features

* Glassmorphism inspired design
* Gradient backgrounds
* Smooth animations
* Scrollable chat interface
* Responsive sidebar
* Dropdown chat actions
* Typing indicator animation

---

# 📸 Screenshots

## 🏠 Home Page

Add screenshot here:

```md
![Home](images/home.png)
```

## 💬 Chat Interface

```md
![Chat](images/chat.png)
```

---

# 🔒 Security Features

* Password hashing using Werkzeug
* Session-based authentication
* Environment variable protection
* SQL parameterized queries
* Secure user validation

---

## 4️⃣ Deployed 🚀

AI chatbot deployed on render
https://chatbot-2kvj.onrender.com/

---

# 💡 Future Improvements

* 🌍 Multi-language support
* ⚡ Streaming AI responses
* 📎 File upload support
* 🎤 Voice chat
* 🌙 Dark/Light mode toggle
* 📱 Mobile application
* 🤝 Share chats
* 📌 Pin chats
* 🗂️ Archive chats
* 🔍 Search conversations

---

# 👨‍💻 Author

GitHub:

https://github.com/Siri2156

---

# ⭐ Support

If you like this project, give it a ⭐ on GitHub and share it with others.

---

# 📜 License

This project is licensed under the MIT License.
