
from getpass import getpass
from werkzeug.security import generate_password_hash

print("=== Admin Password ===")
admin_password = getpass("Enter Admin Password: ")
admin_hash = generate_password_hash(admin_password, method="scrypt")

print("\n=== Owner Password ===")
owner_password = getpass("Enter Owner Password: ")
owner_hash = generate_password_hash(owner_password, method="scrypt")

print("\n===== GENERATED PASSWORD HASHES =====")

print("\nADMIN HASH:")
print(admin_hash)

print("\nOWNER HASH:")
print(owner_hash)
