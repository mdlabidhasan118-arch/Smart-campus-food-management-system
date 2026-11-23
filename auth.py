from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        if not name or not email or len(password)<8:
            flash("সব তথ্য দিন। Password কমপক্ষে ৮ অক্ষরের হতে হবে।", "danger")
            return redirect(url_for("auth.register"))
        db=get_db(); cur=db.cursor()
        try:
            cur.execute("INSERT INTO users(name,email,password_hash,role) VALUES(%s,%s,%s,'student')",
                        (name,email,generate_password_hash(password)))
            db.commit()
            flash("Registration সফল হয়েছে। এখন Login করুন।","success")
            return redirect(url_for("auth.login"))
        except Exception:
            db.rollback(); flash("এই Email আগে থেকেই ব্যবহৃত হয়েছে অথবা তথ্য সঠিক নয়।","danger")
        finally:
            cur.close(); db.close()
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        db=get_db(); cur=db.cursor(dictionary=True)
        cur.execute("SELECT id,name,email,password_hash,role FROM users WHERE email=%s AND is_active=1",(email,))
        user=cur.fetchone(); cur.close(); db.close()
        if user and check_password_hash(user["password_hash"],password):
            session.clear()
            session["user"]={k:user[k] for k in ("id","name","email","role")}
            flash("স্বাগতম, "+user["name"],"success")
            target={"student":"student.dashboard","owner":"owner.dashboard","admin":"admin.dashboard"}
            return redirect(url_for(target[user["role"]]))
        flash("Email অথবা Password ভুল।","danger")
    return render_template("auth/login.html")

@auth_bp.route("/logout")
def logout():
    session.clear(); flash("আপনি Logout করেছেন।","info")
    return redirect(url_for("home"))
