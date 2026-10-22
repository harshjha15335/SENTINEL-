// Local fixture harness only. Never deploy or use as a PayPal verifier.
import { createHandler } from "../supabase/functions/paypal-webhook/receiver.ts";

if (Deno.env.get("SENTINEL_FIXTURE_RECEIVER") !== "true") {
  throw new Error("Explicit local fixture receiver flag required");
}
const project = Deno.env.get("SENTINEL_SUPABASE_URL");
const key = Deno.env.get("SENTINEL_SUPABASE_SERVICE_ROLE_KEY");
if (!project || !key) {
  throw new Error("Private fixture RPC configuration missing");
}
const env: Record<string, string> = {
  SENTINEL_PAYPAL_CLIENT_ID: "fixture-client",
  SENTINEL_PAYPAL_CLIENT_SECRET: "fixture-only-secret",
  SENTINEL_PAYPAL_WEBHOOK_ID: "FIXTURE-WEBHOOK",
  SUPABASE_URL: project,
  SUPABASE_SERVICE_ROLE_KEY: key,
};
const handler = createHandler({
  env: (name) => env[name],
  fetch: (url, init) => {
    const endpoint = String(url);
    if (endpoint === "https://api-m.sandbox.paypal.com/v1/oauth2/token") {
      return Promise.resolve(Response.json({ access_token: "fixture-token" }));
    }
    if (
      endpoint ===
        "https://api-m.sandbox.paypal.com/v1/notifications/verify-webhook-signature"
    ) {
      return Promise.resolve(Response.json({ verification_status: "SUCCESS" }));
    }
    if (endpoint === `${project}/rest/v1/rpc/sentinel_enqueue_webhook`) {
      return fetch(`${project}/rest/v1/rpc/sentinel_enqueue_fixture`, init);
    }
    throw new Error("Unexpected fixture network destination");
  },
});
Deno.serve({ hostname: "127.0.0.1", port: 8043 }, handler);
