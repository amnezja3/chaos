const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
function config(path) {
    const ctx = {module: {exports: {}}, process: {env: {
        CHAOS_OLLAMA_WORKER_ENABLED: 'false', CHAOS_NARRATIVE_PUBLISHER_ENABLED: 'false',
        CHAOS_OLLAMA_SOURCE_EVENT_ID: 'old-signal'
    }}};
    vm.runInNewContext(fs.readFileSync(path, 'utf8'), ctx);
    return ctx.module.exports.apps[0];
}
const ollama = config('ecosystem.ollama-worker.config.js');
const publisher = config('ecosystem.narrative-publisher.config.js');
assert.equal(ollama.env.CHAOS_OLLAMA_WORKER_ENABLED, 'true');
assert.equal(ollama.env.CHAOS_OLLAMA_SOURCE_EVENT_ID, '');
assert.equal(publisher.env.CHAOS_NARRATIVE_PUBLISHER_ENABLED, 'true');
assert.equal(ollama.env.CHAOS_NARRATIVE_LEGACY_FILE_QUEUE_ENABLED, 'false');
assert.equal(publisher.env.CHAOS_NARRATIVE_LEGACY_FILE_QUEUE_ENABLED, 'false');
assert.equal(ollama.instances, 1);
assert.equal(publisher.instances, 1);
console.log('Narrative ecosystems PASS: independent of stale shell flags and event filter');
