from werkzeug.security import generate_password_hash
from db import get_db

users=[
 ("System Administrator","admin@smartcampus.local","Admin@12345","admin"),
 ("Demo Canteen Owner","owner@smartcampus.local","Owner@12345","owner")
]
db=get_db(); cur=db.cursor()
for name,email,password,role in users:
    cur.execute("""INSERT INTO users(name,email,password_hash,role)
                   VALUES(%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash),role=VALUES(role),is_active=1""",
                (name,email,generate_password_hash(password),role))
db.commit(); cur.close(); db.close()
print("Demo admin and owner accounts are ready.")
