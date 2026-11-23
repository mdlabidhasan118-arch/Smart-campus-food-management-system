import os
from flask import Flask, render_template, redirect, url_for, flash, session, request
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from config import Config
from db import get_db, init_db
from auth import auth_bp
from student import student_bp
from owner import owner_bp
from admin import admin_bp

load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(owner_bp, url_prefix="/owner")
app.register_blueprint(admin_bp, url_prefix="/admin")

@app.context_processor
def inject_globals():
    return {"current_user": session.get("user")}


@app.route("/")
def home():
    db = get_db()
    cur = db.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT
                c.id AS canteen_id,
                c.name,
                c.location,
                c.description,

                COUNT(
                    DISTINCT CASE
                        WHEN f.is_available = 1 THEN f.id
                    END
                ) AS food_count

            FROM canteens AS c

            LEFT JOIN foods AS f
                ON f.canteen_id = c.id

            GROUP BY
                c.id,
                c.name,
                c.location,
                c.description

            ORDER BY c.name
        """)

        canteens = cur.fetchall()

    finally:
        cur.close()
        db.close()

    return render_template(
        "home.html",
        canteens=canteens
    )




@app.route("/db-info")
def db_info():
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT DATABASE() AS database_name")
    result = cur.fetchone()

    cur.close()
    db.close()

    return {
        "connected_database": result
    }
   
    
if __name__ == "__main__":

    print("\n========== FLASK ROUTE CHECK ==========")

    for rule in app.url_map.iter_rules():
        if "owner" in rule.endpoint:
            print(rule.endpoint, "---->", rule.rule)

    print("=======================================\n")

    app.run(debug=True)