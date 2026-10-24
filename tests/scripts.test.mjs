// Every script of the website has its own tests. Node measures the coverage only of
// the files that a test loads, so a script without tests would leave the 100 % of
// scripts/check-project.sh unharmed; this test names it instead. The tests of
// docs/javascripts/<name>.js and of overrides/partials/<name>.js are
// tests/<name>.test.mjs, and they read the script by its path.
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";

const ROOT = new URL("../", import.meta.url);
const FOLDERS = ["docs/javascripts/", "overrides/partials/"];

// The scripts of folder, as paths from the root of the repository.
const scripts = (folder) =>
  readdirSync(new URL(folder, ROOT))
    .filter((name) => name.endsWith(".js"))
    .map((name) => `${folder}${name}`);

test("every script of the website has tests that read it", () => {
  const all = FOLDERS.flatMap(scripts);
  assert.ok(all.length > 0, "no scripts found in docs/javascripts/ or overrides/partials/");
  const untested = all.filter((path) => {
    const stem = path.slice(path.lastIndexOf("/") + 1, -".js".length);
    const tests = new URL(`tests/${stem}.test.mjs`, ROOT);
    return !existsSync(tests) || !readFileSync(tests, "utf8").includes(path.slice(path.indexOf("/") + 1));
  });
  assert.deepEqual(untested, [], "write tests/<name>.test.mjs for each, which reads the script");
});
