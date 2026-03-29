from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
CORS(app)

# =========================
# ⚙️ CONFIG
# =========================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'supersecretkey'

# INIT
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# =========================
# 👤 USER MODEL
# =========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

# =========================
# 💬 MESSAGE MODEL
# =========================
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50))
    text = db.Column(db.String(500))


# =========================
# 🌐 PAGE ROUTES (IMPORTANT)
# =========================

@app.route("/")
def root():
    return render_template("signup.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/home")
def home_page():
    return render_template("home.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")


# =========================
# 🔐 AUTH ROUTES
# =========================

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json

    existing = User.query.filter(
        (User.email == data["email"]) | (User.username == data["username"])
    ).first()

    if existing:
        return jsonify({"msg": "User already exists"}), 400

    hashed = bcrypt.generate_password_hash(data["password"]).decode('utf-8')

    user = User(
        username=data["username"],
        email=data["email"],
        password=hashed
    )

    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=user.username)

    return jsonify({"token": token})


@app.route("/login", methods=["POST"])
def login():
    data = request.json

    user = User.query.filter_by(email=data["email"]).first()

    if not user:
        return jsonify({"msg": "User not found"}), 404

    if not bcrypt.check_password_hash(user.password, data["password"]):
        return jsonify({"msg": "Wrong password"}), 401

    token = create_access_token(identity=user.username)

    return jsonify({"token": token})


# =========================
# ⚡ REAL-TIME CHAT
# =========================

@socketio.on("send_message")
def handle_message(data):
    username = data["sender"]
    text = data["text"]

    msg = Message(sender=username, text=text)
    db.session.add(msg)
    db.session.commit()

    emit("receive_message", {
        "sender": username,
        "text": text
    }, broadcast=True)


# =========================
# 🚀 RUN (RENDER FIX)
# =========================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("DB ready 😤")

    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)