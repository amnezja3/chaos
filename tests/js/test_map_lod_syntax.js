"use strict";

const assert = require("assert");
const fs = require("fs");

const source = fs.readFileSync("templates/map_template.html", "utf8");
const marker = "<script>\n        const map =";
const start = source.indexOf(marker);
assert.ok(start >= 0, "main map runtime script must exist");
const scriptStart = start + "<script>\n".length;
const end = source.indexOf("</script>", scriptStart);
assert.ok(end > scriptStart, "main map runtime script must be closed");

const runtime = source.slice(scriptStart, end);
assert.doesNotThrow(() => new Function(runtime), "main map runtime must remain valid JavaScript");
assert.ok(runtime.includes("window.applyMapLevelOfDetail"));
assert.ok(runtime.includes("window.chaosMapPerformanceProbe"));

console.log("map LOD syntax contract: OK");
