CREATE TABLE IF NOT EXISTS logs (
  id SERIAL PRIMARY KEY,
  timestamp VARCHAR(64),
  level VARCHAR(16),
  source VARCHAR(64),
  message TEXT
);

CREATE TABLE IF NOT EXISTS features (
  id SERIAL PRIMARY KEY,
  log_id INTEGER,
  vector_ref VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS models (
  id SERIAL PRIMARY KEY,
  name VARCHAR(128),
  version VARCHAR(64),
  path VARCHAR(256),
  metric_aupr DOUBLE PRECISION DEFAULT 0.0,
  notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bgl_logs (
  id SERIAL PRIMARY KEY,
  line_id INTEGER,
  alert_tag VARCHAR(64),
  is_alert BOOLEAN,
  raw TEXT,
  message TEXT
);

