
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app
)

from db import get_db
from helpers import role_required


owner_bp = Blueprint("owner", __name__)


# ==========================================
# OWNER CANTEEN
# ==========================================

def owner_canteen(cur, owner_id):
    cur.execute(
        "SELECT id, name FROM canteens WHERE owner_id=%s LIMIT 1",
        (owner_id,)
    )
    return cur.fetchone()


# ==========================================
# OWNER DASHBOARD
# ==========================================

@owner_bp.route("/dashboard")
@role_required("owner")
def dashboard():

    db = get_db()
    cur = db.cursor(dictionary=True)

    c = owner_canteen(cur, session["user"]["id"])

    if not c:
        cur.close()
        db.close()
        return render_template("owner/no_canteen.html")

    cur.execute(
        "SELECT * FROM foods WHERE canteen_id=%s ORDER BY created_at DESC",
        (c["id"],)
    )
    foods = cur.fetchall()

    cur.execute(
        "SELECT COUNT(*) AS n FROM orders WHERE canteen_id=%s",
        (c["id"],)
    )
    count = cur.fetchone()["n"]

    cur.execute(
        """
        SELECT crowd_level, crowd_note, updated_at
        FROM crowd_status
        WHERE canteen_id=%s
        """,
        (c["id"],)
    )
    crowd = cur.fetchone()

    cur.close()
    db.close()

    return render_template(
        "owner/dashboard.html",
        canteen=c,
        foods=foods,
        count=count,
        crowd=crowd
    )


# ==========================================
# ADD FOOD
# ==========================================

@owner_bp.route("/food/add", methods=["POST"])
@role_required("owner")
def add_food():

    db = get_db()
    cur = db.cursor(dictionary=True)

    c = owner_canteen(cur, session["user"]["id"])

    if c:

        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()

        try:
            price = float(request.form.get("price", "0"))
        except ValueError:
            price = 0

        if name and price > 0:

            cur.execute(
                """
                INSERT INTO foods(
                    canteen_id,
                    name,
                    description,
                    price,
                    category
                )
                VALUES(%s, %s, %s, %s, %s)
                """,
                (
                    c["id"],
                    name,
                    desc,
                    price,
                    request.form.get("category", "Meal")
                )
            )

            db.commit()

            flash("Food item added successfully.", "success")

        else:
            flash("Please enter a valid food name and price.", "danger")

    cur.close()
    db.close()

    return redirect(url_for("owner.dashboard"))


# ==========================================
# TOGGLE FOOD AVAILABILITY
# ==========================================

@owner_bp.route("/food/<int:food_id>/toggle", methods=["POST"])
@role_required("owner")
def toggle_food(food_id):

    db = get_db()
    cur = db.cursor(dictionary=True)

    c = owner_canteen(cur, session["user"]["id"])

    if c:

        cur.execute(
            """
            UPDATE foods
            SET is_available = 1 - is_available
            WHERE id=%s AND canteen_id=%s
            """,
            (food_id, c["id"])
        )

        db.commit()

    cur.close()
    db.close()

    return redirect(url_for("owner.dashboard"))


# ==========================================
# OWNER ORDERS
# PROFESSIONAL ORDER LIST WITH FOOD DETAILS
# ==========================================

@owner_bp.route("/orders")
@role_required("owner")
def orders():

    db = None
    cur = None

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        canteen = owner_canteen(cur, session["user"]["id"])

        rows = []

        if not canteen:
            flash("No canteen is assigned to your account.", "warning")
            return render_template(
                "owner/orders.html",
                orders=rows
            )

        cur.execute(
            """
            SELECT
                o.*,
                u.name AS student_name,
                u.email AS student_email
            FROM orders AS o
            JOIN users AS u
                ON u.id = o.student_id
            WHERE o.canteen_id = %s
            ORDER BY
                CASE o.status
                    WHEN 'pending' THEN 1
                    WHEN 'confirmed' THEN 2
                    WHEN 'preparing' THEN 3
                    WHEN 'ready' THEN 4
                    WHEN 'completed' THEN 5
                    WHEN 'cancelled' THEN 6
                    ELSE 7
                END,
                o.created_at DESC
            """,
            (canteen["id"],)
        )

        rows = cur.fetchall()

        for order in rows:
            cur.execute(
                """
                SELECT
                    oi.food_id,
                    f.name AS food_name,
                    oi.quantity,
                    oi.unit_price,
                    (oi.quantity * oi.unit_price) AS subtotal
                FROM order_items AS oi
                LEFT JOIN foods AS f
                    ON f.id = oi.food_id
                WHERE oi.order_id = %s
                ORDER BY oi.food_id
                """,
                (order["id"],)
            )

            order["items"] = cur.fetchall()

    except Exception:
        current_app.logger.exception("Owner order list could not be loaded")
        flash(
            "Unable to load orders. Please check the database tables and error log.",
            "danger"
        )
        rows = []

    finally:
        if cur:
            cur.close()

        if db:
            db.close()

    return render_template(
        "owner/orders.html",
        orders=rows
    )


