const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
const window = {responseNpcDirections: ['up', 'up_right', 'right', 'down_right', 'down', 'down_left', 'left', 'up_left']};
const ctx = vm.createContext({window, Date});
for (const name of ['projectResponseNpcPoint', 'directionFromResponseNpcAngle', 'parseResponseNpcTime', 'positionResponseNpcAt']) {
    const start = source.indexOf(`window.${name} = function(`);
    assert(start >= 0, name);
    const end = source.indexOf('\n            };', start) + '\n            };'.length;
    vm.runInContext(source.slice(start, end), ctx);
}
const start = Date.parse('2026-09-17T12:00:00Z');
let samples = 0;
for (const trajectory of ['orbital_search', 'spiral_sweep', 'intercept_loop']) {
    for (const radius of [25, 160, 300]) {
        const capsule = {incident_center: {lat: 52, lng: 21}, spawn_at: new Date(start),
            expires_at: new Date(start + 3600000), speed_mps: 8, patrol_radius_m: radius,
            trajectory_type: trajectory, trajectory_phase_deg: 17};
        for (let seconds = 1; seconds < 240; seconds += 3) {
            const time = start + seconds * 1000;
            const p = window.positionResponseNpcAt(capsule, new Date(time));
            const before = window.positionResponseNpcAt(capsule, new Date(time - 100));
            const after = window.positionResponseNpcAt(capsule, new Date(time + 100));
            const east = (after.lng - before.lng) * Math.cos(p.lat * Math.PI / 180);
            const north = after.lat - before.lat;
            const bearing = Math.atan2(east, north) * 180 / Math.PI;
            const heading = window.responseNpcDirections.indexOf(p.direction) * 45;
            const error = Math.abs(((heading - bearing + 540) % 360) - 180);
            assert(error < 24, `${trajectory} radius=${radius} t=${seconds}: heading error ${error}`);
            samples++;
        }
    }
}
console.log(`NPC heading PASS: ${samples} movement samples across all trajectories`);
