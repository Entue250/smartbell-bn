# # ════════════════════════════════════════════════════════
# # Smart School Bell — Flask API Server
# # BUG FIXES:
# #   1. All ff"..." → f"..." (f-string syntax error)
# #   2. SQLite → PostgreSQL (psycopg2)
# #   3. Added /api/auth/signup + signup toggle endpoints
# # ════════════════════════════════════════════════════════

# from flask import Flask, request, jsonify
# from flask_socketio import SocketIO
# from flask_cors import CORS
# from flask_jwt_extended import (JWTManager, create_access_token,
#                                 jwt_required, get_jwt_identity, get_jwt)
# import psycopg2, psycopg2.extras, datetime, bcrypt
# from functools import wraps
# from scheduler import start_scheduler

# app = Flask(__name__, static_folder='static')
# CORS(app, origins="*")
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
# app.config['JWT_SECRET_KEY'] = 'smartbell-secret-change-in-production'
# app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=7)
# jwt = JWTManager(app)

# # ── ARDUINO ───────────────────────────────────────────────
# arduino = None
# try:
#     import serial
#     for port in ['/dev/ttyUSB0', '/dev/ttyACM0', 'COM3', 'COM4', 'COM5']:
#         try:
#             arduino = serial.Serial(port, 9600, timeout=2)
#             print(f"Arduino connected on {port}")
#             break
#         except Exception:
#             pass
#     if not arduino:
#         print("Arduino not found - simulation mode active")
# except ImportError:
#     print("pyserial not installed - simulation mode active")

# # ── POSTGRESQL ────────────────────────────────────────────
# DB_CONFIG = {
#     'host':     'localhost',
#     'port':     5432,
#     'dbname':   'smartbell',
#     'user':     'postgres',
#     'password': 'Niyomugabo@20171',
# }

# def get_db():
#     conn = psycopg2.connect(**DB_CONFIG)
#     return conn

