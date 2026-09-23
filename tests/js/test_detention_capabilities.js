const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync('static/js/detention.js', 'utf8'), context);
const ui = context.window.DetentionUI;
for (const stage of [6, 7, 8, 9]) {
    ui.update({stage, app_access: stage === 9 ? 'webdragon_radio' : 'normal',
        cyberner_world: stage === 6 ? 'full' : stage === 7 ? 'read_only' : 'blocked',
        private_messages_remaining: 1});
    for (const id of ['browser','radio','ghost-radio','cyberner','email']) assert(ui.appAllowed(id));
    assert.equal(ui.appAllowed('terminal'), stage !== 9);
    assert.equal(ui.chatReason('world') === '', stage === 6);
    assert.equal(ui.chatReason('world', false) === '', stage < 8);
    for (const channel of ['direct','clan','friends','new-private-channel']) {
        assert.equal(ui.chatReason(channel), '');
        assert.equal(ui.chatReason(channel, false), '');
    }
    ui.update({...ui.state, private_messages_remaining: 0});
    for (const channel of ['direct','clan','friends']) {
        assert(ui.chatReason(channel));
        assert.equal(ui.chatReason(channel, false), '');
    }
}
ui.update(null);
assert(ui.appAllowed('terminal'));
assert.equal(ui.chatReason('world'), '');
console.log('detention capabilities: OK');
