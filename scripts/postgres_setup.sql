create table if not exists users (
  telegram_id bigint primary key,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  ban_until timestamptz
);
create table if not exists dialogs (
  id text primary key,
  user1 bigint not null,
  user2 bigint not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  reason text
);
create table if not exists topics (
  id text primary key,
  user_id bigint not null,
  text text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);
create table if not exists reports (
  id bigserial primary key,
  from_id bigint not null,
  target_id bigint not null,
  reason text,
  created_at timestamptz not null default now()
);