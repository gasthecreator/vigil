import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const webDir = path.join(root, "apps/web");
const manifestPath = path.join(webDir, ".next/app-build-manifest.json");
const reportPath = path.join(root, "reports/quality/COMPANION_BUNDLE.json");
const budgetBytes = 180 * 1024;
const seedFail = process.argv.includes("--seed-fail");

function measureAsset(assetPath, content) {
  return {
    path: assetPath,
    raw_bytes: content.length,
    gzip_bytes: gzipSync(content, { level: 9 }).length,
    sha256: crypto.createHash("sha256").update(content).digest("hex"),
  };
}

function seededOversizedAsset() {
  // Deterministic, poorly compressible bytes exercise the same measurement and budget check as real chunks.
  const content = Buffer.alloc(budgetBytes + 16 * 1024);
  for (let offset = 0, counter = 0; offset < content.length; counter += 1) {
    const block = crypto.createHash("sha256").update(`companion-budget-seed-${counter}`).digest();
    block.copy(content, offset, 0, Math.min(block.length, content.length - offset));
    offset += block.length;
  }
  return measureAsset("[seeded oversized fixture]", content);
}

if (!fs.existsSync(manifestPath)) {
  console.error("Missing Next app build manifest. Build apps/web before measuring the companion route.");
  process.exit(2);
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const chunks = manifest.pages?.["/companion/page"];
if (!Array.isArray(chunks) || chunks.length === 0) {
  console.error("Next app manifest has no /companion/page entry.");
  process.exit(2);
}

const uniqueChunks = [...new Set(chunks.filter((item) => item.endsWith(".js")))];
const assets = uniqueChunks.map((relative) => {
  const absolute = path.join(webDir, ".next", relative);
  if (!fs.existsSync(absolute)) throw new Error(`Missing built companion chunk: ${relative}`);
  return measureAsset(relative, fs.readFileSync(absolute));
});

if (seedFail) assets.push(seededOversizedAsset());
const measuredBytes = assets.reduce((sum, asset) => sum + asset.gzip_bytes, 0);
const report = {
  route: "/companion",
  data_status: "Measured from the Next.js production app build; JavaScript chunks only.",
  command: "npm run web:build && node scripts/check_companion_bundle.mjs",
  machine: `${os.platform()}-${os.arch()} ${os.release()}`,
  budget_gzip_bytes: budgetBytes,
  measured_gzip_bytes: measuredBytes,
  seed_fail: seedFail,
  asset_count: assets.length,
  assets,
};

if (!seedFail) {
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
}
console.log(JSON.stringify(report, null, 2));

if (measuredBytes > budgetBytes) {
  console.error(`Companion JS gzip budget exceeded: ${measuredBytes} > ${budgetBytes} bytes.`);
  process.exit(1);
}
