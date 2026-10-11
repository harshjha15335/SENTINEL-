// Serves a directory the way GitHub Pages serves a project site, for testing the static demo:
// files as-is, and anything missing gets <root>/<repo>/404.html with status 404.
// Usage: node scripts/pages-preview.mjs <root> <repo> [port]
import { readFile, stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";

const [root, repo, port = "4173"] = process.argv.slice(2);
if (!root || !repo) throw new Error("usage: pages-preview.mjs <root> <repo> [port]");

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

createServer(async (req, res) => {
  const path = normalize(decodeURIComponent(new URL(req.url ?? "/", "http://localhost").pathname));
  try {
    let file = join(root, path);
    if ((await stat(file)).isDirectory()) file = join(file, "index.html");
    const body = await readFile(file);
    res.writeHead(200, { "content-type": TYPES[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404, { "content-type": TYPES[".html"] });
    res.end(await readFile(join(root, repo, "404.html")));
  }
}).listen(Number(port), "127.0.0.1", () => console.log(`pages preview on http://127.0.0.1:${port}/${repo}/`));
