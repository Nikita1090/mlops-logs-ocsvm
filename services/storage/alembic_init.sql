-- =====================================================================
-- Alembic-like init script for Storage Service
-- Создаёт базовые таблицы, если их ещё нет.
-- Таблицы:
--   logs          — общий пример сырых логов (оставлена для совместимости)
--   features      — ссылка на внешнее хранилище фич (совместимость)
--   models        — реестр ML-моделей/артефактов
--   bgl_logs      — сырые строки BGL (если вдруг захочешь хранить текст)
--   bgl_vectors   — разрежённые векторные представления (CSR как JSON)
-- Также создаются базовые индексы по часто используемым полям.
-- =====================================================================

-- -------------------------------
-- Общие таблицы (совместимость)
-- -------------------------------
CREATE TABLE IF NOT EXISTS logs (
  id        SERIAL PRIMARY KEY,
  timestamp VARCHAR(64),
  level     VARCHAR(16),
  source    VARCHAR(64),
  message   TEXT
);

CREATE TABLE IF NOT EXISTS features (
  id         SERIAL PRIMARY KEY,
  log_id     INTEGER,
  vector_ref VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS models (
  id           SERIAL PRIMARY KEY,
  name         VARCHAR(128),
  version      VARCHAR(64),
  path         VARCHAR(256),
  metric_aupr  DOUBLE PRECISION DEFAULT 0.0,
  notes        TEXT DEFAULT ''
);

-- Полезные индексы для models
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_models_name_version' AND n.nspname = 'public'
  ) THEN
    CREATE INDEX idx_models_name_version ON models (name, version);
  END IF;
END$$;

-- ---------------------------------------
-- BGL: сырые строки (опционально)
-- ---------------------------------------
CREATE TABLE IF NOT EXISTS bgl_logs (
  id         SERIAL PRIMARY KEY,
  line_id    INTEGER,
  alert_tag  VARCHAR(64),
  is_alert   BOOLEAN,
  raw        TEXT,
  message    TEXT
);

-- Индексы для bgl_logs
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_bgl_logs_line_id' AND n.nspname = 'public'
  ) THEN
    CREATE INDEX idx_bgl_logs_line_id ON bgl_logs (line_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_bgl_logs_is_alert' AND n.nspname = 'public'
  ) THEN
    CREATE INDEX idx_bgl_logs_is_alert ON bgl_logs (is_alert);
  END IF;
END$$;

-- ---------------------------------------
-- BGL: векторные представления (CSR)
--   indices / values — JSON-массивы
--   dim              — размерность пространства
-- ---------------------------------------
CREATE TABLE IF NOT EXISTS bgl_vectors (
  id           SERIAL PRIMARY KEY,
  line_id      INTEGER,
  alert_tag    VARCHAR(64),
  is_alert     BOOLEAN,
  template_id  INTEGER,
  dim          INTEGER,
  indices      TEXT,     -- JSON array of ints (CSR.indices)
  values       TEXT      -- JSON array of floats (CSR.data)
);

-- Индексы для bgl_vectors
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_bgl_vectors_line_id' AND n.nspname = 'public'
  ) THEN
    CREATE INDEX idx_bgl_vectors_line_id ON bgl_vectors (line_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_bgl_vectors_is_alert' AND n.nspname = 'public'
  ) THEN
    CREATE INDEX idx_bgl_vectors_is_alert ON bgl_vectors (is_alert);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_bgl_vectors_template_id' AND n.nspname = 'public'
  ) THEN
    CREATE INDEX idx_bgl_vectors_template_id ON bgl_vectors (template_id);
  END IF;
END$$;

