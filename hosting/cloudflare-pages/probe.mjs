// Validate the local response model and compressibility; this does not test Cloudflare's edge.
import assert from "node:assert/strict";
import { request as httpsRequest } from "node:https";
import { request as httpRequest } from "node:http";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { brotliDecompressSync, gunzipSync } from "node:zlib";
const [
  release,
  output = "/tmp/sentinel-host-headers.json",
  origin = "https://127.0.0.1:9448",
] = process.argv.slice(2);
const address = new URL(origin);
if (address.hostname !== "127.0.0.1")
  throw Error("Local certificate exception is loopback only");
const manifest = JSON.parse(
  readFileSync(`${release}/HOST-MANIFEST.json`, "utf8"),
);
const request = (path, headers = {}, plain = false) =>
  new Promise((resolve, reject) => {
    const req = (plain ? httpRequest : httpsRequest)(
      {
        hostname: "127.0.0.1",
        port: plain ? Number(address.port) - 1 : Number(address.port),
        path,
        headers,
        rejectUnauthorized: false,
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () =>
          resolve({
            status: res.statusCode,
            headers: res.headers,
            body: Buffer.concat(chunks),
          }),
        );
      },
    );
    req.on("error", reject);
    req.end();
  });
const results = [];
const redirect = await request("/", {}, true);
assert.equal(redirect.status, 308);
assert.equal(redirect.headers.location, `${address.origin}/`);
for (const [name, file] of Object.entries(manifest.files)) {
  if (name === "_headers") continue;
  const path = name === "index.html" ? "/" : `/${name}`;
  for (const encoding of ["gzip", "br"]) {
    const response = await request(path, { "Accept-Encoding": encoding });
    assert.equal(response.status, 200, name);
    const h = response.headers;
    assert.equal(h["x-content-type-options"], "nosniff");
    assert.equal(h["x-frame-options"], "DENY");
    assert.equal(h["referrer-policy"], "no-referrer");
    assert.equal(h["strict-transport-security"], "max-age=86400");
    assert.ok(h["content-security-policy"].includes("script-src 'self';"));
    assert.ok(!h["content-security-policy"].includes("unsafe-eval"));
    const decoded =
      h["content-encoding"] === "br"
        ? brotliDecompressSync(response.body)
        : h["content-encoding"] === "gzip"
          ? gunzipSync(response.body)
          : response.body;
    assert.equal(
      createHash("sha256").update(decoded).digest("hex"),
      file.sha256,
      name,
    );
    const compressible =
      /\.json$|\.js$|\.css$|\.html$|\.svg$/.test(name) && file.bytes > 50;
    if (compressible) assert.equal(h["content-encoding"], encoding, name);
    if (name.startsWith("assets/"))
      assert.equal(h["cache-control"], "public, max-age=31536000, immutable");
    else if (name.endsWith(".html") || name.endsWith(".json"))
      assert.equal(h["cache-control"], "public, max-age=0, must-revalidate");
    if (name.endsWith(".json"))
      assert.match(h["content-type"], /^application\/json/);
    else if (name.endsWith(".js"))
      assert.match(h["content-type"], /javascript/);
    else if (name.endsWith(".css"))
      assert.match(h["content-type"], /^text\/css/);
    else if (name.endsWith(".woff2"))
      assert.equal(h["content-type"], "font/woff2");
    const conditional = await request(path, {
      "Accept-Encoding": encoding,
      "If-None-Match": h.etag,
    });
    assert.equal(conditional.status, 304, name);
    assert.equal(conditional.body.length, 0);
    results.push({
      file: name,
      encoding: h["content-encoding"] ?? "identity",
      rawBytes: file.bytes,
      wireBodyBytes: response.body.length,
      etag304: true,
      mime: h["content-type"],
      cache: h["cache-control"],
    });
  }
}
for (const path of [
  "/_headers",
  "/.env",
  "/SOURCE.bundle",
  "/private-review.zip",
  "/app/physical/unknown",
]) {
  const response = await request(path);
  assert.equal(response.status, 404, path);
  assert.ok(response.body.includes("Open the homepage"));
}
writeFileSync(
  output,
  JSON.stringify(
    {
      localModelOnly: true,
      httpRedirect: 308,
      filesChecked: results.length / 2,
      compressionAndCacheResults: results,
      privatePaths404: true,
    },
    null,
    2,
  ),
);
console.log(
  JSON.stringify({
    localModelOnly: true,
    filesChecked: results.length / 2,
    encodingChecks: results.length,
    privatePaths404: true,
  }),
);
