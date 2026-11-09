const PAYPAL = "https://api-m.sandbox.paypal.com";
const MAX_BYTES = 256 * 1024;
const HEADER_NAMES = [
  "paypal-transmission-id",
  "paypal-transmission-time",
  "paypal-cert-url",
  "paypal-auth-algo",
  "paypal-transmission-sig",
];
type Dependencies = {
  env: (name: string) => string | undefined;
  fetch: typeof fetch;
};

class Rejected extends Error {
  constructor(public status: number, public code: string) {
    super(code);
  }
}

function response(status: number, body: object): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

async function bodyText(request: Request): Promise<string> {
  const reader = request.body?.getReader();
  if (!reader) throw new Rejected(400, "invalid_event");
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > MAX_BYTES) {
        await reader.cancel();
        throw new Rejected(413, "payload_too_large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.length;
  }
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    throw new Rejected(400, "invalid_event");
  }
}

export function createHandler(
  deps: Dependencies,
): (request: Request) => Promise<Response> {
  return async (request) => {
    if (request.method === "GET") {
      return response(200, { status: "ok", mode: "sandbox" });
    }
    if (request.method !== "POST") {
      return response(405, { error: "method_not_allowed" });
    }
    try {
      const headers: Record<string, string> = {};
      for (const name of HEADER_NAMES) {
        const value = request.headers.get(name);
        if (!value || value.length > 8192) {
          throw new Rejected(400, "invalid_signature_headers");
        }
        headers[name] = value;
      }
      let cert: URL;
      try {
        cert = new URL(headers["paypal-cert-url"]);
      } catch {
        throw new Rejected(400, "invalid_certificate_url");
      }
      if (
        cert.protocol !== "https:" || cert.username || cert.password ||
        cert.port || cert.search ||
        cert.hash || ![
          "api.paypal.com",
          "api.sandbox.paypal.com",
          "api-m.paypal.com",
          "api-m.sandbox.paypal.com",
        ].includes(cert.hostname) ||
        !cert.pathname.startsWith("/v1/notifications/certs/") ||
        headers["paypal-auth-algo"].toUpperCase() !== "SHA256WITHRSA"
      ) throw new Rejected(400, "invalid_signature_headers");

      const raw = await bodyText(request);
      let event: Record<string, unknown>;
      try {
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          throw new Error();
        }
        event = parsed;
      } catch {
        throw new Rejected(400, "invalid_event");
      }
      if (
        typeof event.id !== "string" || !event.id || event.id.length > 128 ||
        typeof event.event_type !== "string" || !event.event_type ||
        event.event_type.length > 128
      ) throw new Rejected(400, "invalid_event");

      const clientId = deps.env("SENTINEL_PAYPAL_CLIENT_ID");
      const secret = deps.env("SENTINEL_PAYPAL_CLIENT_SECRET");
      const webhookId = deps.env("SENTINEL_PAYPAL_WEBHOOK_ID");
      const supabase = deps.env("SUPABASE_URL");
      const serviceKey = deps.env("SUPABASE_SERVICE_ROLE_KEY");
      if (
        !clientId || !secret || !webhookId || webhookId === "WEBHOOK_ID" ||
        !supabase || !serviceKey
      ) {
        throw new Rejected(503, "webhook_not_configured");
      }
      const call = (url: string, init: RequestInit) =>
        deps.fetch(url, {
          ...init,
          redirect: "error",
          signal: AbortSignal.timeout(15_000),
        });
      const tokenResponse = await call(`${PAYPAL}/v1/oauth2/token`, {
        method: "POST",
        headers: {
          Authorization: `Basic ${btoa(`${clientId}:${secret}`)}`,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: "grant_type=client_credentials",
      });
      if (!tokenResponse.ok) {
        throw new Rejected(503, "verification_unavailable");
      }
      const token = await tokenResponse.json();
      if (typeof token.access_token !== "string" || !token.access_token) {
        throw new Rejected(503, "verification_unavailable");
      }
      const verified = await call(
        `${PAYPAL}/v1/notifications/verify-webhook-signature`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            auth_algo: headers["paypal-auth-algo"],
            cert_url: headers["paypal-cert-url"],
            transmission_id: headers["paypal-transmission-id"],
            transmission_sig: headers["paypal-transmission-sig"],
            transmission_time: headers["paypal-transmission-time"],
            webhook_id: webhookId,
            webhook_event: event,
          }),
        },
      );
      if (!verified.ok) throw new Rejected(503, "verification_unavailable");
      if ((await verified.json()).verification_status !== "SUCCESS") {
        throw new Rejected(400, "signature_rejected");
      }
      // Acknowledge only after a durable commit; provider retries are idempotent.
      const stored = await call(
        `${supabase.replace(/\/$/, "")}/rest/v1/rpc/sentinel_enqueue_webhook`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${serviceKey}`,
            apikey: serviceKey,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            p_event_id: event.id,
            p_event_type: event.event_type,
            p_raw_body: raw,
            p_headers: headers,
          }),
        },
      );
      if (stored.status === 409) throw new Rejected(409, "event_body_conflict");
      if (!stored.ok) throw new Rejected(503, "storage_unavailable");
      return response(200, {
        received: true,
        duplicate: (await stored.json()) === false,
      });
    } catch (error) {
      if (error instanceof Rejected) {
        return response(error.status, { error: error.code });
      }
      // Never log request bodies, OAuth responses, keys or provider error messages.
      return response(503, { error: "webhook_unavailable" });
    }
  };
}
