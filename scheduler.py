# # Fixed scheduler.py — replaced ff"..." with f"..."
# from apscheduler.schedulers.background import BackgroundScheduler
# import psycopg2, psycopg2.extras, datetime

# _scheduler = None
# _ring_bell_fn = None
# _db_config = None

# def check_bells():
#     now = datetime.datetime.now()
#     now_time = now.strftime('%H:%M')
#     if now.weekday() >= 5:   # Skip Sat/Sun
#         return
#     try:
#         conn = psycopg2.connect(**_db_config)
#         cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
#         cur.execute("SELECT * FROM schedules WHERE ring_time=%s AND active=1", (now_time,))
#         schedules = cur.fetchall()
#         cur.close(); conn.close()
#         for s in schedules:
#             print(f"Auto-ringing: {s['name']} at {now_time}")   # FIX: was ff"..."
#             _ring_bell_fn(name=s['name'], pattern=s['pattern'],
#                           line1=s['lcd_line1'], line2=s['lcd_line2'],
#                           led=s['led_color'], triggered_by='schedule')
#     except Exception as e:
#         print(f"Scheduler error: {e}")

# def start_scheduler(ring_fn, db_config):
#     global _scheduler, _ring_bell_fn, _db_config
#     _ring_bell_fn = ring_fn
#     _db_config = db_config
#     _scheduler = BackgroundScheduler()
#     _scheduler.add_job(check_bells, 'interval', minutes=1, id='bell_check')
#     _scheduler.start()
#     print("Bell scheduler started")

"""
SmartBell v2.0 — Scheduler (scheduler.py)
- Uses cron (second=0) instead of interval for exact firing
- Duplicate-ring guard (90s window)
- Day-of-week filtering
- Template-aware scheduling
- LCD situation update on second=5
"""

import datetime
import psycopg2
import psycopg2.extras
from apscheduler.schedulers.background import BackgroundScheduler

# M T W T F S S (index 0=Mon, 6=Sun)
DAY_CHARS = ['M', 'T', 'W', 't', 'F', 'S', 's']

_scheduler = None


def start_scheduler(ring_bell_fn, update_lcd_fn):
    global _scheduler
    _scheduler = BackgroundScheduler()

    # Capture functions in closures
    def check_bells_job():
        _check_bells(ring_bell_fn)

    def lcd_update_job():
        try:
            update_lcd_fn()
        except Exception as e:
            print(f"LCD update error: {e}")

    # Fires at second=0 of every minute (exact timing)
    _scheduler.add_job(check_bells_job,  'cron', second=0,  id='bell_check')
    # LCD update fires 5 seconds after bell check
    _scheduler.add_job(lcd_update_job,   'cron', second=5,  id='lcd_update')

    _scheduler.start()
    print("✅ Bell scheduler started (cron mode)")


def _get_db():
    import os
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 5432)),
        dbname=os.environ.get('DB_NAME', 'smartbell'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'smartbell2024'),
    )


def _check_bells(ring_bell_fn):
    now       = datetime.datetime.now()
    now_str   = now.strftime('%H:%M')
    weekday   = now.weekday()
    day_char  = DAY_CHARS[weekday]

    try:
        conn = _get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Find active template (if any)
        cur.execute("SELECT id FROM schedule_templates WHERE is_active=TRUE LIMIT 1")
        tmpl = cur.fetchone()
        tmpl_id = tmpl['id'] if tmpl else None

        # Build query: only ring schedules for current template (or null template if none)
        if tmpl_id:
            cur.execute("""
                SELECT * FROM schedules
                WHERE ring_time=%s AND active=1 AND template_id=%s
            """, (now_str, tmpl_id))
        else:
            cur.execute("""
                SELECT * FROM schedules
                WHERE ring_time=%s AND active=1
                  AND (template_id IS NULL OR template_id = (
                      SELECT id FROM schedule_templates WHERE is_active=TRUE LIMIT 1
                  ))
            """, (now_str,))
        schedules = cur.fetchall()

        for s in schedules:
            # Day-of-week filter
            days = s.get('days_of_week', 'MTWTF')
            if day_char not in days:
                continue

            # Duplicate-ring guard: skip if rung within last 90 seconds
            cur.execute("""
                SELECT id FROM ring_logs
                WHERE schedule_name=%s
                  AND rang_at > NOW() - INTERVAL '90 seconds'
                LIMIT 1
            """, (s['name'],))
            if cur.fetchone():
                print(f"⏭ Duplicate ring guard — skipping {s['name']}")
                continue

            print(f"🔔 Ringing: {s['name']} at {now_str}")
            ring_bell_fn(dict(s), triggered_by='schedule')

        cur.close(); conn.close()
    except Exception as e:
        print(f"Scheduler error: {e}")