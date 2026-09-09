const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("templates/map_template.html", "utf8");
const start = source.indexOf("window.renderActiveOperationsPanel = function(operations, history)");
const end = source.indexOf("window.updateActiveOperationCountdowns = function", start);
assert.ok(start >= 0 && end > start, "current Operation Center renderer must exist");

const panel = {
    dataset: {},
    classList: { toggle() {} },
    querySelector() { return null; },
    _html: "",
    set innerHTML(value) { this._html = value; },
    get innerHTML() { return this._html; }
};
const windowObject = {
    operationCenterTab: "active",
    operationCenterState: "preview",
    latestOperationHistory: [],
    operationCancelInFlight: new Map(),
    operationDomSignature() { return "stable-signature"; },
    operationMarkerMeta() { return {name: "Skanowanie", icon: "S"}; },
    operationLabel(operation) { return operation.target_name; },
    operationRiskLabel() { return "none"; },
    escapeMapText(value) { return String(value || ""); },
    formatOperationDate(value) { return String(value || "-"); },
    formatRemainingTime() { return "10:00"; },
    updateActiveOperationCountdowns() {}
};
const sandbox = {
    Map, Set, JSON, Array, Boolean,
    window: windowObject,
    document: {
        getElementById(id) { return id === "active-operations-panel" ? panel : null; },
        createElement() { throw new Error("initial render must not enter incremental replacement"); }
    },
    operationClientId(operation) { return operation.operation_id; },
    operationHistorySignature() { return "history"; }
};
sandbox.window.window = sandbox.window;
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);

assert.doesNotThrow(() => sandbox.window.renderActiveOperationsPanel([{
    operation_id: "op-scan-vulnerability-1",
    target_name: "Public vulnerability",
    status: "running",
    started_at: "2026-09-09T10:00:00Z",
    expires_at: "2026-09-09T11:00:00Z",
    risk_level: "none"
}], []));
assert.match(panel.innerHTML, /op-scan-vulnerability-1/);
assert.match(panel.innerHTML, /Public vulnerability/);
assert.strictEqual(panel.dataset.viewKey, "active:preview");
console.log("operation center renderer tests: OK");
