"""
SmartBell v2.0 — LCD Situation Engine (lcd_engine.py)
Computes what the LCD should show between bell rings.
Called every minute by the scheduler.
"""

import datetime


def get_idle_display(situation_type, schedule_name, next_bell_time, next_bell_name, now):
    """
    Returns (line1, line2) each up to 16 chars.
    Based on the situation type of the most recently rung bell.
    """
    time_str = now.strftime('%H:%M')

    if situation_type == 'CLASS':
        line1 = (schedule_name or 'CLASS').upper()[:16]
        line2 = f"NEXT: {next_bell_time}" if next_bell_time else time_str
        return line1, line2

    elif situation_type == 'BREAK':
        line1 = "BREAK TIME"
        mins_left = _minutes_until(next_bell_time, now) if next_bell_time else None
        line2 = f"{mins_left} MIN REMAIN" if mins_left else "ENJOY BREAK"
        return line1, line2

    elif situation_type == 'LUNCH':
        line1 = "LUNCH BREAK"
        mins_left = _minutes_until(next_bell_time, now) if next_bell_time else None
        line2 = f"{mins_left} MIN REMAIN" if mins_left else "ENJOY LUNCH"
        return line1, line2

    elif situation_type == 'EXAM':
        line1 = "EXAM IN PROG."
        line2 = f"ENDS: {next_bell_time}" if next_bell_time else "SILENCE PLEASE"
        return line1, line2

    elif situation_type == 'EMERGENCY':
        line1 = "!! EMERGENCY !!"
        line2 = "FOLLOW INSTRUCT"
        return line1, line2

    elif situation_type == 'WARNING':
        line1 = "5 MIN WARNING"
        line2 = (next_bell_name or 'PREPARE NOW')[:16]
        return line1, line2

    elif situation_type == 'ASSEMBLY':
        line1 = "ASSEMBLY TIME"
        line2 = "GO TO HALL NOW"
        return line1, line2

    elif situation_type == 'HOLIDAY':
        line1 = "HOLIDAY"
        line2 = "SCHOOL CLOSED"
        return line1, line2

    else:  # CUSTOM or unknown
        return (schedule_name or 'SMARTBELL').upper()[:16], time_str


def _minutes_until(time_str, now):
    """Returns integer minutes until HH:MM, or None."""
    try:
        target = datetime.datetime.strptime(time_str, '%H:%M').replace(
            year=now.year, month=now.month, day=now.day)
        delta = (target - now).total_seconds() / 60
        return int(delta) if delta > 0 else None
    except Exception:
        return None