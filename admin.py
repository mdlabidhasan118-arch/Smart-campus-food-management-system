from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import get_db
from helpers import role_required
admin_bp=Blueprint("admin",__name__)

@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    db=get_db(); cur=db.cursor(dictionary=True)
    stats={}
    for table,key in [("users","users"),("canteens","canteens"),("foods","foods"),("orders","orders"),("complaints","complaints")]:
        cur.execute(f"SELECT COUNT(*) AS n FROM {table}"); stats[key]=cur.fetchone()["n"]
    cur.execute("SELECT COALESCE(SUM(total_amount),0) AS revenue FROM orders WHERE status='completed'")
    stats["revenue"]=cur.fetchone()["revenue"]
    cur.execute("""SELECT o.id,o.total_amount,o.status,o.created_at,u.name AS student,c.name AS canteen
                   FROM orders o JOIN users u ON u.id=o.student_id JOIN canteens c ON c.id=o.canteen_id
                   ORDER BY o.created_at DESC LIMIT 10""")
    recent=cur.fetchall()
    cur.execute("""SELECT cp.*,u.name AS user_name FROM complaints cp JOIN users u ON u.id=cp.user_id
                   ORDER BY cp.created_at DESC LIMIT 10""")
    complaints=cur.fetchall()
    cur.close(); db.close()
    return render_template("admin/dashboard.html",stats=stats,recent=recent,complaints=complaints)

@admin_bp.route("/users")
@role_required("admin")
def users():
    db=get_db(); cur=db.cursor(dictionary=True)
    cur.execute("SELECT id,name,email,role,is_active,created_at FROM users ORDER BY created_at DESC")
    rows=cur.fetchall(); cur.close(); db.close()
    return render_template("admin/users.html",users=rows)

@admin_bp.route("/user/<int:uid>/toggle",methods=["POST"])
@role_required("admin")
def toggle_user(uid):
    db=get_db(); cur=db.cursor()
    cur.execute("UPDATE users SET is_active=1-is_active WHERE id=%s AND role<>'admin'",(uid,))
    db.commit(); cur.close(); db.close()
    flash("User status update হয়েছে।","success"); return redirect(url_for("admin.users"))

@admin_bp.route("/complaints")
@role_required("admin")
def complaints():
    db=get_db(); cur=db.cursor(dictionary=True)
    cur.execute("""SELECT cp.*,u.name AS user_name,c.name AS canteen_name FROM complaints cp
                   JOIN users u ON u.id=cp.user_id LEFT JOIN canteens c ON c.id=cp.canteen_id
                   ORDER BY cp.created_at DESC""")
    rows=cur.fetchall(); cur.close(); db.close()
    return render_template("admin/complaints.html",complaints=rows)

@admin_bp.route("/complaint/<int:cid>/resolve",methods=["POST"])
@role_required("admin")
def resolve(cid):
    db=get_db(); cur=db.cursor()
    cur.execute("UPDATE complaints SET status='resolved' WHERE id=%s",(cid,))
    db.commit(); cur.close(); db.close()
    return redirect(url_for("admin.complaints"))

@admin_bp.route("/reports")
@role_required("admin")
def reports():
    db=get_db(); cur=db.cursor(dictionary=True)
    cur.execute("""SELECT DATE(created_at) AS day,COUNT(*) AS orders_count,SUM(total_amount) AS revenue
                   FROM orders WHERE status='completed' GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 30""")
    daily=cur.fetchall()
    cur.execute("""SELECT c.name,COUNT(o.id) AS orders_count,COALESCE(SUM(o.total_amount),0) AS revenue
                   FROM canteens c LEFT JOIN orders o ON o.canteen_id=c.id AND o.status='completed'
                   GROUP BY c.id ORDER BY revenue DESC""")
    canteen_stats=cur.fetchall()
    cur.close(); db.close()
    return render_template("admin/reports.html",daily=daily,canteen_stats=canteen_stats)
