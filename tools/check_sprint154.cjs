'use strict';
// Frontend contract regression for the 154 PL/EN workspace release.
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const names = [
    'ghost_i18n', 'ghost_i18n_runtime', 'locale_frame', 'map_action_locale',
    'map_lod_syntax', 'scan_marker_actions', 'creator_ux_contract', 'creator_picker_handoff',
    'googleplex_search_categories', 'googleplex_app_purchase_lock', 'googleplex_runtime_bridge',
    'googleplex_download_update', 'ghostnetwork_suite_app', 'ghostnetwork_suite_live',
    'ghostnetwork_suite_navigation', 'signal_registry', 'agi2108_console',
    'ghostlab_publication', 'ghostlab_projects_flow', 'ghostlab_runtime',
    'ghostlab_maintenance', 'ghostlab_firmware', 'ghostlab_scanner',
    'ghostlab_scanner_preview', 'ghostlab_travel', 'player_hack_financial_result',
    'player_hack_log_reader', 'player_hack_request_guard', 'player_hack_window'
];
const files = names.map(name => `tests/js/test_${name}.js`).concat('tests/ghost_signal_show_audio.test.js');
let failed = 0;
for (const file of files) {
    const result = spawnSync(process.execPath, [file], {cwd: root, encoding: 'utf8', timeout: 120000});
    const ok = result.status === 0;
    console.log(`${ok ? 'PASS' : 'FAIL'} ${file}`);
    if (!ok) {
        failed += 1;
        console.error(String(result.error || result.stderr || result.stdout).slice(0, 5000));
    }
}
console.log(`${files.length - failed}/${files.length} frontend suites passed.`);
process.exitCode = failed ? 1 : 0;
