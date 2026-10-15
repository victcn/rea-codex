import { fileURLToPath } from "node:url";
import { runMeasuredCommand } from "./workflow-metrics.mjs";

// Time the existing packager; it owns archive staging and validation.
await runMeasuredCommand([
  "bash",
  fileURLToPath(new URL("../skills/sites/scripts/package-site.sh", import.meta.url)),
  ...process.argv.slice(2),
]);
