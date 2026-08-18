"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");

function extractFunction(name, nextName) {
    const start = source.indexOf(`function ${name}`);
    const end = source.indexOf(`function ${nextName}`, start);
    assert(start >= 0 && end > start, `Cannot extract ${name}`);
    return source.slice(start, end);
}

const sandbox = {Set, Array};
vm.createContext(sandbox);
vm.runInContext(
    `${extractFunction("intersectCreatorOptions", "collectCreatorTargetFilters")}`
    + `\nresult = intersectCreatorOptions;`,
    sandbox
);

const intersect = sandbox.result;
assert.deepStrictEqual(
    Array.from(intersect(["scan_ports", "trace"], [], false)),
    ["scan_ports", "trace"]
);
assert.deepStrictEqual(
    Array.from(intersect(["scan_ports", "trace"], [], true)),
    [],
    "An active constraint with an empty intersection must not reopen the family pool"
);
assert.deepStrictEqual(
    Array.from(intersect(["scan_ports", "trace"], ["trace"], true)),
    ["trace"]
);

for (const interfaceName of ["progressbar_random", "terminal", "window", "button_choices"]) {
    assert(
        source.includes(`appendCreatorMeta(form, keys, '${interfaceName}')`),
        `${interfaceName} must use the shared creator contract`
    );
}

assert(source.includes('role="tab"'));
assert(source.includes("event.key === 'ArrowRight'"));
assert(source.includes("panel.setAttribute('aria-hidden'"));
assert(source.includes("field.setAttribute('aria-invalid', 'true')"));
assert(source.includes('["Kolizje",'));

console.log("Creator UX contract tests passed.");
