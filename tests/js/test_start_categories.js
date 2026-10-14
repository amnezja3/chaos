const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'static/js/terminal.js'), 'utf8');
const context = {openWalletApp() {}, createEmailClient() {}, createMap() {}};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function startAppCategory('), source.indexOf('function renderStartMenu(')), context);
const category = entry => context.startAppCategory({entry});
for (const [entry, expected] of [
    [{type:'scanner', target_types:['poi','player']}, 'recon'],
    [{type:'scanner', creator_contract:{action:'scan_player', target_types:['player']}}, 'pvp'],
    [{type:'exploit', creator_contract:{action:'exploit_player'}}, 'pvp'],
    [{type:'sniffer', target_types:['player']}, 'pvp'],
    [{type:'tracker', target_types:['player']}, 'pvp'],
    [{type:'scanner', map_actions:['mic_sniff']}, 'monitoring'],
    [{type:'camera_tool', map_actions:['camera_shutdown']}, 'exploits'],
    [{type:'camera_tool', map_actions:['camera_stream']}, 'recon'],
    [{id:'financialSniffer', type:'pro-system-tool'}, 'pvp'],
    [{id:'random-generated', template_id:'security_panel_proxy'}, 'pvp'],
    [{template_id:'deep_scanner', tool_family:'pro_system_tool'}, 'recon'],
    [{template_id:'file_cleanup'}, 'service'],
    [{template_id:'ptk_document'}, 'analysis'],
    [{system_launcher:'ghost_lab'}, 'creators'],
    [{system_launcher:'operation_control'}, 'monitoring'],
    [{system_launcher:'createAgi2108ConsoleApp'}, 'analysis'],
    [{type:'wallet'}, 'finance'],
    [{type:'radio'}, 'social'],
    [{type:'os_component'}, 'service'],
    [{name:'Scanner exploit PvP'}, 'gameplay'],
]) assert.equal(category(entry), expected, JSON.stringify(entry));
const allowed = new Set(['recon','exploits','monitoring','pvp','analysis','finance','social','creators','service','system','gameplay']);
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'static/app_config.json'), 'utf8'));
for (const app of catalog) assert(allowed.has(category(app)), app.id);
console.log(`Start categories: PASS; ${catalog.length} catalog entries covered`);