# def init_db():
#     conn = get_db()
#     cur = conn.cursor()
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS users (
#             id SERIAL PRIMARY KEY,
#             username TEXT UNIQUE NOT NULL,
#             password TEXT NOT NULL,
#             role TEXT NOT NULL DEFAULT 'viewer',
#             created_at TIMESTAMP DEFAULT NOW()
#         );
#         CREATE TABLE IF NOT EXISTS schedules (
#             id SERIAL PRIMARY KEY,
#             name TEXT NOT NULL,
#             ring_time TEXT NOT NULL,
#             pattern TEXT NOT NULL DEFAULT 'LONG_SHORT',
#             led_color TEXT NOT NULL DEFAULT 'GREEN',
#             lcd_line1 TEXT NOT NULL,
#             lcd_line2 TEXT NOT NULL DEFAULT '',
#             active INTEGER NOT NULL DEFAULT 1,
#             created_by TEXT,
#             created_at TIMESTAMP DEFAULT NOW()
#         );
#         CREATE TABLE IF NOT EXISTS ring_logs (
#             id SERIAL PRIMARY KEY,
#             schedule_name TEXT,
#             rang_at TIMESTAMP DEFAULT NOW(),
#             triggered_by TEXT DEFAULT 'schedule',
#             user_id INTEGER
#         );
#         CREATE TABLE IF NOT EXISTS app_settings (
#             key TEXT PRIMARY KEY,
#             value TEXT NOT NULL
#         );
#     """)
#     cur.execute("SELECT COUNT(*) FROM app_settings WHERE key='signup_enabled'")
#     if cur.fetchone()[0] == 0:
#         cur.execute("INSERT INTO app_settings (key,value) VALUES ('signup_enabled','false')")
#     cur.execute("SELECT COUNT(*) FROM users")
#     if cur.fetchone()[0] == 0:
#         pw = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
#         cur.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,%s)",
#                     ('admin', pw, 'admin'))
#         print("Default admin created: admin / admin123")
#     conn.commit()
#     cur.close(); conn.close()

# def send_to_arduino(cmd):
#     if arduino and arduino.is_open:
#         arduino.write((cmd + '\n').encode())
#         arduino.flush()
#         print(f"Arduino: {cmd}")
#     else:
#         print(f"[SIMULATE] {cmd}")

# def ring_bell(name, pattern, line1, line2, led, triggered_by='schedule', user_id=None):
#     send_to_arduino(f"BELL|{pattern}|{line1}|{line2}|{led}")
#     conn = get_db()
#     cur = conn.cursor()
#     cur.execute("INSERT INTO ring_logs (schedule_name,triggered_by,user_id) VALUES (%s,%s,%s)",
#                 (name, triggered_by, user_id))
#     conn.commit(); cur.close(); conn.close()
#     socketio.emit('bell_rang', {
#         'name': name, 'time': datetime.datetime.now().strftime('%H:%M:%S'),
#         'pattern': pattern, 'led': led, 'triggered_by': triggered_by,
#     })

# def require_role(*roles):
#     def decorator(f):
#         @wraps(f)
#         @jwt_required()
#         def wrapper(*args, **kwargs):
#             if get_jwt().get('role') not in roles:
#                 return jsonify({'error': 'Insufficient permissions'}), 403
#             return f(*args, **kwargs)
#         return wrapper
#     return decorator

# # ════ AUTH ═══════════════════════════════════════════════
# @app.route('/api/auth/login', methods=['POST'])
# def login():
#     data = request.json
#     conn = get_db()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#     cur.execute("SELECT * FROM users WHERE username=%s", (data['username'],))
#     user = cur.fetchone(); cur.close(); conn.close()
#     if not user or not bcrypt.checkpw(data['password'].encode(), user['password'].encode()):
#         return jsonify({'error': 'Invalid credentials'}), 401
#     token = create_access_token(identity=str(user['id']),
#         additional_claims={'role': user['role'], 'username': user['username']})
#     return jsonify({'token': token, 'role': user['role'], 'username': user['username']})

# @app.route('/api/auth/signup-status', methods=['GET'])
# def signup_status():
#     conn = get_db()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#     cur.execute("SELECT value FROM app_settings WHERE key='signup_enabled'")
#     row = cur.fetchone(); cur.close(); conn.close()
#     return jsonify({'enabled': row['value'] == 'true' if row else False})

# @app.route('/api/auth/signup', methods=['POST'])
# def signup():
#     conn = get_db()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#     cur.execute("SELECT value FROM app_settings WHERE key='signup_enabled'")
#     row = cur.fetchone()
#     if not row or row['value'] != 'true':
#         cur.close(); conn.close()
#         return jsonify({'error': 'Signup is disabled. Contact admin.'}), 403
#     data = request.json
#     pw_hash = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
#     try:
#         cur2 = conn.cursor()
#         cur2.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,%s)",
#                      (data['username'], pw_hash, 'teacher'))
#         conn.commit(); cur.close(); cur2.close(); conn.close()
#         return jsonify({'status': 'created', 'role': 'teacher'}), 201
#     except psycopg2.errors.UniqueViolation:
#         conn.rollback(); cur.close(); conn.close()
#         return jsonify({'error': 'Username already exists'}), 409

# @app.route('/api/auth/signup-toggle', methods=['POST'])
# @require_role('admin')
# def toggle_signup():
#     enabled = bool(request.json.get('enabled', False))
#     conn = get_db(); cur = conn.cursor()
#     cur.execute("UPDATE app_settings SET value=%s WHERE key='signup_enabled'",
#                 ('true' if enabled else 'false',))
#     conn.commit(); cur.close(); conn.close()
#     return jsonify({'enabled': enabled})
# # ══════════════════════════════════════════════════════
# # ADD THESE TWO ROUTES TO YOUR app.py
# # Place them after the /api/auth/signup-toggle route
# # ══════════════════════════════════════════════════════

# @app.route('/api/auth/change-password', methods=['POST'])
# @jwt_required()
# def change_password():
#     """Any logged-in user can change their own password."""
#     data = request.json
#     current_pw  = data.get('current_password', '')
#     new_pw      = data.get('new_password', '')
#     confirm_pw  = data.get('confirm_password', '')

#     if not current_pw or not new_pw or not confirm_pw:
#         return jsonify({'error': 'All fields are required'}), 400
#     if new_pw != confirm_pw:
#         return jsonify({'error': 'New passwords do not match'}), 400
#     if len(new_pw) < 6:
#         return jsonify({'error': 'New password must be at least 6 characters'}), 400
#     if new_pw == current_pw:
#         return jsonify({'error': 'New password must be different from current password'}), 400

#     uid = get_jwt_identity()
#     conn = get_db()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#     cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
#     user = cur.fetchone()

#     if not user or not bcrypt.checkpw(current_pw.encode(), user['password'].encode()):
#         cur.close(); conn.close()
#         return jsonify({'error': 'Current password is incorrect'}), 401

#     new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
#     cur2 = conn.cursor()
#     cur2.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, uid))
#     conn.commit()
#     cur.close(); cur2.close(); conn.close()
#     return jsonify({'status': 'Password changed successfully'})


# @app.route('/api/auth/admin-reset-password', methods=['POST'])
# @require_role('admin')
# def admin_reset_password():
#     """Admin can reset any user's password without knowing the old one."""
#     data = request.json
#     uid     = data.get('user_id')
#     new_pw  = data.get('new_password', '')

#     if not uid or not new_pw:
#         return jsonify({'error': 'user_id and new_password are required'}), 400
#     if len(new_pw) < 6:
#         return jsonify({'error': 'Password must be at least 6 characters'}), 400

#     new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
#     conn = get_db(); cur = conn.cursor()
#     cur.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, uid))
#     conn.commit(); cur.close(); conn.close()
#     return jsonify({'status': 'Password reset successfully'})
# @app.route('/api/auth/register', methods=['POST'])
# @require_role('admin')
# def register():
#     data = request.json
#     pw_hash = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
#     conn = get_db(); cur = conn.cursor()
#     try:
#         cur.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,%s)",
#                     (data['username'], pw_hash, data.get('role', 'viewer')))
#         conn.commit(); cur.close(); conn.close()
#         return jsonify({'status': 'created'}), 201
#     except psycopg2.errors.UniqueViolation:
#         conn.rollback(); cur.close(); conn.close()
#         return jsonify({'error': 'Username already exists'}), 409

# # ════ SCHEDULES ══════════════════════════════════════════
# @app.route('/api/schedules', methods=['GET'])
# @jwt_required()
# def get_schedules():
#     conn = get_db()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#     cur.execute("SELECT * FROM schedules ORDER BY ring_time")
#     rows = cur.fetchall(); cur.close(); conn.close()
#     return jsonify([dict(r) for r in rows])

# @app.route('/api/schedules', methods=['POST'])
# @require_role('admin', 'teacher')
# def add_schedule():
#     d = request.json
#     conn = get_db(); cur = conn.cursor()
#     cur.execute(
#         "INSERT INTO schedules (name,ring_time,pattern,led_color,lcd_line1,lcd_line2,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s)",
#         (d['name'], d['ring_time'], d.get('pattern','LONG_SHORT'),
#          d.get('led_color','GREEN'), d['lcd_line1'], d.get('lcd_line2',''), get_jwt_identity()))
#     conn.commit(); cur.close(); conn.close()
#     return jsonify({'status': 'created'}), 201

# @app.route('/api/schedules/<int:sid>', methods=['PUT'])
# @require_role('admin', 'teacher')
# def update_schedule(sid):
#     d = request.json
#     conn = get_db(); cur = conn.cursor()
#     cur.execute(
#         "UPDATE schedules SET name=%s,ring_time=%s,pattern=%s,led_color=%s,lcd_line1=%s,lcd_line2=%s,active=%s WHERE id=%s",
#         (d['name'],d['ring_time'],d['pattern'],d['led_color'],d['lcd_line1'],d['lcd_line2'],d.get('active',1),sid))
#     conn.commit(); cur.close(); conn.close()
#     return jsonify({'status': 'updated'})

# @app.route('/api/schedules/<int:sid>', methods=['DELETE'])
# @require_role('admin')
# def delete_schedule(sid):
#     conn = get_db(); cur = conn.cursor()
#     cur.execute("DELETE FROM schedules WHERE id=%s", (sid,))
#     conn.commit(); cur.close(); conn.close()
#     return jsonify({'status': 'deleted'})

# @app.route('/api/ring-now', methods=['POST'])
# @require_role('admin', 'teacher')
# def ring_now():
#     d = request.json
#     ring_bell(name=d.get('name','Manual Ring'), pattern=d.get('pattern','LONG_SHORT'),
#               line1=d.get('lcd_line1','MANUAL RING'), line2=d.get('lcd_line2',''),
#               led=d.get('led_color','GREEN'), triggered_by='manual', user_id=get_jwt_identity())
#     return jsonify({'status': 'rung'})

# @app.route('/api/logs', methods=['GET'])
# @jwt_required()
# def get_logs():
#     limit = request.args.get('limit', 50, type=int)
#     conn = get_db()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#     cur.execute("SELECT * FROM ring_logs ORDER BY rang_at DESC LIMIT %s", (limit,))
#     rows = cur.fetchall(); cur.close(); conn.close()
#     return jsonify([dict(r) for r in rows])

# @app.route('/api/status', methods=['GET'])
# def get_status():
#     now_str = datetime.datetime.now().strftime('%H:%M')
#     conn = get_db()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#     cur.execute("SELECT * FROM schedules WHERE ring_time > %s AND active=1 ORDER BY ring_time LIMIT 1", (now_str,))
#     next_bell = cur.fetchone()
#     cur.execute("SELECT COUNT(*) as c FROM ring_logs WHERE rang_at::date = CURRENT_DATE")
#     c = cur.fetchone(); cur.close(); conn.close()
#     return jsonify({'time': now_str, 'arduino': 'connected' if arduino else 'disconnected',
#                     'next_bell': dict(next_bell) if next_bell else None, 'rings_today': c['c']})

# @app.route('/api/users', methods=['GET'])
# @require_role('admin')
# def get_users():
#     conn = get_db()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#     cur.execute("SELECT id,username,role,created_at FROM users ORDER BY id")
#     rows = cur.fetchall(); cur.close(); conn.close()
#     return jsonify([dict(r) for r in rows])

# @app.route('/api/users/<int:uid>', methods=['DELETE'])
# @require_role('admin')
# def delete_user(uid):
#     conn = get_db(); cur = conn.cursor()
#     cur.execute("DELETE FROM users WHERE id=%s AND role!='admin'", (uid,))
#     conn.commit(); cur.close(); conn.close()
#     return jsonify({'status': 'deleted'})

# @app.route('/api/users/<int:uid>/role', methods=['PUT'])
# @require_role('admin')
# def update_user_role(uid):
#     conn = get_db(); cur = conn.cursor()
#     cur.execute("UPDATE users SET role=%s WHERE id=%s", (request.json['role'], uid))
#     conn.commit(); cur.close(); conn.close()
#     return jsonify({'status': 'updated'})

# if __name__ == '__main__':
#     init_db()
#     start_scheduler(ring_bell, DB_CONFIG)
#     print("SmartBell server running at http://0.0.0.0:5000")
#     socketio.run(app, host='0.0.0.0', port=5000, debug=False)

"""
SmartBell v2.0 — Flask Backend (app.py)
All improvements: ACK health, templates, silence, patterns,
LCD override, analytics, health endpoint, forgot-password,
JWT refresh, rate limiting, indexes.
"""

import os
import re
import random
import datetime
import threading
import serial
import serial.tools.list_ports
import psycopg2
import psycopg2.extras
import bcrypt


from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from scheduler import start_scheduler

load_dotenv()

# ── APP SETUP ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins="*") 
app.config['JWT_SECRET_KEY']               = os.environ.get('JWT_SECRET_KEY', 'dev-only-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES']     = datetime.timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES']    = datetime.timedelta(days=30)
app.config['JWT_TOKEN_LOCATION']           = ['headers']

jwt     = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins='*')
limiter  = Limiter(app=app, key_func=get_remote_address, default_limits=[])

