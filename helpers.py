from functools import wraps
from flask import session, redirect, url_for, flash
def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user=session.get("user")
            if not user:
                flash("এই পেজ দেখতে Login করতে হবে।","warning")
                return redirect(url_for("auth.login"))
            if user["role"] not in roles:
                flash("এই পেজে প্রবেশের অনুমতি নেই।","danger")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator
