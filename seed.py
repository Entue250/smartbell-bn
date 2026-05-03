# # seed.py — PostgreSQL version
# import psycopg2

# DB_CONFIG = {
#     'host': 'localhost', 'port': 5432,
#     'dbname': 'smartbell', 'user': 'postgres',
#     'password': 'Niyomugabo@20171',  # Change this!
# }

# DEFAULT_SCHEDULE = [
#     ("School Opens", "07:30", "LONG_SHORT",   "GREEN",  "SCHOOL OPENS", "WELCOME!"),
#     ("Period 1",     "07:45", "LONG_SHORT",   "GREEN",  "PERIOD 1",     "07:45-08:35"),
#     ("Period 2",     "08:35", "LONG_SHORT",   "GREEN",  "PERIOD 2",     "08:35-09:25"),
#     ("Short Break",  "09:25", "TRIPLE_SHORT", "YELLOW", "BREAK TIME",   "15 MINUTES"),
#     ("Period 3",     "09:40", "LONG_SHORT",   "GREEN",  "PERIOD 3",     "09:40-10:30"),
#     ("Period 4",     "10:30", "LONG_SHORT",   "GREEN",  "PERIOD 4",     "10:30-11:20"),
#     ("Lunch Break",  "11:20", "TRIPLE_SHORT", "YELLOW", "LUNCH BREAK",  "45 MINUTES"),
#     ("Period 5",     "12:05", "LONG_SHORT",   "GREEN",  "PERIOD 5",     "12:05-13:00"),
#     ("School Ends",  "13:00", "TRIPLE_LONG",  "RED",    "SCHOOL ENDS!", "HAVE A NICE DAY"),
# ]

# conn = psycopg2.connect(**DB_CONFIG)
# cur = conn.cursor()
# for row in DEFAULT_SCHEDULE:
#     cur.execute(
#         "INSERT INTO schedules (name,ring_time,pattern,led_color,lcd_line1,lcd_line2) VALUES (%s,%s,%s,%s,%s,%s)",
#         row
#     )
# conn.commit(); cur.close(); conn.close()
# print("Default schedule inserted!")

"""
SmartBell v2 — seed.py
Inserts default 9-period school schedule.
Run ONCE after first setup: python seed.py
"""

import os
import psycopg2

DB_CONFIG = {
    'host':     'localhost',
    'port':     5432,
    'dbname':   'smartbell',
    'user':     'postgres',
    'password': os.environ.get('DB_PASSWORD', 'Niyomugabo@20171'),
}

SCHEDULES = [
    {
        'name': 'School Opens',   'ring_time': '07:30',
        'pattern': 'DOUBLE_PULSE', 'led_color': 'GREEN',
        'lcd_line1': 'SCHOOL OPENS', 'lcd_line2': 'WELCOME BACK',
        'lcd_idle_line1': '',        'lcd_idle_line2': '',
        'situation_type': 'ASSEMBLY', 'days_of_week': 'MTWTF',
    },
    {
        'name': 'Period 1 Start', 'ring_time': '07:45',
        'pattern': 'LONG_SHORT',  'led_color': 'GREEN',
        'lcd_line1': 'PERIOD 1',   'lcd_line2': 'CLASS BEGINS',
        'lcd_idle_line1': '',       'lcd_idle_line2': '',
        'situation_type': 'CLASS',  'days_of_week': 'MTWTF',
    },
    {
        'name': 'Period 2 Start', 'ring_time': '08:35',
        'pattern': 'LONG_SHORT',  'led_color': 'GREEN',
        'lcd_line1': 'PERIOD 2',   'lcd_line2': 'CLASS BEGINS',
        'lcd_idle_line1': '',       'lcd_idle_line2': '',
        'situation_type': 'CLASS',  'days_of_week': 'MTWTF',
    },
    {
        'name': 'Short Break',    'ring_time': '09:25',
        'pattern': 'TRIPLE_SHORT', 'led_color': 'YELLOW',
        'lcd_line1': 'BREAK TIME', 'lcd_line2': '15 MIN BREAK',
        'lcd_idle_line1': '',       'lcd_idle_line2': '',
        'situation_type': 'BREAK', 'days_of_week': 'MTWTF',
    },
    {
        'name': 'Period 3 Start', 'ring_time': '09:40',
        'pattern': 'LONG_SHORT',  'led_color': 'GREEN',
        'lcd_line1': 'PERIOD 3',   'lcd_line2': 'CLASS BEGINS',
        'lcd_idle_line1': '',       'lcd_idle_line2': '',
        'situation_type': 'CLASS',  'days_of_week': 'MTWTF',
    },
    {
        'name': 'Period 4 Start', 'ring_time': '10:30',
        'pattern': 'LONG_SHORT',  'led_color': 'GREEN',
        'lcd_line1': 'PERIOD 4',   'lcd_line2': 'CLASS BEGINS',
        'lcd_idle_line1': '',       'lcd_idle_line2': '',
        'situation_type': 'CLASS',  'days_of_week': 'MTWTF',
    },
    {
        'name': 'Lunch Break',    'ring_time': '11:20',
        'pattern': 'TRIPLE_SHORT', 'led_color': 'YELLOW',
        'lcd_line1': 'LUNCH BREAK','lcd_line2': '45 MIN LUNCH',
        'lcd_idle_line1': '',       'lcd_idle_line2': '',
        'situation_type': 'LUNCH', 'days_of_week': 'MTWTF',
    },
    {
        'name': 'Period 5 Start', 'ring_time': '12:05',
        'pattern': 'LONG_SHORT',  'led_color': 'GREEN',
        'lcd_line1': 'PERIOD 5',   'lcd_line2': 'CLASS BEGINS',
        'lcd_idle_line1': '',       'lcd_idle_line2': '',
        'situation_type': 'CLASS',  'days_of_week': 'MTWTF',
    },
    {
        'name': 'School Ends',    'ring_time': '13:00',
        'pattern': 'TRIPLE_LONG', 'led_color': 'RED',
        'lcd_line1': 'SCHOOL ENDS','lcd_line2': 'SEE YOU TMRW!',
        'lcd_idle_line1': '',       'lcd_idle_line2': '',
        'situation_type': 'CLASS',  'days_of_week': 'MTWTF',
    },
]

def seed():
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM schedules")
    count = cur.fetchone()[0]
    if count > 0:
        print(f"⚠  {count} schedules already exist. Skipping seed to avoid duplicates.")
        print("   Delete all schedules first if you want to reseed:")
        print("   psql -U postgres -d smartbell -c 'DELETE FROM schedules;'")
        cur.close(); conn.close()
        return

    for s in SCHEDULES:
        cur.execute("""
            INSERT INTO schedules
              (name, ring_time, pattern, led_color, lcd_line1, lcd_line2,
               lcd_idle_line1, lcd_idle_line2, situation_type, days_of_week,
               active, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,'seed')
        """, (
            s['name'], s['ring_time'], s['pattern'], s['led_color'],
            s['lcd_line1'], s['lcd_line2'],
            s['lcd_idle_line1'], s['lcd_idle_line2'],
            s['situation_type'], s['days_of_week'],
        ))
        print(f"✅  Added: {s['ring_time']} — {s['name']}")

    conn.commit()
    print(f"\n🎉 Seeded {len(SCHEDULES)} schedules successfully.")
    cur.close(); conn.close()

if __name__ == '__main__':
    seed()