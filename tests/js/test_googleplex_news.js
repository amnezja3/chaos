"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/googleplex_news.js", "utf8");
const sandbox = {console};
vm.createContext(sandbox);
vm.runInContext(source, sandbox);

const ui = sandbox.GoogleplexNewsUI;
assert.ok(ui, "GoogleplexNewsUI must be exported");

const snapshot = ui.normalizeSnapshot({
    success: true,
    view: "home",
    schema_version: "v1",
    state_version: "state-1",
    entries: [{
        content: {news_id: "entry-1", title: "Title", summary: "Summary", category: "SYSTEM"},
        presentation: {
            weight: "hero", state: "verified", asset_family: "scene", asset_state: "neutral",
            asset_kind: "image", asset_path: "/static/images/googleplx/scene/world-neutral-01.webp"
        },
        action: {kind: "ACTIONABLE", action_type: "open_map", action_target: "world"}
    }],
    global_stats: [],
    protocol_status: {ollama_used: false, publication_enabled: false}
});
assert.ok(snapshot);
assert.strictEqual(snapshot.entries.length, 1);
assert.strictEqual(snapshot.entries[0].action.kind, "ACTIONABLE");
assert.strictEqual(snapshot.entries[0].presentation.asset_path, "/static/images/googleplx/scene/world-neutral-01.webp");

const unsafe = ui.normalizeSnapshot({
    success: true,
    view: "home",
    entries: [{
        content: {news_id: "unsafe", title: "Unsafe"},
        presentation: {weight: "giant", asset_family: "remote", asset_kind: "image", asset_path: "https://evil.invalid/a.svg"},
        action: {kind: "ACTIONABLE", action_type: "delete_everything", action_target: "*"}
    }]
});
assert.strictEqual(unsafe.entries[0].presentation.weight, "small");
assert.strictEqual(unsafe.entries[0].presentation.asset_family, "stamp");
assert.strictEqual(unsafe.entries[0].presentation.asset_path, "");
assert.strictEqual(unsafe.entries[0].action.kind, "STAMP_ONLY");
assert.strictEqual(unsafe.entries[0].action.action_type, "");

const terminalSource = fs.readFileSync("static/js/terminal.js", "utf8");
const newsCss = fs.readFileSync("static/css/googleplex_news.css", "utf8");
assert.ok(terminalSource.includes("loadGoogleplexHome().catch(() => {});"), "browser boot must load Home");
assert.ok(terminalSource.includes("if (!catalogLoaded)"), "catalog must be lazy");
assert.ok(source.includes("dataset.inFlight"), "action dispatch must be single-flight");
assert.ok(terminalSource.includes("browser-maximize-btn"), "WebDragons must expose a maximize control");
assert.ok(terminalSource.includes("is-window-maximized"), "maximize must use a reversible window state");
assert.ok(terminalSource.includes("restoreGeometry"), "restore must preserve the prior geometry");
assert.ok(terminalSource.includes("defaultBrowserHeight"), "initial browser geometry must adapt to viewport height");
assert.ok(!newsCss.includes("grid-auto-rows: 68px"), "windowed cards must not overflow undersized grid tracks");
assert.ok(newsCss.includes("grid-template-columns: minmax(0, 1fr) auto"), "brand and HC must own separate header columns");
assert.ok(newsCss.includes("filter: drop-shadow"), "the logo glow must follow the rendered wordmark bounds");

console.log("googleplex news tests: OK");
