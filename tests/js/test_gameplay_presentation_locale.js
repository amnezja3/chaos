const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const config=JSON.parse(fs.readFileSync('static/data/operation_feedback.v1.json'));
const before=JSON.stringify(config),outputs={};
for(const locale of ['pl','en']){
 const sandbox=vm.createContext({console});require('./locale_fixture')(sandbox,locale);
 vm.runInContext(fs.readFileSync('static/js/operation_feedback.js','utf8'),sandbox);
 const ofs=sandbox.window.OperationFeedbackSystem,profile=config.operations.car_hack;
 outputs[locale]=[];
 for(const voice of ['terminal','button_choices','window','progressbar_random','default'])for(const stage of config.provisional_timelines.launch_150s.stages){
   const result=ofs.composeProvisionalScene({config,profile,stage,context:{interface:voice,app_title:'Custom name',description:'Tekst autora',target_label:'VW',action_label:'car_hack'},random:()=>.4});
   const node={dataset:{}};ofs.setSystemText(node,result.lines[0]);
   assert(node.dataset.ghostI18n.startsWith('apps.preload.scene.'));
   outputs[locale].push([result.scene_id,result.family,result.phase,result.transition,result.variant_key,result.wait_band]);
 }
 const messages=JSON.parse(fs.readFileSync(`static/locales/${locale}/map_workspace.json`)).messages;
 const codes=[...fs.readFileSync('ghostnetwork/ability_presentation.py','utf8').matchAll(/^\s*"([a-z_]+)": \(/gm)].map(x=>x[1]);
 assert.equal(codes.length,20);
 for(const code of codes)for(const field of ['name','tagline','description'])assert(messages[`map.ability.${code}.${field}`]?.text);
 const sceneIds=[...fs.readFileSync('templates/map_template.html','utf8').matchAll(/scene_id: '([^']+)', sound_event: 'secret_path/g)].map(x=>x[1]);
 assert.equal(sceneIds.length,6);
 for(const id of sceneIds)for(const field of ['eyebrow','title','copy'])assert(messages[`map.secret.${id}.${field}`]?.text);
 const text=sandbox.window.ghostCopy('map.boot.base_map');
 const node={dataset:{}};sandbox.window.ghostSetCopy(node,text);
 assert.equal(node.dataset.ghostI18n,'map.boot.base_map');
 sandbox.window.ghostSetCopy(node,'Tekst autora');assert.equal(node.textContent,'Tekst autora');assert(!node.dataset.ghostI18n);
}
assert.deepEqual(outputs.pl,outputs.en,'locale must not change scene identity or cadence');
assert(!/showMapPreloader\(\s*['"]/.test(fs.readFileSync('templates/map_template.html','utf8')),
 'Map boot and recovery must retain a locale binding, not a Polish literal');
assert.equal(JSON.stringify(config),before,'presentation cannot mutate runtime configuration');
console.log('Gameplay presentation locale PASS: five voices, stable scenes, 20 abilities, six Secret Path scenes, literal authored text');
