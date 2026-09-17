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
for (const file of ['ecosystem.web.config.js', 'ecosystem.territory-worker.config.js',
    'ecosystem.ollama-worker.config.js', 'ecosystem.narrative-publisher.config.js']) {
    const env = config(file).env;
    assert.equal(env.CHAOS_NARRATIVE_TTL_URGENT_SECONDS, '1800');
    assert.equal(env.CHAOS_NARRATIVE_TTL_NORMAL_SECONDS, '7200');
    assert.equal(env.CHAOS_NARRATIVE_TTL_EDITORIAL_SECONDS, '21600');
    assert(Number(env.CHAOS_NARRATIVE_PRIORITY_URGENT) > Number(env.CHAOS_NARRATIVE_PRIORITY_NORMAL));
    assert(Number(env.CHAOS_NARRATIVE_PRIORITY_NORMAL) > Number(env.CHAOS_NARRATIVE_PRIORITY_EDITORIAL));
}
console.log('Narrative ecosystems PASS: independent of stale shell flags and event filter');
