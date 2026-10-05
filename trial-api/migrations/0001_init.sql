PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS trial_records (
  record_id TEXT PRIMARY KEY,
  company_id TEXT NOT NULL,
  verified_at INTEGER,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS storage_usage (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  used_bytes INTEGER NOT NULL DEFAULT 0 CHECK (used_bytes >= 0),
  reserved_bytes INTEGER NOT NULL DEFAULT 0 CHECK (reserved_bytes >= 0),
  CHECK (used_bytes + reserved_bytes <= 7000000000)
);
INSERT OR IGNORE INTO storage_usage(singleton, used_bytes, reserved_bytes) VALUES (1, 0, 0);

CREATE TABLE IF NOT EXISTS photos (
  photo_id TEXT PRIMARY KEY,
  record_id TEXT NOT NULL REFERENCES trial_records(record_id) ON DELETE CASCADE,
  slot INTEGER NOT NULL CHECK (slot IN (1, 2)),
  content_type TEXT NOT NULL CHECK (content_type IN ('image/jpeg', 'image/png', 'image/webp')),
  byte_size INTEGER NOT NULL CHECK (byte_size > 0 AND byte_size <= 12582912),
  object_key TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL CHECK (state IN ('reserved', 'stored')),
  uploaded_by TEXT NOT NULL,
  screened_by TEXT,
  uploaded_at INTEGER NOT NULL,
  reservation_expires_at INTEGER,
  UNIQUE(record_id, slot)
);
CREATE INDEX IF NOT EXISTS photos_record_state ON photos(record_id, state);
CREATE INDEX IF NOT EXISTS photos_reservation_expiry ON photos(state, reservation_expires_at);

CREATE TRIGGER IF NOT EXISTS photos_reserve_before_insert
BEFORE INSERT ON photos
BEGIN
  SELECT CASE WHEN NEW.state <> 'reserved' OR NEW.screened_by IS NOT NULL THEN RAISE(ABORT, 'photo must start reserved') END;
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM trial_records WHERE record_id = NEW.record_id AND verified_at IS NOT NULL
  ) THEN RAISE(ABORT, 'verified record required') END;
  SELECT CASE WHEN (
    SELECT used_bytes + reserved_bytes + NEW.byte_size FROM storage_usage WHERE singleton = 1
  ) > 7000000000 THEN RAISE(ABORT, 'trial storage full') END;
END;

CREATE TRIGGER IF NOT EXISTS photos_reserve_after_insert
AFTER INSERT ON photos
BEGIN
  UPDATE storage_usage SET reserved_bytes = reserved_bytes + NEW.byte_size WHERE singleton = 1;
END;

CREATE TRIGGER IF NOT EXISTS photos_transition_before_update
BEFORE UPDATE ON photos
BEGIN
  SELECT CASE WHEN NOT (
    OLD.state = 'reserved' AND NEW.state = 'stored' AND
    NEW.photo_id = OLD.photo_id AND NEW.record_id = OLD.record_id AND
    NEW.slot = OLD.slot AND NEW.content_type = OLD.content_type AND
    NEW.byte_size = OLD.byte_size AND NEW.object_key = OLD.object_key AND
    NEW.uploaded_by = OLD.uploaded_by AND NEW.uploaded_at = OLD.uploaded_at AND
    OLD.screened_by IS NULL AND NEW.screened_by IS NOT NULL AND
    NEW.reservation_expires_at IS NULL
  ) THEN RAISE(ABORT, 'invalid photo transition') END;
END;

CREATE TRIGGER IF NOT EXISTS photos_store_after_update
AFTER UPDATE OF state ON photos
WHEN OLD.state = 'reserved' AND NEW.state = 'stored'
BEGIN
  UPDATE storage_usage
  SET reserved_bytes = reserved_bytes - OLD.byte_size,
      used_bytes = used_bytes + NEW.byte_size
  WHERE singleton = 1;
END;

CREATE TRIGGER IF NOT EXISTS photos_account_after_delete
AFTER DELETE ON photos
BEGIN
  UPDATE storage_usage
  SET reserved_bytes = reserved_bytes - CASE WHEN OLD.state = 'reserved' THEN OLD.byte_size ELSE 0 END,
      used_bytes = used_bytes - CASE WHEN OLD.state = 'stored' THEN OLD.byte_size ELSE 0 END
  WHERE singleton = 1;
END;

CREATE TABLE IF NOT EXISTS rate_windows (
  window_key TEXT PRIMARY KEY,
  window_start INTEGER NOT NULL,
  request_count INTEGER NOT NULL CHECK (request_count > 0)
);
