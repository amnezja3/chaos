const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
const start = source.indexOf('function isSaneTerritoryPolygon(');
const end = source.indexOf('function normalizeMapLatLngPair(', start);
const context = vm.createContext({});
vm.runInContext(source.slice(start, end), context);
const sane = context.isSaneTerritoryPolygon;
// Synthetic rectangle with the observed production bounds, not the real ring.
const main = [[51.9610687,20.1131042],[51.9610687,22.2832641],
              [52.6441913,22.2832641],[52.6441913,20.1131042]];
assert(sane(main), 'main disappears after growing beyond two degrees');
assert(sane([[50,20],[53,20],[53,24]]), 'latitude growth must not add another display cap');
assert(sane([[52,20],[52.001,20],[52,20.001]]));
for (const ring of [[], [[0,0],[1,1]], [[0,0],[0,0],[1,1]],
    [[0,0],[NaN,1],[1,2]], [[0,0],[1,Infinity],[1,2]],
    [[0,0],[91,1],[1,2]], [[0,0],[1,181],[1,2]],
    [null,[1,1],[1,2]], [['',0],[1,1],[1,2]]]) {
    assert.strictEqual(sane(ring), false, 'invalid coordinates/ring must be rejected');
}
console.log('territory display geometry: PASS');
