const {spawn}=require('node:child_process');
const readline=require('node:readline');
const server=spawn('cmd.exe',['/d','/c','npx.cmd','-y','@playwright/mcp@latest','--config','C:/Users/aimse/.codex/playwright-mcp.json'],{windowsHide:true,stdio:['pipe','pipe','pipe']});
let serial=0;const pending=new Map();
server.stderr.on('data',data=>process.stderr.write(data));
readline.createInterface({input:server.stdout}).on('line',line=>{let message;try{message=JSON.parse(line);}catch{return;}if(pending.has(message.id)){const p=pending.get(message.id);pending.delete(message.id);clearTimeout(p.timer);message.error?p.reject(Error(JSON.stringify(message.error))):p.resolve(message.result);}});
function request(method,params){return new Promise((resolve,reject)=>{const id=++serial;const timer=setTimeout(()=>{pending.delete(id);reject(Error('Timeout: '+method));},90000);pending.set(id,{resolve,reject,timer});server.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');});}
async function call(name,args){const result=await request('tools/call',{name,arguments:args});for(const item of result.content||[])if(item.type==='text')console.log(item.text.split('### Ran Playwright code')[0]);if(result.isError)throw Error(name+' failed');return result;}
(async()=>{try{
console.log('INITIALIZE',JSON.stringify(await request('initialize',{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'codex-setup-smoke',version:'1.0'}})));
server.stdin.write(JSON.stringify({jsonrpc:'2.0',method:'notifications/initialized'})+'\n');
const list=await request('tools/list',{});console.log('TOOLS',list.tools.map(t=>t.name).join(', '));
await call('browser_navigate',{url:'http://127.0.0.1:5000'});
const fs=require('node:fs');
const template=fs.readFileSync('templates/map_template.html','utf8');
const css=template.match(/<style>([\s\S]*?)<\/style>/)[1];
await call('browser_evaluate',{function:`async () => {
document.head.innerHTML=''; document.body.innerHTML='';
for(const href of ['/static/css/style.css','/static/css/blacknet.css','/static/css/ghostnetwork_map.css','/static/css/ghostlab_scanner.css']) {const link=document.createElement('link');link.rel='stylesheet';link.href=href;document.head.append(link);await new Promise(resolve=>{link.onload=resolve;link.onerror=resolve;});}
const s=document.createElement('style');s.textContent=${JSON.stringify(css)};document.head.append(s);
document.body.innerHTML='<div class="leaflet-container" style="position:relative;width:900px;height:650px;background:#8f9987"><div class="chaos-map-scan-overlay deep-scanner-styled is-visible" style="--scanner-frame:#65eaff;--scanner-button:#65eaff" data-scanner-pattern="viewfinder" data-label="TEST"></div></div>';
for(const href of ['https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css','https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css']) {const link=document.createElement('link');link.rel='stylesheet';link.href=href;document.head.append(link);await new Promise(resolve=>{link.onload=resolve;link.onerror=resolve;});}
const el=document.querySelector('.chaos-map-scan-overlay');
return ['regular','pulse','wave','viewfinder','direct'].map(p=>{el.dataset.scannerPattern=p;const c=getComputedStyle(el,'::before');return {p,width:c.width,height:c.height,color:c.color,background:c.background,animation:c.animation,display:getComputedStyle(el).display};});
}`});
await call('browser_evaluate',{function:`async () => {
const script=document.createElement('script');script.src='https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js';document.head.append(script);await new Promise(resolve=>script.onload=resolve);
document.body.innerHTML='';document.body.style.cssText='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:12px;background:#17201c;height:auto;overflow:auto';
const results=[];
for(const pattern of ['regular','pulse','wave','viewfinder','direct']) {
 const card=document.createElement('section');card.innerHTML='<h3 style="color:white">'+pattern+'</h3><div style="height:300px"></div>';document.body.append(card);
 const box=card.lastElementChild; const map=L.map(box).setView([52,21],12);
 box.style.background='repeating-linear-gradient(30deg,#d4d1ba 0 45px,#faf9f2 46px 52px,#bfcbb4 53px 90px)';
 const overlay=document.createElement('div');overlay.className='chaos-map-scan-overlay deep-scanner-styled is-visible';overlay.dataset.scannerPattern=pattern;overlay.dataset.label='Test mapy Leaflet';overlay.style.cssText='--scanner-frame:#b6ff54;--scanner-button:#b6ff54';box.append(overlay);
 await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
 for(const animation of overlay.getAnimations({subtree:true})) {animation.pause();animation.currentTime=800;}
 const cs=getComputedStyle(overlay,'::before');
 if(cs.content==='none'||cs.display==='none'||parseFloat(cs.width)<=0||parseFloat(cs.height)<=0) throw Error(pattern+' invisible');
 results.push({pattern,width:cs.width,height:cs.height,opacity:cs.opacity,animation:cs.animationName,filter:cs.filter});
}
return results;
}`});
await call('browser_take_screenshot',{type:'png',filename:'.playwright-mcp/scanner-after.png'});
await call('browser_resize',{width:390,height:844});
await call('browser_evaluate',{function:`async () => {document.body.style.gridTemplateColumns='1fr'; window.dispatchEvent(new Event('resize')); return [...document.querySelectorAll('.chaos-map-scan-overlay')].map(el=>({pattern:el.dataset.scannerPattern,width:el.getBoundingClientRect().width,effectWidth:getComputedStyle(el,'::before').width}));}`});
await call('browser_take_screenshot',{type:'png',filename:'.playwright-mcp/scanner-mobile.png',fullPage:true});
await call('browser_console_messages',{level:'error'});
await call('browser_close',{});
console.log('PLAYWRIGHT MCP SMOKE PASS');
}catch(error){console.error(error.message);process.exitCode=1;try{await call('browser_close',{});}catch{}}
finally{server.stdin.end();setTimeout(()=>server.kill(),3000).unref();}
})();