# ── DATABASE ─────────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     'localhost',
    'port':     5432,
    'dbname':   'smartbell',
    'user':     'postgres',
    'password': os.environ.get('DB_PASSWORD', 'Niyomugabo@20171'),
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

# ── ARDUINO ──────────────────────────────────────────────────────────────────
arduino         = None
ack_fail_count  = 0
arduino_lock    = threading.Lock()

def connect_arduino():
    global arduino
    ports = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']
    for p in ports:
        try:
            arduino = serial.Serial(p, 9600, timeout=2)
            datetime.time
            import time; time.sleep(2)
            print(f"✅ Arduino connected on {p}")
            return
        except Exception:
            continue
    print("⚠ Arduino not found — simulation mode")

# ── VALID VALUES ─────────────────────────────────────────────────────────────
VALID_PATTERNS = {
    'LONG_SHORT', 'TRIPLE_SHORT', 'TRIPLE_LONG', 'EMERGENCY',
    'WARNING', 'DOUBLE_PULSE', 'ASCENDING', 'DESCENDING', 'TRIPLE_DOUBLE'
}
VALID_LED_COLORS = {'GREEN', 'YELLOW', 'RED', 'OFF'}
VALID_SITUATION_TYPES = {
    'CLASS', 'BREAK', 'LUNCH', 'EXAM', 'EMERGENCY',
    'WARNING', 'ASSEMBLY', 'HOLIDAY', 'CUSTOM'
}

