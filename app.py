from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import mysql.connector
import bcrypt
import json
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# MySQL Database Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "cwwebhook"
}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


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

            if user:
                # Check if the user is enabled
                if user.get("status") == 0:  # Assuming 0 means disabled
                    return render_template("login.html", error="Your account is disabled. Please contact support.")

                # Check the password
                if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
                    session["user_id"] = user["id"]
                    return redirect(url_for("dashboard"))

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
@login_required
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

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

    return render_template("index.html", webhook_ids=webhook_ids, user_id=user_id)


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
            cursor.execute("INSERT INTO users (username, password_hash, status) VALUES (%s, %s, 0)",
                           (username, hashed_password))
            conn.commit()
            return redirect(url_for("login"))
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    return render_template("register.html")


@app.route("/mark_as_read/<int:request_id>", methods=["POST"])
@login_required
def mark_as_read(request_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE webhook_responses
            SET is_read = 1
            WHERE id = %s AND user_id = %s
        """, (request_id, session["user_id"]))
        conn.commit()
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return jsonify({"message": "Request marked as read"}), 200


@app.route("/webhook/<user_id>/<webhook_id>", methods=["GET", "POST"])
def handle_webhook(user_id, webhook_id):
    if request.method == "POST":
        # Validate if the user exists
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            # Check if the user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"error": "User does not exist"}), 404

            # Process the webhook data
            method = request.method
            headers = dict(request.headers)
            body = request.get_json(silent=True) or request.data.decode("utf-8")
            query_params = request.args.to_dict()

            # Store the webhook response in the database
            cursor.execute("""
                INSERT INTO webhook_responses (user_id, webhook_id, method, headers, body, query_params, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, webhook_id, method, json.dumps(headers), json.dumps(body), json.dumps(query_params),
                  datetime.utcnow()))
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
                    SELECT id, method, headers, body, query_params, timestamp, is_read
                    FROM webhook_responses
                    WHERE user_id = %s AND webhook_id = %s
                    ORDER BY timestamp DESC
                """, (user_id, webhook_id))
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