# ==========================================
# UPDATE ORDER STATUS
# WITH REWARD POINTS SYSTEM
# ==========================================

@owner_bp.route("/order/<int:oid>/status", methods=["POST"])
@role_required("owner")
def update_status(oid):

    status = (request.form.get("status") or "").strip()

    note = (request.form.get("note") or "").strip()[:255]

    transitions = {

        "pending": {"confirmed", "cancelled"},

        "confirmed": {"preparing", "cancelled"},

        "preparing": {"ready", "cancelled"},

        "ready": {"completed"},

        "completed": set(),

        "cancelled": set()
    }

    timestamp_columns = {

        "confirmed": "accepted_at",

        "preparing": "preparing_at",

        "ready": "ready_at",

        "completed": "completed_at",

        "cancelled": "cancelled_at"
    }

    db = None
    cur = None

    try:

        db = get_db()

        cur = db.cursor(dictionary=True)

        # Start database transaction
        db.start_transaction()

        # Get owner's canteen
        canteen = owner_canteen(
            cur,
            session["user"]["id"]
        )

        if not canteen:

            db.rollback()

            flash(
                "No canteen is assigned to your account.",
                "danger"
            )

            return redirect(url_for("owner.orders"))

        # Get order details and lock database row
        # UPDATED: Added student_id and total_amount

        cur.execute(
            """
            SELECT
                id,
                status,
                student_id,
                total_amount
            FROM orders
            WHERE id=%s AND canteen_id=%s
            FOR UPDATE
            """,
            (oid, canteen["id"])
        )

        order = cur.fetchone()

        if not order:

            db.rollback()

            flash(
                "Order not found.",
                "danger"
            )

            return redirect(url_for("owner.orders"))

        old_status = order["status"]

        # Validate status transition
        if status not in transitions.get(old_status, set()):

            db.rollback()

            flash(
                f"Changing status from {old_status} to {status} is not allowed.",
                "danger"
            )

            return redirect(url_for("owner.orders"))

        # Cancellation reason is mandatory
        if status == "cancelled" and not note:

            db.rollback()

            flash(
                "Please provide a reason for cancelling this order.",
                "danger"
            )

            return redirect(url_for("owner.orders"))

        # Select timestamp column
        timestamp_column = timestamp_columns[status]

        # Update order status
        if status == "cancelled":

            cur.execute(
                f"""
                UPDATE orders
                SET status=%s,
                    {timestamp_column}=CURRENT_TIMESTAMP,
                    cancel_reason=%s
                WHERE id=%s AND canteen_id=%s
                """,
                (
                    status,
                    note,
                    oid,
                    canteen["id"]
                )
            )

        else:

            cur.execute(
                f"""
                UPDATE orders
                SET status=%s,
                    {timestamp_column}=CURRENT_TIMESTAMP
                WHERE id=%s AND canteen_id=%s
                """,
                (
                    status,
                    oid,
                    canteen["id"]
                )
            )

        # ======================================
        # ADD REWARD POINTS WHEN ORDER COMPLETED
        # ======================================

        if status == "completed":

            points = int(order["total_amount"] // 10)

            if points > 0:

                cur.execute(
                    """
                    INSERT IGNORE INTO reward_transactions(
                        student_id,
                        order_id,
                        points
                    )
                    VALUES(%s, %s, %s)
                    """,
                    (
                        order["student_id"],
                        oid,
                        points
                    )
                )

                if cur.rowcount == 1:
                    flash(
                        f"{points} reward points awarded to the student.",
                        "success"
                    )

        # ======================================
        # SAVE ORDER STATUS CHANGE HISTORY
        # ======================================

        cur.execute(
            """
            INSERT INTO order_status_history(
                order_id,
                previous_status,
                new_status,
                changed_by,
                note
            )
            VALUES(%s, %s, %s, %s, %s)
            """,
            (
                oid,
                old_status,
                status,
                session["user"]["id"],
                note or None
            )
        )

        # Commit all database changes
        db.commit()

        flash(
            f"Order status successfully changed from {old_status} to {status}.",
            "success"
        )

    except Exception:

        if db:
            db.rollback()

        current_app.logger.exception(
            "Owner order status update failed"
        )

        flash(
            "Unable to update order status. Please check the database configuration and error log.",
            "danger"
        )

    finally:

        if cur:
            cur.close()

        if db:
            db.close()

    return redirect(url_for("owner.orders"))


# ==========================================
# UPDATE CANTEEN CROWD STATUS
# ==========================================

@owner_bp.route("/crowd", methods=["POST"])
@role_required("owner")
def crowd():

    level = request.form.get("level")

    if level not in {"low", "moderate", "high", "very_high"}:
        level = "moderate"

    db = get_db()
    cur = db.cursor(dictionary=True)

    c = owner_canteen(cur, session["user"]["id"])

    if c:

        cur.execute(
            """
            INSERT INTO crowd_status(
                canteen_id,
                crowd_level,
                crowd_note
            )
            VALUES(%s, %s, %s)

            ON DUPLICATE KEY UPDATE
                crowd_level=VALUES(crowd_level),
                crowd_note=VALUES(crowd_note),
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                c["id"],
                level,
                request.form.get("note", "").strip()
            )
        )

        db.commit()

    cur.close()
    db.close()

    flash(
        "Canteen crowd status updated successfully.",
        "success"
    )

    return redirect(url_for("owner.dashboard"))


# ==========================================
# OWNER SALES & REVENUE DASHBOARD
# PHASE 2
# ==========================================

@owner_bp.route("/revenue")
@role_required("owner")
def revenue():

    db = None
    cur = None

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        canteen = owner_canteen(
            cur,
            session["user"]["id"]
        )

        if not canteen:
            return render_template("owner/no_canteen.html")

        canteen_id = canteen["id"]

        # Today's revenue
        cur.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE canteen_id = %s
              AND status = 'completed'
              AND DATE(completed_at) = CURDATE()
            """,
            (canteen_id,)
        )
        today_revenue = cur.fetchone()["total"]

        # This week's revenue
        cur.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE canteen_id = %s
              AND status = 'completed'
              AND YEARWEEK(completed_at, 1)
                  = YEARWEEK(CURDATE(), 1)
            """,
            (canteen_id,)
        )
        weekly_revenue = cur.fetchone()["total"]

        # This month's revenue
        cur.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE canteen_id = %s
              AND status = 'completed'
              AND YEAR(completed_at) = YEAR(CURDATE())
              AND MONTH(completed_at) = MONTH(CURDATE())
            """,
            (canteen_id,)
        )
        monthly_revenue = cur.fetchone()["total"]

        # Total completed orders
        cur.execute(
            """
            SELECT COUNT(*) AS total
            FROM orders
            WHERE canteen_id = %s
              AND status = 'completed'
            """,
            (canteen_id,)
        )
        completed_orders = cur.fetchone()["total"]

        # Best-selling foods
        cur.execute(
            """
            SELECT
                f.name AS food_name,
                SUM(oi.quantity) AS total_quantity,
                SUM(oi.quantity * oi.unit_price) AS total_sales
            FROM order_items AS oi
            JOIN orders AS o
                ON o.id = oi.order_id
            JOIN foods AS f
                ON f.id = oi.food_id
            WHERE o.canteen_id = %s
              AND o.status = 'completed'
            GROUP BY f.id, f.name
            ORDER BY total_quantity DESC
            LIMIT 5
            """,
            (canteen_id,)
        )
        best_selling_foods = cur.fetchall()

        # Last 7 days sales chart
        cur.execute(
            """
            SELECT
                DATE(completed_at) AS sale_date,
                SUM(total_amount) AS daily_total
            FROM orders
            WHERE canteen_id = %s
              AND status = 'completed'
              AND completed_at >= CURDATE() - INTERVAL 6 DAY
              AND completed_at < CURDATE() + INTERVAL 1 DAY
            GROUP BY DATE(completed_at)
            ORDER BY sale_date
            """,
            (canteen_id,)
        )
        sales_rows = cur.fetchall()

        chart_labels = [
            str(row["sale_date"])
            for row in sales_rows
        ]

        chart_values = [
            float(row["daily_total"])
            for row in sales_rows
        ]

        return render_template(
            "owner/revenue.html",
            canteen=canteen,
            today_revenue=today_revenue,
            weekly_revenue=weekly_revenue,
            monthly_revenue=monthly_revenue,
            completed_orders=completed_orders,
            best_selling_foods=best_selling_foods,
            chart_labels=chart_labels,
            chart_values=chart_values
        )

    except Exception:
        current_app.logger.exception(
            "Owner revenue dashboard could not be loaded"
        )

        flash(
            "Unable to load revenue dashboard. Please check the error log.",
            "danger"
        )

        return redirect(url_for("owner.dashboard"))

    finally:
        if cur:
            cur.close()

        if db:
            db.close()
