from os import name
from flask import Flask, jsonify, request, session
import mysql.connector
from flask_cors import CORS

#ทำการเชื่อมต่อฐานข้อมูล
db = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="userdata"
)

#สร้าง Cursor Object เพื่อใช้ query ข้อมูล
cursor = db.cursor()

#สร้าง Flask App Object
app = Flask(__name__)
app.secret_key = 'mysecretkey'

# สร้าง decorator function สำหรับกำหนด CORS headers ใน response
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

#สร้าง Route สำหรับการ Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # ตรวจสอบการล็อกอินโดย query ข้อมูลจากฐานข้อมูล
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()

    if user:
        # ดึงข้อมูล IP Address จากฐานข้อมูล
        cursor.execute("SELECT ip_address FROM users WHERE email = %s", (email,))
        ip_address = cursor.fetchone()[0]
        cursor.execute("SELECT port FROM users WHERE email = %s", (email,))
        port = cursor.fetchone()[0]
        
        # สร้าง JSON ตอบกลับไปยังผู้ใช้
        return jsonify({'ipAddress': ip_address, 'port': port})
    else:
        return 'Invalid email or password', 401



@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    ip_address = request.form.get('ip_address')
    port = request.form.get('port')
    # เช็คว่ามี username หรือ email นี้ในฐานข้อมูลแล้วหรือยัง
    cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
    user = cursor.fetchone()
    if user:
        return 'Username or email already exists', 400
    # ถ้าไม่มี ให้ทำการ insert ข้อมูล user ใหม่ลงในฐานข้อมูล
    cursor.execute("INSERT INTO users (username, password, email, ip_address, port) VALUES (%s, %s, %s, %s, %s)", (username, password, email, ip_address, port))
    db.commit()
    
    # ส่ง response กลับไปยัง client ว่า register เสร็จสิ้น
    return 'Register successful', 200

if __name__ == '__main__':
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.after_request(after_request)
    app.run(port=8569,debug=True)