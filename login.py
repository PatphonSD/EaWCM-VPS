from os import name
from flask import Flask, jsonify, make_response, request, session
import mysql.connector
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis import Redis

#ทำการเชื่อมต่อฐานข้อมูล
db = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="userdata"
)

#ทำการเชื่อมต่อฐานข้อมูล
dbmain = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="token"
)

#สร้าง Cursor Object เพื่อใช้ query ข้อมูล
cursor = db.cursor()
cursormain = dbmain.cursor()

#สร้าง Flask App Object
app = Flask(__name__)
redis = Redis(host='localhost', port=8569)

limiter = Limiter(
    app,
    default_limits=["100 per day", "20 per hour"]
)
limiter.key_func = get_remote_address
app.secret_key = "123123123123123123123123123123123123"
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

    # เพิ่มตรวจสอบจำนวนครั้งล็อกอินผิดก่อน
    login_attempts = session.get('login_attempts', 0)
    if login_attempts > 5:
        # ส่งรหัส 429 และปิดการเข้าถึงจนกว่าจะครบ 30วินาที
        response = make_response('Too many login attempts. Please try again later.')
        response.headers['Retry-After'] = 30
        response.status_code = 429
        return response
    
    # ตรวจสอบการล็อกอินโดย query ข้อมูลจากฐานข้อมูล
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    
    if user:
        # ดึงข้อมูล IP Address จากฐานข้อมูล
        cursor.execute("SELECT ip_address FROM users WHERE email = %s", (email,))
        ip_address = cursor.fetchone()[0]
        cursor.execute("SELECT port FROM users WHERE email = %s", (email,))
        port = cursor.fetchone()[0]
    
        # รีเซ็ตค่าครั้งล็อกอินผิด
        session['login_attempts'] = 0
        
        # สร้าง JSON ตอบกลับไปยังผู้ใช้
        return jsonify({'ipAddress': ip_address, 'port': port})
    else:
        # เพิ่มค่าครั้งล็อกอินผิด
        session['login_attempts'] = login_attempts + 1
    
        return 'Invalid email or password', 401

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    ip_address = request.form.get('ip_address')
    port = request.form.get('port')
    token = request.form.get('token')
    # เช็คว่ามี username หรือ email นี้ในฐานข้อมูลแล้วหรือยัง
    cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
    user = cursor.fetchone()
    if user:
        return 'Username or email already exists', 400
    # ถ้าไม่มี ให้ทำการ insert ข้อมูล user ใหม่ลงในฐานข้อมูล
    cursormain.execute("SELECT `data` FROM `token` WHERE token = %s", (token,))
    token = cursormain.fetchone()
    if token:
        cursor.execute("INSERT INTO users (username, password, email, ip_address, port) VALUES (%s, %s, %s, %s, %s)", (username, password, email, ip_address, port))
        db.commit()
        return 'Register successful', 200
    else :
        return 'Token not match', 400
    

if __name__ == '__main__':
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.after_request(after_request)
    app.run(port=8569,debug=True)