def validate_pattern(p):
    return p if p in VALID_PATTERNS else 'LONG_SHORT'

def validate_led(c):
    return c if c in VALID_LED_COLORS else 'GREEN'

def validate_situation(s):
    return s if s in VALID_SITUATION_TYPES else 'CLASS'

def validate_time(t):
    return t if re.match(r'^\d{2}:\d{2}$', str(t)) else None

def pad16(s):
    return (str(s) + ' ' * 16)[:16]

# ── ARDUINO COMMUNICATION ─────────────────────────────────────────────────────
def send_to_arduino(command: str) -> bool:
    global arduino, ack_fail_count
    with arduino_lock:
        if arduino and arduino.is_open:
            try:
                arduino.write((command + '\n').encode())
                arduino.flush()
                response = arduino.readline().decode().strip()
                if response in ('OK', 'PONG', 'READY'):
                    ack_fail_count = 0
                    return True
                else:
                    print(f"⚠ Arduino unexpected response: '{response}'")
                    ack_fail_count += 1
                    if ack_fail_count >= 3:
                        socketio.emit('arduino_error', {
                            'message': 'Arduino not responding — check USB connection',
                            'fail_count': ack_fail_count
                        })
                    return False
            except Exception as e:
                print(f"⚠ Arduino ACK timeout: {e}")
                ack_fail_count += 1
                if ack_fail_count >= 3:
                    socketio.emit('arduino_error', {
                        'message': f'Arduino communication error: {str(e)}',
                        'fail_count': ack_fail_count
                    })
                return False
        else:
            print(f"[SIMULATE] → Arduino: {command}")
            return False

