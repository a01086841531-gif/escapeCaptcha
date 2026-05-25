-- SQL: create table to store captured client events in batches
-- Enable pgcrypto for gen_random_uuid()
create extension if not exists "pgcrypto";

create table if not exists captcha_event_batches (
  id uuid primary key default gen_random_uuid(),
  session_id text,
  page text,
  user_agent text,
  events jsonb not null,
  created_at timestamptz default now()
);

create index if not exists captcha_event_batches_session_idx on captcha_event_batches (session_id);

-- Example usage:
-- INSERT INTO captcha_event_batches (session_id, page, user_agent, events) VALUES ('abc', '/', 'ua', '[{"type":"click","x":10}]');
