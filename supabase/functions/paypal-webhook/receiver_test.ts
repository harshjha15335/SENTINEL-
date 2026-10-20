import { createHandler } from "./receiver.ts";

function assert(value: unknown, message = "Assertion failed"): asserts value {
  if (!value) throw new Error(message);
}
const payload = JSON.stringify({
  id: "WH-TEST-1",
  event_type: "PAYMENT.CAPTURE.COMPLETED",
  resource: { id: "CAPTURE-1" },
});
const signed = {
  "paypal-transmission-id": "transmission-1",
  "paypal-transmission-time": "2026-10-20T12:00:00Z",
  "paypal-cert-url":
    "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1",
  "paypal-auth-algo": "SHA256withRSA",
  "paypal-transmission-sig": "TEST-SCRIPTED-SIGNATURE",
};
function setup(
  options: {
    verification?: string;
    storage?: number;
    duplicate?: boolean;
    configured?: boolean;
  } = {},
) {
  const calls: string[] = [];
  const env: Record<string, string> = {
    SENTINEL_PAYPAL_CLIENT_ID: "test-client",
    SENTINEL_PAYPAL_CLIENT_SECRET: "test-secret",
    SENTINEL_PAYPAL_WEBHOOK_ID: "test-webhook",
    SUPABASE_URL: "https://example.supabase.co",
    SUPABASE_SERVICE_ROLE_KEY: "test-service-key",
  };
  const handler = createHandler({
    env: (name) => options.configured === false ? undefined : env[name],
    fetch: async (input, init) => {
      const url = String(input);
      calls.push(url);
      assert(init?.redirect === "error");
      assert(init?.signal instanceof AbortSignal);
      if (url.endsWith("/oauth2/token")) {
        return Response.json({ access_token: "test-token" });
      }
      if (url.endsWith("/verify-webhook-signature")) {
        const sent = await new Response(String(init?.body)).json();
        assert(sent.webhook_id === "test-webhook");
        assert(sent.webhook_event.id === "WH-TEST-1");
        return Response.json({
          verification_status: options.verification ?? "SUCCESS",
        });
      }
      assert(url.endsWith("/rpc/sentinel_enqueue_webhook"));
      const sent = JSON.parse(String(init?.body));
      assert(
        sent.p_raw_body === payload,
        "Original signed bytes must survive storage",
      );
      assert(
        sent.p_headers["paypal-transmission-sig"] ===
          signed["paypal-transmission-sig"],
      );
      return Response.json(!options.duplicate, {
        status: options.storage ?? 200,
      });
    },
  });
  return { handler, calls };
}
function request(body = payload, headers = signed) {
  return new Request(
    "https://example.supabase.co/functions/v1/paypal-webhook",
    { method: "POST", body, headers },
  );
}

Deno.test("verified sandbox event is acknowledged only after storage", async () => {
  const { handler, calls } = setup();
  const response = await handler(request());
  assert(response.status === 200);
  assert((await response.json()).duplicate === false);
  assert(calls.length === 3 && calls[2].includes("enqueue"));
});
Deno.test("duplicate receipt is acknowledged without pretending to process a payment", async () => {
  const { handler } = setup({ duplicate: true });
  const result = await handler(request());
  assert(result.status === 200 && (await result.json()).duplicate === true);
});
Deno.test("verification failure never reaches storage", async () => {
  const { handler, calls } = setup({ verification: "FAILURE" });
  assert((await handler(request())).status === 400);
  assert(calls.length === 2);
});
Deno.test("database failure returns retryable failure, not receipt", async () => {
  const { handler } = setup({ storage: 503 });
  assert((await handler(request())).status === 503);
});
Deno.test("same event id with changed body returns conflict", async () => {
  const { handler } = setup({ storage: 409 });
  assert((await handler(request())).status === 409);
});
Deno.test("unsigned events fail before provider or storage calls", async () => {
  const { handler, calls } = setup();
  assert((await handler(request(payload, {} as typeof signed))).status === 400);
  assert(calls.length === 0);
});
Deno.test("foreign certificate host, credentials, query and port are rejected", async () => {
  for (
    const url of [
      "https://attacker.example/cert",
      "https://api.paypal.com:8443/v1/notifications/certs/1",
      "https://a:b@api.paypal.com/v1/notifications/certs/1",
      "https://api.paypal.com/v1/notifications/certs/1?x=1",
    ]
  ) {
    const { handler, calls } = setup();
    assert(
      (await handler(request(payload, { ...signed, "paypal-cert-url": url })))
        .status === 400,
    );
    assert(calls.length === 0);
  }
});
Deno.test("streamed body limit applies without content-length", async () => {
  const { handler, calls } = setup();
  assert((await handler(request("x".repeat(262145)))).status === 413);
  assert(calls.length === 0);
});
Deno.test("malformed and non-object JSON are rejected", async () => {
  for (const body of ["{", "null", "[]", "{}"]) {
    const { handler, calls } = setup();
    assert((await handler(request(body))).status === 400);
    assert(calls.length === 0);
  }
});
Deno.test("missing configuration fails closed", async () => {
  const { handler, calls } = setup({ configured: false });
  assert((await handler(request())).status === 503);
  assert(calls.length === 0);
});
Deno.test("provider network exception is retryable and does not leak secrets", async () => {
  const handler = createHandler({
    env: () => "configured",
    fetch: () => {
      throw new Error("secret-value");
    },
  });
  const result = await handler(request());
  assert(result.status === 503);
  assert(!(await result.text()).includes("secret-value"));
});
