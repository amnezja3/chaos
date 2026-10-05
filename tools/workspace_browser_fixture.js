// Isolated window-manager component host; no game server or database access.
// node tools/workspace_browser_fixture.js -> http://127.0.0.1:8990
const http = require('http');
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'static/js/terminal.js'), 'utf8');
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const script = section('const WORKSPACE_WINDOW_APPS', 'function applyMobileSafeModeToOpenWindows(')
    + section('function getWindowTitle(', 'const toolbarObserver');
const html = `<!doctype html><meta charset="utf-8"><title>Workspace controls fixture</title>
<link rel="stylesheet" href="/static/css/style.css">
<link rel="stylesheet" href="/static/css/creator_editor.css">
<div id="system-toolbar"><div style="width:110px">GHOST</div><button id="system-window-tab-button">Next</button><div id="system-running-apps"></div><div id="system-status-strip"><span>ARS 100%</span><span>HC 24000</span><span>LVL 100</span></div></div>
<script>
let topZIndex=100,windowSequence=0;const runningWindows=new Map(),desktopApps=[],toolbarLauncherApps=[];
const ensureSystemToolbar=()=>{},applyMobileSafeModeToWindow=()=>{},isMobileSafeMode=()=>matchMedia('(max-width:900px), (max-height:700px)').matches;
const escapeHTML=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
${script}
document.getElementById('system-window-tab-button').onclick=cycleMobileToolbarWindow;
window.fixtureOpen=(app)=>{
 const win=document.createElement('div');win.className='terminal';win.dataset.app=app;win.dataset.appTitle=app;
 if(['appforge','termcreator','windowmaker','buttonmaker'].includes(app))win.classList.add('creator-window','creator-v2');
 if(['territory-control','operation-control','victim-picker','ghostnetwork-suite','ghostsignal-archive'].includes(app))win.classList.add('pro-tool-window');
 win.style.cssText='top:60px;left:80px;width:620px;height:480px;';
 win.innerHTML='<div class="title-bar">'+app+'<button class="close-btn">X</button></div><textarea>unsaved draft</textarea><div class="fixture-scroll" style="height:100px;overflow:auto"><div style="height:900px">scroll state</div></div><iframe title="state" srcdoc="<input value=iframe-state>"></iframe>';
 if(win.classList.contains('creator-window'))win.querySelector('.close-btn').outerHTML='<span class="close-btn">X</span>';
 if(['browser','ghostlab'].includes(app))win.querySelector('.title-bar').outerHTML='<div class="title-bar browser-title-bar"><span>'+app+'</span><span class="browser-window-controls"><button class="browser-window-control browser-maximize-btn">M</button><button class="close-btn browser-window-control">X</button></span></div>';
 document.body.append(win);makeDraggable(win);win.querySelector('.close-btn').onclick=()=>{win.remove();renderRunningApps();};return win;
};
</script>`;
http.createServer((req,res)=>{
 if(req.url==='/'){res.setHeader('Content-Type','text/html; charset=utf-8');return res.end(html);}
 const file=path.resolve(root,'.'+decodeURIComponent(req.url.split('?')[0]));
 if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){res.statusCode=404;return res.end();}
 res.setHeader('Content-Type',file.endsWith('.css')?'text/css':'application/octet-stream');fs.createReadStream(file).pipe(res);
}).listen(8990,'127.0.0.1',()=>console.log('Workspace fixture http://127.0.0.1:8990'));
