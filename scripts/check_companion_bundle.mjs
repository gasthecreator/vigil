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
  const content = fs.readFileSync(absolute);
  return {
    path: relative,
    raw_bytes: content.length,
    gzip_bytes: gzipSync(content, { level: 9 }).length,
    sha256: crypto.createHash("sha256").update(content).digest("hex"),
  };
});

const measuredBytes = assets.reduce((sum, asset) => sum + asset.gzip_bytes, 0);
const reportedBytes = seedFail ? Math.max(measuredBytes, budgetBytes) + 1 : measuredBytes;
const report = {
  route: "/companion",
  data_status: "Measured from the Next.js production app build; JavaScript chunks only.",
  command: "npm run web:build && node scripts/check_companion_bundle.mjs",
  machine: `${os.platform()}-${os.arch()} ${os.release()}`,
  budget_gzip_bytes: budgetBytes,
  measured_gzip_bytes: measuredBytes,
  reported_gzip_bytes: reportedBytes,
  seed_fail: seedFail,
  asset_count: assets.length,
  assets,
};

if (!seedFail) {
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
}
console.log(JSON.stringify(report, null, 2));

if (reportedBytes > budgetBytes) {
  console.error(`Companion JS gzip budget exceeded: ${reportedBytes} > ${budgetBytes} bytes.`);
  process.exit(1);
}
