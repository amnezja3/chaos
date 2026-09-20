const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const start = source.indexOf('function applyInventoryRemoval(');
const end = source.indexOf('function refreshOpenFileManagersForApps(', start);
const ctx = {};
vm.createContext(ctx);
vm.runInContext(source.slice(start, end), ctx);
const snapshot = {apps: [{id:'removed'}, {id:'kept'}], files:{tools:[
    {tool_id:'file-1',name:'Same.sh',app_id:'removed'},
    {tool_id:'file-2',name:'Same.sh',app_id:'kept'},
    'Legacy.sh', {name:'Unrelated.sh'}], documents:['note']}};
const payload = {removed_app_ids:['removed'],removed_tools:[
    {tool_id:'file-1',name:'Same.sh'},{tool_id:'old',name:'Legacy.sh'}]};
const result = ctx.applyInventoryRemoval(snapshot, payload);
assert.equal(result.apps.length, 1);
assert.equal(result.files.tools.length, 2);
assert.equal(result.files.tools[0].app_id, 'kept');
assert.equal(result.files.documents[0], 'note');
assert.equal(snapshot.files.tools.length, 4);
assert.equal(JSON.stringify(ctx.applyInventoryRemoval(result,payload)),JSON.stringify(result));
console.log('Consequence inventory delta: removals, same-name ownership, legacy files and replay PASS');
