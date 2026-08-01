import { lstatSync, readFileSync, realpathSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

if (process.env.CI || process.env.GITHUB_ACTIONS) {
  console.error(
    "Refusing to update accepted visual baselines in CI. Run this command locally for explicit review.",
  );
  process.exit(2);
}

const here = dirname(fileURLToPath(import.meta.url));
const repository = realpathSync(resolve(here, "../.."));
const baselineSegments = ["design", "frontend", "baselines"];
let baselineCursor = repository;
for (const segment of baselineSegments) {
  baselineCursor = resolve(baselineCursor, segment);
  const stat = lstatSync(baselineCursor);
  if (stat.isSymbolicLink() || !stat.isDirectory()) {
    throw new Error(`Visual baseline path segment must be a real directory: ${segment}`);
  }
}
const baselines = realpathSync(baselineCursor);
const baselinesRelative = relative(repository, baselines);
if (
  !baselinesRelative
  || isAbsolute(baselinesRelative)
  || baselinesRelative === ".."
  || baselinesRelative.startsWith(`..${sep}`)
) {
  throw new Error("Visual baselines must resolve inside the repository.");
}
const contract = JSON.parse(
  readFileSync(resolve(repository, "design/frontend/visual-contract.json"), "utf8"),
);
const renderer = contract.baseline_policy.canonical_renderer;

if (!renderer.container_image?.includes("@sha256:")) {
  throw new Error("The visual renderer must use a digest-pinned container image.");
}

const visualProjects = [
  "visual-small-mobile",
  "visual-mobile",
  "visual-phone-landscape",
  "visual-tablet-portrait",
  "visual-tablet-landscape",
  "visual-desktop",
  "visual-wide",
];
const testCommand = [
  "node node_modules/@playwright/test/cli.js test tests/frontend/visual-evidence.spec.js",
  ...visualProjects.map((project) => `--project=${project}`),
  "--update-snapshots=changed",
  "--workers=1",
].join(" ");
const containerCommand = [
  "set -euo pipefail",
  'cd /source && find . -mindepth 1 -maxdepth 1 ! -name .git ! -name node_modules ! -name .artifacts -print0 | tar --null -T - -cf - | tar -C /work -xf -',
  "rm -rf /work/design/frontend/baselines",
  "ln -s /baselines /work/design/frontend/baselines",
  'cd /work && mkdir -p "$HOME" "$npm_config_cache"',
  "npm ci --ignore-scripts",
  testCommand,
  "python3 tools/build_visual_baseline_manifest.py",
].join(" && ");

const dockerArgs = [
  "run",
  "--rm",
  "--init",
  "-e",
  "CI=1",
  "-e",
  "HOME=/tmp/concordloom-home",
  "-e",
  "npm_config_cache=/tmp/concordloom-npm-cache",
];

if (typeof process.getuid === "function" && typeof process.getgid === "function") {
  dockerArgs.push("--user", `${process.getuid()}:${process.getgid()}`);
}

dockerArgs.push(
  "--tmpfs",
  "/work:rw,exec,mode=1777",
  "--mount",
  `type=bind,src=${repository},dst=/source,readonly`,
  "--mount",
  `type=bind,src=${baselines},dst=/baselines`,
  "--workdir",
  "/work",
  renderer.container_image,
  "bash",
  "-lc",
  containerCommand,
);

const result = spawnSync("docker", dockerArgs, { stdio: "inherit" });
if (result.error) throw result.error;
process.exit(result.status ?? 1);
