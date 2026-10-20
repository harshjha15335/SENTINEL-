-- Independent of SENTINEL's Alembic schema. Only service_role may access the inbox.
create table if not exists public.sentinel_webhook_inbox (
  id uuid primary key default gen_random_uuid(),
  provider_event_id text not null unique check (length(provider_event_id) between 1 and 128),
  event_type text not null check (length(event_type) between 1 and 128),
  raw_body text not null check (octet_length(raw_body) <= 262144),
  signature_headers jsonb not null,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  attempts integer not null default 0,
  lease_token uuid,
  available_at timestamptz not null default now(),
  last_error text
);
alter table public.sentinel_webhook_inbox enable row level security;
revoke all on public.sentinel_webhook_inbox from public, anon, authenticated;
grant select, insert, update on public.sentinel_webhook_inbox to service_role;
create index if not exists sentinel_webhook_pending
  on public.sentinel_webhook_inbox (available_at, received_at) where processed_at is null;

create or replace function public.sentinel_enqueue_webhook(
  p_event_id text, p_event_type text, p_raw_body text, p_headers jsonb
) returns boolean language plpgsql set search_path = '' as $$
declare inserted_id uuid; previous_body text;
begin
  if (p_raw_body::jsonb ->> 'id') is distinct from p_event_id
    or (p_raw_body::jsonb ->> 'event_type') is distinct from p_event_type then
    raise check_violation using message = 'Event metadata does not match body';
  end if;
  insert into public.sentinel_webhook_inbox(provider_event_id, event_type, raw_body, signature_headers)
    values (p_event_id, p_event_type, p_raw_body, p_headers)
    on conflict (provider_event_id) do nothing returning id into inserted_id;
  if inserted_id is not null then return true; end if;
  select raw_body into previous_body from public.sentinel_webhook_inbox where provider_event_id = p_event_id;
  if previous_body is distinct from p_raw_body then
    raise unique_violation using message = 'Event id already has a different body';
  end if;
  return false;
end;
$$;

create or replace function public.sentinel_claim_webhooks(p_limit integer default 25)
returns setof public.sentinel_webhook_inbox language sql set search_path = '' as $$
  update public.sentinel_webhook_inbox as inbox
  set lease_token = gen_random_uuid(), available_at = now() + interval '2 minutes', attempts = inbox.attempts + 1
  where inbox.id in (
    select id from public.sentinel_webhook_inbox
    where processed_at is null and available_at <= now() and attempts < 10
    order by received_at limit greatest(1, least(p_limit, 50)) for update skip locked
  ) returning inbox.*;
$$;

create or replace function public.sentinel_finish_webhook(p_id uuid, p_lease_token uuid, p_success boolean, p_error text default null)
returns boolean language plpgsql set search_path = '' as $$
begin
  update public.sentinel_webhook_inbox
  set processed_at = case when p_success then now() else null end,
      available_at = now() + interval '1 minute', lease_token = null,
      last_error = case when p_success then null else left(p_error, 100) end
  where id = p_id and lease_token = p_lease_token and processed_at is null;
  return found;
end;
$$;

revoke all on function public.sentinel_enqueue_webhook(text, text, text, jsonb) from public, anon, authenticated;
revoke all on function public.sentinel_claim_webhooks(integer) from public, anon, authenticated;
revoke all on function public.sentinel_finish_webhook(uuid, uuid, boolean, text) from public, anon, authenticated;
grant execute on function public.sentinel_enqueue_webhook(text, text, text, jsonb) to service_role;
grant execute on function public.sentinel_claim_webhooks(integer) to service_role;
grant execute on function public.sentinel_finish_webhook(uuid, uuid, boolean, text) to service_role;
notify pgrst, 'reload schema';