# ── RING BELL ─────────────────────────────────────────────────────────────────
def ring_bell(schedule: dict, triggered_by: str = 'schedule', user_id=None):
    pattern  = validate_pattern(schedule.get('pattern', 'LONG_SHORT'))
    led      = validate_led(schedule.get('led_color', 'GREEN'))
    line1    = pad16(schedule.get('lcd_line1', schedule.get('name', '')))
    line2    = pad16(schedule.get('lcd_line2', ''))
    cmd      = f"BELL|{pattern}|{line1}|{line2}|{led}"
    send_to_arduino(cmd)

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        """INSERT INTO ring_logs
           (schedule_name, triggered_by, user_id, situation_type, pattern, led_color)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (schedule.get('name'), triggered_by, user_id,
         schedule.get('situation_type', 'CLASS'), pattern, led)
    )
    conn.commit(); cur.close(); conn.close()

    socketio.emit('bell_rang', {
        'name':    schedule.get('name'),
        'time':    datetime.datetime.now().strftime('%H:%M'),
        'pattern': pattern,
        'led':     led,
    })

# ── LCD SITUATION UPDATE ──────────────────────────────────────────────────────
def update_lcd_situation():
    from lcd_engine import get_idle_display
    now      = datetime.datetime.now()
    now_time = now.strftime('%H:%M')
    try:
        # Check for manual LCD override first
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT value FROM app_settings WHERE key='lcd_override'")
        override = cur.fetchone()
        if override:
            import json
            data  = json.loads(override['value'])
            line1 = pad16(data.get('line1', ''))
            line2 = pad16(data.get('line2', ''))
            cur.close(); conn.close()
            send_to_arduino(f"STATUS|{line1}|{line2}")
            return

        # Find most recently rung bell today
        cur.execute("""
            SELECT s.name, s.situation_type, s.lcd_idle_line1, s.lcd_idle_line2, s.ring_time
            FROM schedules s
            JOIN ring_logs r ON r.schedule_name = s.name
            WHERE DATE(r.rang_at) = CURRENT_DATE AND s.active = 1
            ORDER BY s.ring_time DESC LIMIT 1
        """)
        current = cur.fetchone()

        # Find next upcoming bell
        cur.execute("""
            SELECT name, ring_time, situation_type FROM schedules
            WHERE ring_time > %s AND active = 1
            ORDER BY ring_time ASC LIMIT 1
        """, (now_time,))
        upcoming = cur.fetchone()
        cur.close(); conn.close()

        if not current and not upcoming:
            send_to_arduino(f"STATUS|SMARTBELL READY |{now_time}        ")
            return
        if not current:
            send_to_arduino(f"STATUS|SCHOOL STARTS  |AT {upcoming['ring_time']}        ")
            return
        if not upcoming:
            send_to_arduino("STATUS|SCHOOL ENDED  |SEE YOU TMRW!   ")
            return

        if current['lcd_idle_line1'] and current['lcd_idle_line1'].strip():
            line1 = current['lcd_idle_line1']
            line2 = current['lcd_idle_line2'] or ''
        else:
            line1, line2 = get_idle_display(
                situation_type=current['situation_type'],
                schedule_name=current['name'],
                next_bell_time=upcoming['ring_time'],
                next_bell_name=upcoming['name'],
                now=now
            )

        line1 = pad16(line1)
        line2 = pad16(line2)
        send_to_arduino(f"STATUS|{line1}|{line2}")
    except Exception as e:
        print(f"LCD update error: {e}")

# ── RBAC DECORATOR ────────────────────────────────────────────────────────────
from functools import wraps

def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get('role') not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ── DB INIT ───────────────────────────────────────────────────────────────────
def init_db():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule_templates (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            created_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL,
            ring_time TEXT NOT NULL, pattern TEXT NOT NULL DEFAULT 'LONG_SHORT',
            led_color TEXT NOT NULL DEFAULT 'GREEN',
            lcd_line1 TEXT NOT NULL, lcd_line2 TEXT NOT NULL DEFAULT '',
            lcd_idle_line1 TEXT NOT NULL DEFAULT '',
            lcd_idle_line2 TEXT NOT NULL DEFAULT '',
            situation_type TEXT NOT NULL DEFAULT 'CLASS',
            days_of_week TEXT NOT NULL DEFAULT 'MTWTF',
            template_id INTEGER REFERENCES schedule_templates(id) ON DELETE SET NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ring_logs (
            id SERIAL PRIMARY KEY, schedule_name TEXT,
            rang_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            triggered_by TEXT DEFAULT 'schedule',
            user_id INTEGER, situation_type TEXT,
            pattern TEXT, led_color TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY, value TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL, expires_at TIMESTAMP NOT NULL,
            used BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ring_logs_rang_at ON ring_logs(rang_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ring_logs_schedule_name ON ring_logs(schedule_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_schedules_ring_time ON schedules(ring_time)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_schedules_active ON schedules(active)")
    # Migrations for existing installs
    for col, defval in [
        ("days_of_week TEXT NOT NULL DEFAULT 'MTWTF'", "days_of_week"),
        ("situation_type TEXT NOT NULL DEFAULT 'CLASS'", "situation_type"),
        ("lcd_idle_line1 TEXT NOT NULL DEFAULT ''", "lcd_idle_line1"),
        ("lcd_idle_line2 TEXT NOT NULL DEFAULT ''", "lcd_idle_line2"),
        ("template_id INTEGER", "template_id"),
    ]:
        try:
            cur.execute(f"ALTER TABLE schedules ADD COLUMN IF NOT EXISTS {col}")
        except Exception: pass
    for col in ["situation_type TEXT", "pattern TEXT", "led_color TEXT"]:
        try:
            cur.execute(f"ALTER TABLE ring_logs ADD COLUMN IF NOT EXISTS {col}")
        except Exception: pass
    conn.commit()
    # Create default admin
    cur.execute("SELECT id FROM users WHERE username='admin'")
    if not cur.fetchone():
        hashed = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
        cur.execute("INSERT INTO users (username,password,role) VALUES ('admin',%s,'admin')", (hashed,))
        conn.commit()
        print("✅ Default admin created: admin / admin123")
    cur.close(); conn.close()

# ═════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone(); cur.close(); conn.close()
    if not user or not bcrypt.checkpw(password.encode(), user['password'].encode()):
        return jsonify({'error': 'Invalid credentials'}), 401
    claims        = {'role': user['role'], 'username': user['username']}
    access_token  = create_access_token(identity=str(user['id']), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user['id']), additional_claims=claims)
    return jsonify({'token': access_token, 'refresh_token': refresh_token,
                    'role': user['role'], 'username': user['username']})

@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    identity = get_jwt_identity()
    claims   = get_jwt()
    new_token = create_access_token(
        identity=identity,
        additional_claims={'role': claims.get('role'), 'username': claims.get('username')}
    )
    return jsonify({'token': new_token})

@app.route('/api/auth/register', methods=['POST'])
@require_role('admin')
def register():
    data     = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role     = data.get('role', 'viewer')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if role not in ('admin', 'teacher', 'viewer'):
        return jsonify({'error': 'Invalid role'}), 400
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,%s)",
                    (username, hashed, role))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'status': 'User created'})
    except psycopg2.errors.UniqueViolation:
        return jsonify({'error': 'Username already exists'}), 409

@app.route('/api/auth/signup-status', methods=['GET'])
def signup_status():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT value FROM app_settings WHERE key='signup_enabled'")
    row = cur.fetchone(); cur.close(); conn.close()
    return jsonify({'enabled': row and row[0] == 'true'})

@app.route('/api/auth/signup', methods=['POST'])
@limiter.limit("5 per minute")
def signup():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT value FROM app_settings WHERE key='signup_enabled'")
    row = cur.fetchone()
    if not row or row[0] != 'true':
        cur.close(); conn.close()
        return jsonify({'error': 'Self-signup is disabled'}), 403
    cur.close(); conn.close()
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,'teacher')",
                    (username, hashed))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'status': 'Account created'})
    except psycopg2.errors.UniqueViolation:
        return jsonify({'error': 'Username already exists'}), 409

@app.route('/api/auth/signup-toggle', methods=['POST'])
@require_role('admin')
def signup_toggle():
    data    = request.json or {}
    enabled = 'true' if data.get('enabled') else 'false'
    conn    = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO app_settings (key,value) VALUES ('signup_enabled',%s) "
                "ON CONFLICT (key) DO UPDATE SET value=%s", (enabled, enabled))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'signup_enabled': enabled == 'true'})

@app.route('/api/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    data       = request.json or {}
    current_pw = data.get('current_password', '')
    new_pw     = data.get('new_password', '')
    confirm_pw = data.get('confirm_password', '')
    if not all([current_pw, new_pw, confirm_pw]):
        return jsonify({'error': 'All fields are required'}), 400
    if new_pw != confirm_pw:
        return jsonify({'error': 'New passwords do not match'}), 400
    if len(new_pw) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if new_pw == current_pw:
        return jsonify({'error': 'New password must differ from current'}), 400
    uid  = get_jwt_identity()
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
    user = cur.fetchone()
    if not user or not bcrypt.checkpw(current_pw.encode(), user['password'].encode()):
        cur.close(); conn.close()
        return jsonify({'error': 'Current password is incorrect'}), 401
    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    cur2 = conn.cursor()
    cur2.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, uid))
    conn.commit(); cur.close(); cur2.close(); conn.close()
    return jsonify({'status': 'Password changed successfully'})

# ── FORGOT PASSWORD ───────────────────────────────────────────────────────────
@app.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit("10 per minute")
def forgot_password():
    # Always 200 — no user enumeration
    return jsonify({'message': 'Contact your administrator for a reset code.'})

@app.route('/api/auth/generate-reset-code', methods=['POST'])
@require_role('admin')
def generate_reset_code():
    data    = request.json or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    conn = get_db(); cur = conn.cursor()
    # Invalidate existing tokens
    cur.execute("UPDATE password_reset_tokens SET used=TRUE WHERE user_id=%s AND used=FALSE",
                (user_id,))
    code      = str(random.randint(100000, 999999))
    code_hash = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
    expires   = datetime.datetime.now() + datetime.timedelta(minutes=30)
    cur.execute("INSERT INTO password_reset_tokens (user_id,token_hash,expires_at) VALUES (%s,%s,%s)",
                (user_id, code_hash, expires))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'code': code, 'expires_in_minutes': 30})

@app.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit("10 per minute")
def reset_password():
    data     = request.json or {}
    username = data.get('username', '').strip()
    code     = data.get('code', '').strip()
    new_pw   = data.get('new_password', '')
    if not all([username, code, new_pw]):
        return jsonify({'error': 'All fields required'}), 400
    if len(new_pw) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    if not user:
        cur.close(); conn.close()
        return jsonify({'error': 'Invalid code or username'}), 400
    cur.execute("""
        SELECT * FROM password_reset_tokens
        WHERE user_id=%s AND used=FALSE AND expires_at > NOW()
        ORDER BY created_at DESC LIMIT 1
    """, (user['id'],))
    token = cur.fetchone()
    if not token or not bcrypt.checkpw(code.encode(), token['token_hash'].encode()):
        cur.close(); conn.close()
        return jsonify({'error': 'Invalid or expired reset code'}), 400
    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    cur2 = conn.cursor()
    cur2.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, user['id']))
    cur2.execute("UPDATE password_reset_tokens SET used=TRUE WHERE id=%s", (token['id'],))
    conn.commit(); cur.close(); cur2.close(); conn.close()
    return jsonify({'status': 'Password reset successfully'})

# ═════════════════════════════════════════════════════════════════════════════
# SCHEDULE ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/schedules', methods=['GET'])
@jwt_required()
def get_schedules():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM schedules ORDER BY ring_time ASC")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/schedules', methods=['POST'])
@require_role('admin', 'teacher')
def add_schedule():
    data = request.json or {}
    rt   = validate_time(data.get('ring_time'))
    if not rt:
        return jsonify({'error': 'ring_time must be HH:MM'}), 400
    claims = get_jwt()
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO schedules
          (name, ring_time, pattern, led_color, lcd_line1, lcd_line2,
           lcd_idle_line1, lcd_idle_line2, situation_type, days_of_week,
           template_id, active, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data.get('name', '').strip(),
        rt,
        validate_pattern(data.get('pattern', 'LONG_SHORT')),
        validate_led(data.get('led_color', 'GREEN')),
        data.get('lcd_line1', '')[:16],
        data.get('lcd_line2', '')[:16],
        data.get('lcd_idle_line1', '')[:16],
        data.get('lcd_idle_line2', '')[:16],
        validate_situation(data.get('situation_type', 'CLASS')),
        data.get('days_of_week', 'MTWTF'),
        data.get('template_id'),
        1,
        claims.get('username'),
    ))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Schedule created'}), 201

@app.route('/api/schedules/<int:sid>', methods=['PUT'])
@require_role('admin', 'teacher')
def update_schedule(sid):
    data = request.json or {}
    rt   = validate_time(data.get('ring_time'))
    if not rt:
        return jsonify({'error': 'ring_time must be HH:MM'}), 400
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        UPDATE schedules SET
          name=%s, ring_time=%s, pattern=%s, led_color=%s,
          lcd_line1=%s, lcd_line2=%s, lcd_idle_line1=%s, lcd_idle_line2=%s,
          situation_type=%s, days_of_week=%s, template_id=%s, active=%s
        WHERE id=%s
    """, (
        data.get('name', '').strip(), rt,
        validate_pattern(data.get('pattern', 'LONG_SHORT')),
        validate_led(data.get('led_color', 'GREEN')),
        data.get('lcd_line1', '')[:16],
        data.get('lcd_line2', '')[:16],
        data.get('lcd_idle_line1', '')[:16],
        data.get('lcd_idle_line2', '')[:16],
        validate_situation(data.get('situation_type', 'CLASS')),
        data.get('days_of_week', 'MTWTF'),
        data.get('template_id'),
        data.get('active', 1),
        sid
    ))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Updated'})

