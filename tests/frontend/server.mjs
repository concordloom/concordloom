import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const ROOT = resolve(HERE, "../..");
const SITE = join(ROOT, "site");
const WORKSHOP = join(ROOT, "frontend-workshop");
const HOST = "127.0.0.1";
const PORT = Number.parseInt(process.env.PORT || "4173", 10);

const MIME = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".webp", "image/webp"],
]);

function resolveRequest(pathname) {
  const workshop = pathname === "/workshop" || pathname.startsWith("/workshop/");
  const base = workshop ? WORKSHOP : SITE;
  let relative = workshop ? pathname.replace(/^\/workshop\/?/, "") : pathname.slice(1);
  if (!relative || relative.endsWith("/")) relative += "index.html";
  const target = resolve(base, normalize(relative));
  if (target !== base && !target.startsWith(`${base}${sep}`)) return null;
  return target;
}

const server = createServer(async (request, response) => {
  if (!["GET", "HEAD"].includes(request.method || "")) {
    response.writeHead(405, { Allow: "GET, HEAD" });
    response.end();
    return;
  }

  let pathname;
  try {
    pathname = decodeURIComponent(new URL(request.url || "/", `http://${HOST}`).pathname);
  } catch {
    response.writeHead(400);
    response.end("Bad request");
    return;
  }

  const target = resolveRequest(pathname);
  if (!target || target.split(sep).some((part) => part.startsWith("."))) {
    response.writeHead(404);
    response.end("Not found");
    return;
  }

  try {
    const metadata = await stat(target);
    if (!metadata.isFile()) throw new Error("not a file");
    response.writeHead(200, {
      "Cache-Control": "no-store",
      "Content-Length": metadata.size,
      "Content-Type": MIME.get(extname(target)) || "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
    });
    if (request.method === "HEAD") response.end();
    else createReadStream(target).pipe(response);
  } catch {
    response.writeHead(404);
    response.end("Not found");
  }
});

server.listen(PORT, HOST, () => {
  process.stdout.write(`FRONTEND_SERVER_READY http://${HOST}:${PORT}\n`);
});

function stop() {
  server.close(() => process.exit(0));
}

process.on("SIGINT", stop);
process.on("SIGTERM", stop);
