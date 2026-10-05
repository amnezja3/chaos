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
assert(actions({source_type: 'restaurant', name: 'Gość restauracji', generated: true}).includes('trace_device'));
for (const target of [
    {source_type: 'person', name: 'Klient', generated: true},
    {source_type: 'person', name: 'Osoba przy bankomacie', generated: true},
    {source_type: 'shop_clothes', name: 'Klient', generated: true}
]) assert.deepStrictEqual(actions(target), ['trace_device', 'mic_sniff']);
for (const source_type of ['shop', 'shop_clothes', 'bank', 'car_wash', 'parking', 'bicycle_parking', 'parcel_locker']) {
    assert.deepStrictEqual(actions({source_type, name: 'Test'}), ['scan_ports', 'exploit', 'sniff', 'trace']);
}
for (const source_type of ['restaurant', 'bar', 'cafe', 'fast_food']) {
    assert.deepStrictEqual(actions({source_type, name: 'Test'}), ['scan_hotspots', 'audio_hack']);
}
console.log('scan marker actions: OK');
assert.deepStrictEqual(actions({source_type: 'phone', name: 'Telefon'}), ['trace_device', 'mic_sniff']);
for (const name of ['Kamera sklep', 'Klient cafe', 'Osoba bar']) {
    assert.deepStrictEqual(actions({source_type: 'shop', name}), ['scan_ports', 'exploit', 'sniff', 'trace']);
}
assert.deepStrictEqual(actions({source_type: ' Camera ', name: 'Test'}), ['camera_stream', 'camera_shutdown']);
assert.deepStrictEqual(actions({source_type: 'shop_camera', name: 'Test'}), ['scan_ports', 'exploit', 'sniff', 'trace']);
