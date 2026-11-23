# Smart Campus Food Management System

Flask + MySQL ভিত্তিক একটি সম্পূর্ণ শিক্ষামূলক Campus Canteen Management Web Application.

## অন্তর্ভুক্ত ফিচার
- Student registration/login, food listing, order placement, order tracking, complaint submission
- Canteen owner dashboard, food availability management, order status update, crowd status update
- Admin dashboard, user activation/deactivation, complaint resolution, sales/order reports
- Health ও database test endpoints
- Responsive Bootstrap interface

## প্রয়োজন
- Windows 10/11
- Python 3.10 বা নতুন
- MySQL Server 8.0 বা নতুন
- VS Code (ঐচ্ছিক)

## প্রথমবার চালানোর নিয়ম (Windows PowerShell)
1. ZIP Extract করে folder-টি VS Code-এ Open করুন।
2. MySQL Server চালু করুন। MySQL Workbench বা Command Line-এ নিচের কমান্ড চালান:
   ```sql
   CREATE DATABASE smart_campus_food CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Project root-এ `.env.example` কপি করে `.env` নাম দিন। `.env`-এ নিজের MySQL password বসান।
4. Terminal-এ:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Database schema ও demo data import করুন:
   ```powershell
   Get-Content .\database\schema.sql | mysql -u root -p smart_campus_food
   Get-Content .\database\seed.sql | mysql -u root -p smart_campus_food
   ```
   বিকল্পভাবে MySQL Workbench-এ `database/schema.sql`, এরপর `database/seed.sql` খুলে Execute করুন।
6. Demo admin ও owner password তৈরি করতে:
   ```powershell
   python create_demo_users.py
   ```
7. App চালান:
   ```powershell
   python app.py
   ```
8. Browser-এ `http://127.0.0.1:5000` খুলুন।

## Demo login
`python create_demo_users.py` চালানোর পর:
- Admin: `admin@smartcampus.local` / `Admin@12345`
- Owner: `owner@smartcampus.local` / `Owner@12345`

Student account: Register page থেকে তৈরি করুন।

## Test URLs
- `/health` — application health
- `/db-test` — MySQL connection test

## গুরুত্বপূর্ণ
- `.env`-এর আসল Password কাউকে দেবেন না।
- Demo password কেবল local demonstration-এর জন্য। Production ব্যবহারের আগে বদলাতে হবে।
- Flask development server কেবল development/demo-র জন্য; public production deployment-এর জন্য production WSGI server, HTTPS, CSRF protection, rate limiting, backup এবং security review প্রয়োজন।
- Payment gateway integration এখানে নেই; বাস্তব টাকা নেওয়ার আগে অনুমোদিত payment provider ও secure callback integration করতে হবে।
- Database schema এবং seed script পুনরায় চালালে schema-র existing data drop করা হয় না। Demo sample records duplicate এড়াতে seed করা হয়েছে।
