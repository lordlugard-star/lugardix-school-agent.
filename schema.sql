-- School AI Agent: demo database schema (Supabase / PostgreSQL)
-- Extracted from the live demo project. Synthetic data only; no real school records.
-- gen_random_uuid() is available by default on Supabase.

create table public.admins (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  email       text not null unique,
  telegram_id text not null unique,   -- admin identity used by the allow-list; now holds the admin's WhatsApp sender number (column predates the move from Telegram)
  role        text not null,
  created_at  timestamptz not null default now()
);

create table public.students (
  id              uuid primary key default gen_random_uuid(),
  student_number  text not null unique,          -- human-facing lookup key, e.g. L200-001
  name            text not null,
  email           text not null,
  whatsapp_number text not null,
  created_at      timestamptz not null default now()
);

create table public.parents (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,
  email           text not null,
  whatsapp_number text not null,
  created_at      timestamptz not null default now()
);

-- Link table: relationships come from ids and foreign keys, never from names.
create table public.student_parents (
  id           uuid primary key default gen_random_uuid(),
  student_id   uuid not null references public.students(id),
  parent_id    uuid not null references public.parents(id),
  relationship text not null,
  constraint student_parents_pair_unique unique (student_id, parent_id)
);

create table public.messages (
  id           uuid primary key default gen_random_uuid(),
  admin_id     uuid not null references public.admins(id),
  content      text not null,
  channel      text not null,
  status       text not null default 'pending_confirmation',
  scheduled_at timestamptz,
  created_at   timestamptz not null default now(),
  sent_at      timestamptz,
  constraint messages_channel_check check (channel = any (array['whatsapp','email'])),
  constraint messages_status_check  check (status  = any (array['pending_confirmation','scheduled','sending','sent','failed','cancelled']))
);

create table public.message_recipients (
  id              uuid primary key default gen_random_uuid(),
  message_id      uuid not null references public.messages(id) on delete cascade,
  student_id      uuid references public.students(id),
  parent_id       uuid references public.parents(id),
  destination     text not null,
  delivery_status text not null default 'pending',
  error_message   text,
  sent_at         timestamptz,
  -- exactly one recipient type per row
  constraint message_recipient_exactly_one_person check ((student_id is not null) <> (parent_id is not null)),
  constraint message_recipients_delivery_status_check check (delivery_status = any (array['pending','sending','sent','failed','cancelled']))
);

-- Row Level Security is enabled on every table.
-- The n8n backend uses the service_role key (server-side only), which bypasses RLS.
-- With RLS on and no policies, the public anon key can read and write nothing.
alter table public.admins             enable row level security;
alter table public.students           enable row level security;
alter table public.parents            enable row level security;
alter table public.student_parents    enable row level security;
alter table public.messages           enable row level security;
alter table public.message_recipients enable row level security;
