-- Backward-compatible receiver intake; no Edge Function redeployment required.
alter table public.sentinel_webhook_inbox
  add column if not exists data_origin text not null default 'LIVE_SANDBOX'
    check (data_origin in ('LIVE_SANDBOX','SIMULATED')),
  add column if not exists status text not null default 'PENDING'
    check (status in ('PENDING','RUNNING','PROCESSED','DEAD')),
  add column if not exists last_attempt_at timestamptz;
update public.sentinel_webhook_inbox set status='PROCESSED' where processed_at is not null;

drop function if exists public.sentinel_claim_webhooks(integer);
create or replace function public.sentinel_claim_webhooks(p_limit integer default 1, p_origin text default 'LIVE_SANDBOX')
returns setof public.sentinel_webhook_inbox language plpgsql set search_path = '' as $$
begin
  if p_origin not in ('LIVE_SANDBOX','SIMULATED') then raise invalid_parameter_value; end if;
  update public.sentinel_webhook_inbox set status='DEAD', lease_token=null, last_error='LeaseExhausted'
    where data_origin=p_origin and processed_at is null and status in ('PENDING','RUNNING') and attempts >= 10 and available_at <= now();
  return query update public.sentinel_webhook_inbox as inbox
    set status='RUNNING', lease_token=gen_random_uuid(), available_at=now()+interval '2 minutes',
      attempts=inbox.attempts+1, last_attempt_at=now()
    where inbox.id in (
      select id from public.sentinel_webhook_inbox
      where data_origin=p_origin and status in ('PENDING','RUNNING') and available_at<=now() and attempts<10
      order by received_at limit greatest(1,least(p_limit,10)) for update skip locked
    ) returning inbox.*;
end;
$$;

create or replace function public.sentinel_renew_webhook(p_id uuid,p_lease_token uuid)
returns boolean language plpgsql set search_path = '' as $$
begin
  update public.sentinel_webhook_inbox set available_at=now()+interval '2 minutes'
    where id=p_id and lease_token=p_lease_token and status='RUNNING' and available_at>now();
  return found;
end;
$$;

create or replace function public.sentinel_finish_webhook(p_id uuid,p_lease_token uuid,p_success boolean,p_error text default null)
returns boolean language plpgsql set search_path = '' as $$
begin
  update public.sentinel_webhook_inbox
    set status=case when p_success then 'PROCESSED' when attempts>=10 or p_error like 'PERMANENT_%' then 'DEAD' else 'PENDING' end,
      processed_at=case when p_success then now() else null end,
      available_at=now()+make_interval(secs=>least(300,5*power(2,least(attempts,6)))::double precision),
      lease_token=null, last_error=case when p_success then null else left(p_error,100) end
    where id=p_id and lease_token=p_lease_token and status='RUNNING' and available_at>now();
  return found;
end;
$$;

-- Fixtures use a separate privileged RPC and origin. Public receiver cannot set this origin.
create or replace function public.sentinel_enqueue_fixture(p_event_id text,p_event_type text,p_raw_body text,p_headers jsonb)
returns boolean language plpgsql set search_path = '' as $$
declare result boolean;
begin
  if p_event_id not like 'FIXTURE-%' then raise check_violation; end if;
  result=public.sentinel_enqueue_webhook(p_event_id,p_event_type,p_raw_body,p_headers);
  if not result and exists(select 1 from public.sentinel_webhook_inbox where provider_event_id=p_event_id and data_origin<>'SIMULATED') then
    raise check_violation using message='Fixture id conflicts with genuine intake';
  end if;
  update public.sentinel_webhook_inbox set data_origin='SIMULATED' where provider_event_id=p_event_id and attempts=0;
  return result;
end;
$$;

create or replace function public.sentinel_webhook_metrics()
returns jsonb language sql set search_path = '' as $$
  select coalesce(jsonb_agg(t),'[]'::jsonb) from (
    select data_origin,status,count(*) as count,min(received_at) as oldest_received_at,
      max(last_attempt_at) as last_attempt_at from public.sentinel_webhook_inbox group by data_origin,status
  ) t;
$$;
revoke all on function public.sentinel_claim_webhooks(integer,text) from public,anon,authenticated;
revoke all on function public.sentinel_renew_webhook(uuid,uuid) from public,anon,authenticated;
revoke all on function public.sentinel_enqueue_fixture(text,text,text,jsonb) from public,anon,authenticated;
revoke all on function public.sentinel_webhook_metrics() from public,anon,authenticated;
grant execute on function public.sentinel_claim_webhooks(integer,text) to service_role;
grant execute on function public.sentinel_renew_webhook(uuid,uuid) to service_role;
grant execute on function public.sentinel_enqueue_fixture(text,text,text,jsonb) to service_role;
grant execute on function public.sentinel_webhook_metrics() to service_role;
notify pgrst,'reload schema';
