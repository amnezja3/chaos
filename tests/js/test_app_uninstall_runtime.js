"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const start = source.indexOf("async function rebuildDesktopAppsFromProfile");
const end = source.indexOf("function updateCybernerDeltaViews", start);
assert.ok(start >= 0 && end > start, "apps projection helpers must exist");

const sandbox = {
    toolbarProfile: {
        username: "alice",
        apps: [{ id: "removed-app", name: "Removed App" }],
        files: { tools: ["Removed App.sh"], projects: ["keep.glab"] }
    },
    desktopSettings: {},
    fileManagerInstances: new Map(),
    document: { getElementById() { return null; } },
    window: {},
    async buildIconsFromJsonWithCommand(apps) {
        return apps.map(app => ({ id: app.id, label: app.name }));
    },
    getSystemDesktopApps() {
        return [{ id: "terminal", label: "Terminal" }];
    },
    setToolbarProfile(profile) {
        sandbox.toolbarProfile = profile;
    },
    setToolbarLaunchers(apps) {
        sandbox.launchers = apps;
    },
    renderDesktopIcons(apps) {
        sandbox.desktopApps = apps;
    }
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);

(async () => {
    await sandbox.updateAppsView({
        apps: [],
        files: { tools: [] },
        reason: "uninstall_response"
    });

    assert.deepStrictEqual(
        Array.from(sandbox.launchers, item => item.id),
        ["terminal"],
        "uninstalled launcher must disappear from Start menu projection"
    );
    assert.deepStrictEqual(
        Array.from(sandbox.desktopApps, item => item.id),
        ["terminal"],
        "uninstalled launcher must disappear from desktop projection"
    );
    assert.deepStrictEqual(Array.from(sandbox.toolbarProfile.apps), []);
    assert.deepStrictEqual(Array.from(sandbox.toolbarProfile.files.tools), []);
    assert.strictEqual(sandbox.toolbarProfile.files.projects[0], "keep.glab");
    console.log("app uninstall runtime tests: OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
