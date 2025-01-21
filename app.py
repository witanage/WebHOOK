# from flask import Flask, request, jsonify, render_template, url_for
# import mysql.connector
# import json
# from datetime import datetime
#
# app = Flask(__name__)
#
# # MySQL Database Configuration
# db_config = {
#     "host": "localhost",
#     "user": "root",
#     "password": "",
#     "database": "cwwebhook"
# }
#
# # Home Page: List all Webhooks & Add New Webhooks
# @app.route("/")
# def index():
#     try:
#         conn = mysql.connector.connect(**db_config)
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute("SELECT DISTINCT webhook_id FROM webhook_responses")
#         webhook_ids = [row["webhook_id"] for row in cursor.fetchall()]
#     except mysql.connector.Error as err:
#         return f"Database error: {err}"
#     finally:
#         if conn.is_connected():
#             cursor.close()
#             conn.close()
#
#     return render_template("index.html", webhook_ids=webhook_ids)
#
# # Add a new webhook ID
# @app.route("/add_webhook", methods=["POST"])
# def add_webhook():
#     data = request.json
#     webhook_id = data.get("webhook_id")
#
#     if not webhook_id:
#         return jsonify({"error": "Webhook ID cannot be empty"}), 400
#
#     return jsonify({"message": "Webhook added successfully", "webhook_id": webhook_id})
#
# # Handle Webhooks
# @app.route("/webhook/<webhook_id>", methods=["GET", "POST"])
# def handle_webhook(webhook_id):
#     if request.method == "POST":
#         method = request.method
#         headers = dict(request.headers)
#         body = request.get_json(silent=True) or request.data.decode("utf-8")
#         query_params = request.args.to_dict()
#
#         try:
#             conn = mysql.connector.connect(**db_config)
#             cursor = conn.cursor()
#             cursor.execute("""
#                 INSERT INTO webhook_responses (webhook_id, method, headers, body, query_params, timestamp)
#                 VALUES (%s, %s, %s, %s, %s, %s)
#             """, (webhook_id, method, json.dumps(headers), json.dumps(body), json.dumps(query_params), datetime.utcnow()))
#             conn.commit()
#         except mysql.connector.Error as err:
#             return jsonify({"error": str(err)}), 500
#         finally:
#             if conn.is_connected():
#                 cursor.close()
#                 conn.close()
#
#         return jsonify({"message": "Webhook received and logged successfully"}), 201
#
#     elif request.method == "GET":
#         try:
#             conn = mysql.connector.connect(**db_config)
#             cursor = conn.cursor(dictionary=True)
#             cursor.execute("""
#                 SELECT id, method, headers, body, query_params, timestamp
#                 FROM webhook_responses
#                 WHERE webhook_id = %s
#                 ORDER BY timestamp DESC
#             """, (webhook_id,))
#             data = cursor.fetchall()
#         except mysql.connector.Error as err:
#             return jsonify({"error": str(err)}), 500
#         finally:
#             if conn.is_connected():
#                 cursor.close()
#                 conn.close()
#
#         return jsonify(data), 200
#
# if __name__ == "__main__":
#     app.run(debug=False)

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import mysql.connector
import bcrypt
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# MySQL Database Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "cwwebhook"
}

# User Authentication - Login
@app.route("/", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
            else:
                return render_template("login.html", error="Invalid username or password")

        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    return render_template("login.html")

# User Logout
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

# Dashboard - Webhook Viewer (Protected)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Fetch available webhook IDs
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT webhook_id FROM webhook_responses")
        webhook_ids = [row[0] for row in cursor.fetchall()]
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template("index.html", webhook_ids=webhook_ids)

# User Registration - Only for Admins (For Testing Purposes)
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            return redirect(url_for("login"))
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    return render_template("register.html")

# Add a new webhook ID
@app.route("/add_webhook", methods=["POST"])
def add_webhook():
    data = request.json
    webhook_id = data.get("webhook_id")

    if not webhook_id:
        return jsonify({"error": "Webhook ID cannot be empty"}), 400

    return jsonify({"message": "Webhook added successfully", "webhook_id": webhook_id})

# Handle Webhooks
@app.route("/webhook/<webhook_id>", methods=["GET", "POST"])
def handle_webhook(webhook_id):
    if request.method == "POST":
        method = request.method
        headers = dict(request.headers)
        body = request.get_json(silent=True) or request.data.decode("utf-8")
        query_params = request.args.to_dict()

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO webhook_responses (webhook_id, method, headers, body, query_params, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (webhook_id, method, json.dumps(headers), json.dumps(body), json.dumps(query_params), datetime.utcnow()))
            conn.commit()
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

        return jsonify({"message": "Webhook received and logged successfully"}), 201

    elif request.method == "GET":
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, method, headers, body, query_params, timestamp
                FROM webhook_responses
                WHERE webhook_id = %s
                ORDER BY timestamp DESC
            """, (webhook_id,))
            data = cursor.fetchall()
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

        return jsonify(data), 200

if __name__ == "__main__":
    app.run(debug=False)