@app.route('/api/schedules/<int:sid>', methods=['DELETE'])
@require_role('admin')
def delete_schedule(sid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM schedules WHERE id=%s", (sid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Deleted'})

# ═════════════════════════════════════════════════════════════════════════════
# TEMPLATE ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/templates', methods=['GET'])
@jwt_required()
def get_templates():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM schedule_templates ORDER BY created_at DESC")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/templates', methods=['POST'])
@require_role('admin')
def create_template():
    data   = request.json or {}
    name   = data.get('name', '').strip()
    claims = get_jwt()
    if not name:
        return jsonify({'error': 'name required'}), 400
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO schedule_templates (name, created_by) VALUES (%s,%s)",
                (name, claims.get('username')))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Template created'}), 201

@app.route('/api/templates/<int:tid>/activate', methods=['PUT'])
@require_role('admin')
def activate_template(tid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE schedule_templates SET is_active=FALSE")
    cur.execute("UPDATE schedule_templates SET is_active=TRUE WHERE id=%s", (tid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Template activated'})

@app.route('/api/templates/<int:tid>', methods=['DELETE'])
@require_role('admin')
def delete_template(tid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE schedules SET template_id=NULL WHERE template_id=%s", (tid,))
    cur.execute("DELETE FROM schedule_templates WHERE id=%s", (tid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Template deleted'})

# ═════════════════════════════════════════════════════════════════════════════
# RING / CONTROL ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/ring-now', methods=['POST'])
@require_role('admin', 'teacher')
def ring_now():
    data   = request.json or {}
    claims = get_jwt()
    uid    = get_jwt_identity()
    schedule = {
        'name':          data.get('name', 'MANUAL'),
        'pattern':       validate_pattern(data.get('pattern', 'LONG_SHORT')),
        'led_color':     validate_led(data.get('led_color', 'GREEN')),
        'lcd_line1':     data.get('lcd_line1', 'MANUAL RING')[:16],
        'lcd_line2':     data.get('lcd_line2', '')[:16],
        'situation_type': validate_situation(data.get('situation_type', 'CLASS')),
    }
    ring_bell(schedule, triggered_by='manual', user_id=uid)
    return jsonify({'status': 'Ringing'})

@app.route('/api/ring-stop', methods=['POST'])
@require_role('admin', 'teacher')
def ring_stop():
    uid = get_jwt_identity()
    send_to_arduino("STOP")
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO ring_logs (schedule_name, triggered_by, user_id) VALUES ('STOP','manual_stop',%s)", (uid,))
    conn.commit(); cur.close(); conn.close()
    socketio.emit('bell_stopped', {'time': datetime.datetime.now().strftime('%H:%M')})
    # Restore LCD after 2s
    import threading
    threading.Timer(2.0, update_lcd_situation).start()
    return jsonify({'status': 'Bell silenced'})

@app.route('/api/arduino/ping', methods=['GET'])
@require_role('admin', 'teacher')
def arduino_ping():
    ok = send_to_arduino("PING")
    return jsonify({'status': 'ok' if ok else 'timeout'})

# ── LCD OVERRIDE ──────────────────────────────────────────────────────────────
@app.route('/api/lcd-override', methods=['POST'])
@require_role('admin', 'teacher')
def lcd_override():
    import json
    data  = request.json or {}
    line1 = data.get('line1', '')[:16]
    line2 = data.get('line2', '')[:16]
    val   = json.dumps({'line1': line1, 'line2': line2})
    conn  = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO app_settings (key,value) VALUES ('lcd_override',%s) "
                "ON CONFLICT (key) DO UPDATE SET value=%s", (val, val))
    conn.commit(); cur.close(); conn.close()
    send_to_arduino(f"STATUS|{pad16(line1)}|{pad16(line2)}")
    socketio.emit('lcd_updated', {'line1': line1, 'line2': line2})
    return jsonify({'status': 'LCD updated'})

@app.route('/api/lcd-override', methods=['DELETE'])
@require_role('admin')
def clear_lcd_override():
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM app_settings WHERE key='lcd_override'")
    conn.commit(); cur.close(); conn.close()
    update_lcd_situation()
    return jsonify({'status': 'Override cleared'})

# ═════════════════════════════════════════════════════════════════════════════
# LOGS & ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/logs', methods=['GET'])
@jwt_required()
def get_logs():
    limit = int(request.args.get('limit', 50))
    conn  = get_db()
    cur   = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM ring_logs ORDER BY rang_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/logs/stats', methods=['GET'])
@jwt_required()
def get_log_stats():
    days = int(request.args.get('days', 7))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT DATE(rang_at) as date, COUNT(*) as count
        FROM ring_logs
        WHERE rang_at >= NOW() - INTERVAL '%s days'
        GROUP BY DATE(rang_at) ORDER BY date ASC
    """, (days,))
    daily = cur.fetchall()
    cur.execute("""
        SELECT triggered_by, COUNT(*) as count FROM ring_logs
        WHERE rang_at >= NOW() - INTERVAL '%s days'
        GROUP BY triggered_by
    """, (days,))
    by_type = cur.fetchall()
    cur.execute("""
        SELECT EXTRACT(HOUR FROM rang_at)::int as hour, COUNT(*) as count
        FROM ring_logs WHERE rang_at >= NOW() - INTERVAL '%s days'
        GROUP BY hour ORDER BY hour ASC
    """, (days,))
    by_hour = cur.fetchall()
    cur.close(); conn.close()
    return jsonify({
        'daily_counts': [{'date': str(r['date']), 'count': r['count']} for r in daily],
        'by_type':      [{'triggered_by': r['triggered_by'], 'count': r['count']} for r in by_type],
        'by_hour':      [{'hour': r['hour'], 'count': r['count']} for r in by_hour],
    })

# ═════════════════════════════════════════════════════════════════════════════
# STATUS & HEALTH
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/status', methods=['GET'])
def get_status():
    now_time = datetime.datetime.now().strftime('%H:%M:%S')
    conn     = get_db()
    cur      = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) as c FROM ring_logs WHERE DATE(rang_at)=CURRENT_DATE")
    rings_today = cur.fetchone()['c']
    cur.execute("""
        SELECT * FROM schedules WHERE ring_time > %s AND active=1
        ORDER BY ring_time ASC LIMIT 1
    """, (now_time[:5],))
    next_bell = cur.fetchone()
    cur.close(); conn.close()
    return jsonify({
        'time':         now_time,
        'rings_today':  rings_today,
        'next_bell':    dict(next_bell) if next_bell else None,
        'arduino':      'connected' if arduino and arduino.is_open else 'disconnected',
    })

@app.route('/api/health', methods=['GET'])
@require_role('admin')
def get_health():
    try:
        import psutil, time
        temp = None
        try:
            with open('/sys/class/thermal/thermal_zone0/temp') as f:
                temp = int(f.read()) / 1000.0
        except Exception:
            pass
        boot_time = psutil.boot_time()
        uptime_h  = (time.time() - boot_time) / 3600
        return jsonify({
            'cpu_temp_c':   temp,
            'cpu_percent':  psutil.cpu_percent(interval=1),
            'ram_percent':  psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'uptime_hours': round(uptime_h, 1),
            'arduino':      'connected' if arduino and arduino.is_open else 'disconnected',
        })
    except ImportError:
        return jsonify({'error': 'psutil not installed — run: pip install psutil'}), 500

# ═════════════════════════════════════════════════════════════════════════════
# USERS
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/users', methods=['GET'])
@require_role('admin')
def get_users():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, username, role, created_at FROM users ORDER BY id")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/users/<int:uid>', methods=['PUT'])
@require_role('admin')
def update_user(uid):
    data = request.json or {}
    role = data.get('role')
    if role not in ('admin', 'teacher', 'viewer'):
        return jsonify({'error': 'Invalid role'}), 400
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE users SET role=%s WHERE id=%s", (role, uid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Updated'})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@require_role('admin')
def delete_user(uid):
    me = int(get_jwt_identity())
    if uid == me:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (uid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Deleted'})

# ── ADMIN RESET PASSWORD ──────────────────────────────────────────────────────
@app.route('/api/auth/admin-reset-password', methods=['POST'])
@require_role('admin')
def admin_reset_password():
    data   = request.json or {}
    uid    = data.get('user_id')
    new_pw = data.get('new_password', '')
    if not uid or not new_pw:
        return jsonify({'error': 'user_id and new_password required'}), 400
    if len(new_pw) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, uid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'status': 'Password reset successfully'})

# ═════════════════════════════════════════════════════════════════════════════
# STARTUP
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    init_db()
    connect_arduino()
    start_scheduler(ring_bell, update_lcd_situation)
    print("🔔 SmartBell v2.0 running at http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)