-- OZ first-party analytics — D1 schema
-- Apply with:  wrangler d1 execute oz_analytics --local --file=worker/schema.sql
--              wrangler d1 execute oz_analytics --remote --file=worker/schema.sql

CREATE TABLE IF NOT EXISTS events (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  ts       INTEGER NOT NULL,           -- epoch milliseconds
  type     TEXT    NOT NULL,           -- event name (page_view, quote_request, ...)
  path     TEXT    NOT NULL,           -- normalized page path
  referrer TEXT,
  source   TEXT,                       -- utm_source / referral / direct
  medium   TEXT,
  campaign TEXT,
  visitor  TEXT,                       -- persistent anonymous id (localStorage)
  session  TEXT,                       -- per-visit id (sessionStorage)
  device   TEXT,                       -- desktop | mobile | tablet | bot
  country  TEXT,                       -- request.cf.country
  extra    TEXT                        -- JSON of any extra params
);
CREATE INDEX IF NOT EXISTS idx_events_ts    ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_type  ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_path  ON events(path);
CREATE INDEX IF NOT EXISTS idx_events_date ON events((ts / 86400000));

-- One aggregated row per calendar day (UTC). The Cron trigger fills this;
-- /a/report reads from here so it stays cheap as history grows.
CREATE TABLE IF NOT EXISTS daily_report (
  date      TEXT    PRIMARY KEY,        -- YYYY-MM-DD (UTC)
  generated INTEGER NOT NULL,           -- epoch ms of last aggregation
  payload   TEXT    NOT NULL            -- JSON of the full report
);
