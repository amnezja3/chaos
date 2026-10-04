const assert = require('assert');
const fs = require('fs');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
const start = source.indexOf('const targetSourceType =', source.indexOf('function showHackingMenuForMarker('));
const end = source.indexOf('// Nagłówek', start);
const actions = new Function('menuTarget', source.slice(start, end) + 'return actions.map(a => a.action);');
for (const source_type of ['car_wash', 'parking', 'bicycle_parking']) {
    assert(!actions({source_type, name: 'Auto serwis'}).includes('car_hack'), source_type);
}
assert(actions({source_type: 'vehicle', name: 'Auto: Tesla', generated: true}).includes('car_hack'));
assert(actions({source_type: 'parking', name: 'Auto: Tesla', generated: true}).includes('car_hack'));
assert(actions({source_type: 'camera', name: 'Kamera bankomatu'}).includes('camera_shutdown'));
assert(actions({source_type: 'atm', name: 'Bankomat'}).includes('atm_logs'));
assert(actions({source_type: 'person', name: 'Gość restauracji'}).includes('trace_device'));
console.log('scan marker actions: OK');
