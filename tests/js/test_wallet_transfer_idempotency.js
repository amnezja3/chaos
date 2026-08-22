"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const start = source.indexOf("function walletTransferScopeDigest");
const end = source.indexOf("async function submitWalletTransfer", start);
assert(start >= 0 && end > start, "Cannot extract wallet transfer idempotency helpers");

const records = new Map();
let sessionState = {
    username: "alice",
    generation: "generation-a",
    query_token: "query-a",
};
let uuidCounter = 0;
const sandbox = {
    Date,
    JSON,
    Math,
    encodeURIComponent,
    window: {
        ChaosSessionGeneration: {
            getState: () => ({ ...sessionState }),
        },
        crypto: {
            randomUUID: () => `uuid-${++uuidCounter}`,
        },
        sessionStorage: {
            getItem: (key) => records.has(key) ? records.get(key) : null,
            setItem: (key, value) => records.set(key, String(value)),
            removeItem: (key) => records.delete(key),
        },
    },
};
vm.createContext(sandbox);
vm.runInContext(
    `let toolbarProfile = null;\n${source.slice(start, end)}\n`
    + "api = { acquireWalletTransferAction, clearWalletTransferActionKey };",
    sandbox,
);

const firstContainer = { dataset: {} };
const semanticTransfer = { to: "bob", amount: "25", note: "test" };
const first = sandbox.api.acquireWalletTransferAction(semanticTransfer, firstContainer);
assert.strictEqual(first.key, "wallet-transfer:uuid-1");

// A full document reload loses dataset state, but sessionStorage is retained.
const reloadedContainer = { dataset: {} };
const afterReload = sandbox.api.acquireWalletTransferAction(semanticTransfer, reloadedContainer);
assert.strictEqual(afterReload.key, first.key);
assert.strictEqual(uuidCounter, 1);

// Editing request semantics represents a new operation and must mint a key.
const changed = sandbox.api.acquireWalletTransferAction(
    { ...semanticTransfer, amount: "26" },
    reloadedContainer,
);
assert.strictEqual(changed.key, "wallet-transfer:uuid-2");
assert.notStrictEqual(changed.key, first.key);

// The same payload in another authenticated session must never share a key.
sessionState = { username: "bob", generation: "generation-b", query_token: "query-b" };
const otherSession = sandbox.api.acquireWalletTransferAction(semanticTransfer, { dataset: {} });
assert.strictEqual(otherSession.key, "wallet-transfer:uuid-3");
assert.notStrictEqual(otherSession.storageKey, first.storageKey);

sandbox.api.clearWalletTransferActionKey(otherSession);
assert.strictEqual(records.has(otherSession.storageKey), false);
assert(source.includes("clearWalletTransferActionKey();"));
assert(source.includes("clearWalletTransferActionKey(transferAction, container);"));

console.log("wallet transfer idempotency JS tests: ok");
