// Explicit immutable presentation checkpoint. Never includes runtime databases or secrets.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const root = path.resolve(__dirname, '..');
const dest = path.join(root, 'doc/prototypes/camera_view/accepted_164_0_2026_10_31');
if (fs.existsSync(dest)) throw new Error('Checkpoint already exists; refusing overwrite');
const inputs = ['static/js/camera_visual.js', 'static/css/camera_visual.css',
    'static/js/chaos_links.js', 'static/css/chaos_links.css', 'static/images/system/chaos-actions.svg',
    'static/images/camera_visual', 'assets/camera_visual/pilot_164_0/paris',
    'tests/browser/camera_visual_gameplay_164_0.js', 'tests/browser/camera_visual_effects_164_0.js',
    'tests/browser/camera_visual_resize_164_0.js', 'tests/browser/camera_visual_reconnect_164_0.js',
    'doc/plans/camera_visual_pilot_164_0_board.md', 'doc/audits/camera_visual_gameplay_164_0.md',
    'artifacts/cvn-164-effects-comparison.png', 'artifacts/cvn-164-effects-dropout.png'];
const files=[];
function copy(relative) {
    const source=path.join(root,relative);
    if(fs.statSync(source).isDirectory()) {
        for(const child of fs.readdirSync(source)) copy(path.join(relative,child));
    } else {
        const data=fs.readFileSync(source), target=path.join(dest,relative);
        fs.mkdirSync(path.dirname(target),{recursive:true}); fs.writeFileSync(target,data,{flag:'wx'});
        files.push({path:relative.replaceAll('\\','/'),bytes:data.length,sha256:crypto.createHash('sha256').update(data).digest('hex')});
    }
}
inputs.forEach(copy);
fs.writeFileSync(path.join(dest,'manifest.json'),JSON.stringify({version:1,status:'OPERATOR PASS — presentation only',base_head:'3556abdcb9603110271e0ea7563fbea4f590ae63',files},null,2)+'\n',{flag:'wx'});
for(const file of files) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(dest,file.path))).digest('hex')!==file.sha256) throw new Error(file.path);
}
console.log(JSON.stringify({checkpoint:dest,files:files.length,verified:true}));
