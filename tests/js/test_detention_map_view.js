const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
const code = source.slice(source.indexOf('        // 143.5a: a prison viewport'), source.indexOf('        const MANUAL_MAP_VIEW_STORAGE_KEY'));
let shade, zoom = 14, min = 10, max = 18, center = {lat: 0, lng: 0};
const listeners = {};
const map = {getZoom: () => zoom, getMinZoom: () => min, getMaxZoom: () => max,
    setMinZoom: value => {min=value;}, setMaxZoom: value => {max=value;}, getCenter: () => center,
    setView: (point, z) => {center={lat: point[0], lng: point[1]}; zoom=z; listeners.moveend();},
    getContainer: () => ({appendChild: el => {shade=el;}, querySelector: () => shade}),
    on: (events, cb) => events.split(' ').forEach(event => {listeners[event]=cb;})};
for (const key of ['dragging','scrollWheelZoom','doubleClickZoom','touchZoom','boxZoom','keyboard']) {
    let enabled = key !== 'keyboard';
    map[key] = {enabled: () => enabled, enable: () => {enabled=true;}, disable: () => {enabled=false;}};
}
map.zoomControl = {_map: map, remove() {this._map=null;}, addTo(m) {this._map=m;}};
const context={map, baseZoom:18, window:{setTimeout: () => {}, parent:{}}, document:{createElement: () => ({style:{},remove(){shade=null;}})}};
vm.runInNewContext(code, context);
const apply=context.window.applyDetentionView;
apply({prison_position:{lat:53,lng:-7}});
assert.equal(zoom,18); assert.equal(min,18); assert.equal(max,18);
assert.deepEqual(center,{lat:53,lng:-7}); assert(!map.dragging.enabled());
assert(shade.style.cssText.includes('rgba(0,0,0,.6)')); assert.equal(map.zoomControl._map,null);
center={lat:20,lng:20}; zoom=12; listeners.moveend();
assert.deepEqual(center,{lat:53,lng:-7}); assert.equal(zoom,18);
apply({prison_position:{lat:53,lng:-7}}); // repeated poll must not overwrite saved settings
apply(null);
assert.equal(min,10); assert.equal(max,18); assert(map.dragging.enabled());
assert(!map.keyboard.enabled()); assert.equal(shade,null); assert.equal(map.zoomControl._map,map);
center={lat:1,lng:2}; listeners.moveend(); assert.deepEqual(center,{lat:1,lng:2});
console.log('prison focus, zoom lock, dimming and restoration: OK');
