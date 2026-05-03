-- SmartBell v2.0 — Database Migration
-- Run once: psql -U postgres -d smartbell -f migration_v2.sql

-- Schedule templates
CREATE TABLE IF NOT EXISTS schedule_templates (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT FALSE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- New columns on schedules
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS days_of_week   TEXT NOT NULL DEFAULT 'MTWTF';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS situation_type TEXT NOT NULL DEFAULT 'CLASS';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS lcd_idle_line1 TEXT NOT NULL DEFAULT '';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS lcd_idle_line2 TEXT NOT NULL DEFAULT '';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS template_id    INTEGER REFERENCES schedule_templates(id) ON DELETE SET NULL;

-- New columns on ring_logs
ALTER TABLE ring_logs ADD COLUMN IF NOT EXISTS situation_type TEXT;
ALTER TABLE ring_logs ADD COLUMN IF NOT EXISTS pattern        TEXT;
ALTER TABLE ring_logs ADD COLUMN IF NOT EXISTS led_color      TEXT;

-- Password reset tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_ring_logs_rang_at       ON ring_logs(rang_at DESC);
CREATE INDEX IF NOT EXISTS idx_ring_logs_schedule_name ON ring_logs(schedule_name);
CREATE INDEX IF NOT EXISTS idx_schedules_ring_time     ON schedules(ring_time);
CREATE INDEX IF NOT EXISTS idx_schedules_active        ON schedules(active);

-- Done
SELECT 'Migration complete' AS status;