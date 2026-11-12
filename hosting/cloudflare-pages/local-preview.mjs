// Local test harness for this _headers subset; never a Cloudflare emulator or deployment server.
import { createServer as https } from "node:https";
import { createServer as http } from "node:http";
import { readFileSync, statSync } from "node:fs";
import { resolve, extname, sep } from "node:path";
import { createHash } from "node:crypto";
import { brotliCompressSync, gzipSync, constants } from "node:zlib";
const [directory, cert, key, tlsPort = "9448", httpPort = "9447"] =
  process.argv.slice(2);
if (!directory || !cert || !key)
  throw Error(
    "Usage: local-preview.mjs PUBLISH CERT KEY [HTTPS_PORT HTTP_PORT]",
  );
const root = resolve(directory),
  rules = [];
let rule;
for (const line of readFileSync(resolve(root, "_headers"), "utf8").split(
  "\n",
)) {
  if (!line.trim() || line.startsWith("#")) continue;
  if (!line.startsWith(" ")) {
    const expression = line
      .replace(/[.+?^${}()|[\]\\]/g, "\\$&")
      .replace("*", ".*");
    rule = { path: new RegExp(`^${expression}$`), headers: {} };
    rules.push(rule);
  } else {
    const index = line.indexOf(":");
    if (!rule || index < 0) throw Error("Invalid header syntax");
    rule.headers[line.slice(0, index).trim().toLowerCase()] = line
      .slice(index + 1)
      .trim();
  }
}
const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};
const cache = new Map();
https({ cert: readFileSync(cert), key: readFileSync(key) }, (req, res) => {
  if (!["GET", "HEAD"].includes(req.method)) {
    res.writeHead(405, { Allow: "GET, HEAD" });
    res.end();
    return;
  }
  let pathname;
  try {
    pathname = decodeURIComponent(
      new URL(req.url, "https://localhost").pathname,
    );
  } catch {
    res.writeHead(400);
    res.end();
    return;
  }
  let file = resolve(root, `.${pathname === "/" ? "/index.html" : pathname}`),
    status = 200;
  if (!file.startsWith(root + sep) || pathname === "/_headers") {
    file = resolve(root, "404.html");
    status = 404;
  }
  try {
    if (!statSync(file).isFile()) throw Error("not a file");
  } catch {
    file = resolve(root, "404.html");
    status = 404;
  }
  const headers = {
    "content-type": types[extname(file)] ?? "application/octet-stream",
    "cache-control": "public, max-age=0, must-revalidate",
    vary: "Accept-Encoding",
  };
  const custom = {};
  for (const r of rules)
    if (r.path.test(pathname))
      for (const [k, v] of Object.entries(r.headers))
        custom[k] = custom[k] ? `${custom[k]}, ${v}` : v;
  Object.assign(headers, custom);
  const accept = req.headers["accept-encoding"] ?? "";
  const encoding = /\bbr\b/.test(accept)
    ? "br"
    : /\bgzip\b/.test(accept)
      ? "gzip"
      : "identity";
  const cacheKey = `${file}:${encoding}`,
    modified = statSync(file).mtimeMs;
  let hit = cache.get(cacheKey);
  if (!hit || hit.modified !== modified) {
    const raw = readFileSync(file),
      compressible =
        /text\/|javascript|json|svg/.test(headers["content-type"]) &&
        raw.length > 50;
    const used = compressible ? encoding : "identity";
    const body =
      used === "br"
        ? brotliCompressSync(raw, {
            params: { [constants.BROTLI_PARAM_QUALITY]: 5 },
          })
        : used === "gzip"
          ? gzipSync(raw)
          : raw;
    hit = {
      modified,
      body,
      used,
      etag: `"${createHash("sha256").update(body).digest("hex")}"`,
    };
    cache.set(cacheKey, hit);
  }
  headers.etag = hit.etag;
  if (hit.used !== "identity") headers["content-encoding"] = hit.used;
  if (status === 200 && req.headers["if-none-match"] === hit.etag) {
    res.writeHead(304, headers);
    res.end();
    return;
  }
  headers["content-length"] = hit.body.length;
  res.writeHead(status, headers);
  res.end(req.method === "HEAD" ? undefined : hit.body);
}).listen(Number(tlsPort), "127.0.0.1", () =>
  console.log(`LOCAL MODEL ONLY: https://127.0.0.1:${tlsPort}`),
);
http((req, res) => {
  res.writeHead(308, { location: `https://127.0.0.1:${tlsPort}${req.url}` });
  res.end();
}).listen(Number(httpPort), "127.0.0.1");
