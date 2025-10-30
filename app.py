from flask import Flask, request, redirect, session, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from instagrapi import Client
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = 'insane'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///birthdays.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# -------------------- MODELS -------------------- #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    birthdays = db.relationship("Birthday", backref="user", lazy=True)


class Birthday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(150), nullable=False)
    birthday = db.Column(db.String(10), nullable=False)
    wished = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


with app.app_context():
    db.create_all()


# -------------------- AUTO SEND FUNCTION -------------------- #
def auto_send_wishes():
    with app.app_context():
        today = datetime.now().strftime("%m-%d")
        users = User.query.all()

        for user in users:
            birthdays = Birthday.query.filter_by(user_id=user.id, wished=False).all()

            if birthdays:
                try:
                    c1 = Client()
                    c1.login(user.username, user.password)

                    for person in birthdays:
                        if person.birthday[5:] == today:
                            messages = [
                                f"Happy Birthday {person.name}! 🎉 Wishing you a day filled with love, laughter, and unforgettable moments!",
                                f"Cheers to another year of amazing adventures, {person.name}! 🎂 May all your dreams come true!",
                                f"Happy Birthday {person.name}! 🎈 Hope your special day is as wonderful as you are!",
                                f"Another year wiser, another year brighter! Happy Birthday {person.name}! ✨",
                                f"Wishing you the happiest of birthdays, {person.name}! 🎊 May this year bring you endless joy!",
                                f"Happy Birthday {person.name}! 🎁 Here's to celebrating YOU and all the happiness you bring!",
                                f"It's your special day, {person.name}! 🥳 Make it count and enjoy every moment!",
                                f"Happy Birthday to someone who makes the world brighter! 🌟 Have an amazing day, {person.name}!"
                            ]

                            try:
                                import random
                                msg = random.choice(messages)
                                c1.direct_send(msg, [c1.user_id_from_username(person.username)])
                                person.wished = True
                                print(f"Wished {person.username}")
                            except Exception as e:
                                print(f"Failed to send wish to {person.username}: {e}")

                    db.session.commit()

                except Exception as e:
                    print(f"Login failed for {user.username}: {e}")


# -------------------- SCHEDULER -------------------- #
scheduler = BackgroundScheduler()
scheduler.add_job(func=auto_send_wishes, trigger="cron", hour=19, minute=1)
scheduler.start()



@app.route('/')
def home():
    if "user_id" not in session:
        session.pop("user_id", None)
        return redirect("/login")

    user = User.query.get(session["user_id"])
    birthdays = Birthday.query.filter_by(user_id=user.id).all()
    return render_template("index.html", user=user, birthdays=birthdays)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            import os
            c1 = Client()

            if os.path.exists("session.json"):
                print("🔁 Loading existing session...")
                c1.load_settings("session.json")
                c1.login(username, password)
            else:
                print("🆕 Logging in for the first time...")
                c1.login(username, password)
                c1.dump_settings("session.json")

        except Exception as e:
            print("LOGIN ERROR:", e)
            return redirect("/login")

        user = User.query.filter_by(username=username).first()

        if not user:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            print("User created and logged in")
        else:
            user.password = password
            db.session.commit()

        session["user_id"] = user.id
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/login")


@app.route("/add-birthday", methods=["POST"])
def add_birthday():
    if "user_id" not in session:
        return redirect("/login")

    name = request.form["name"]
    username = request.form["username"]
    birthday = request.form["birthday"]

    birthday_entry = Birthday(
        name=name,
        username=username,
        birthday=birthday,
        user_id=session["user_id"]
    )

    db.session.add(birthday_entry)
    db.session.commit()
    return redirect("/")


if __name__ == '__main__':
    auto_send_wishes()
    app.run(debug=True)