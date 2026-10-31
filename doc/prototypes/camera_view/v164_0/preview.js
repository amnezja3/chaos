/* Isolated 164.0 UI backed by durable fixture receipts. Never loaded by the game. */
'use strict';
const $ = s => document.querySelector(s);
const sourceURL = 'https://commons.wikimedia.org/wiki/File:2018_Warszawa_Wa%C5%82owa.jpg';
const words = {
    pl: {open:'Podgląd kamery',intro:'Jedna kamera. Archiwalne otoczenie. Połączenie przez aplikację Ghost System.',note:'Izolowany prototyp · wynik operacji jest symulowany · bez kont, HC, bazy i dostawców.',connect:'Uruchom testową operację',pending:'Oczekiwanie na wynik testowej operacji camera_stream.',archive:'Materiał archiwalny — symulacja, nie transmisja na żywo',area:'Otoczenie lokalizacji · kierunek nieznany',photo:'Zdjęcie: 19.07.2018',info:'Licencja i źródło zdjęcia',author:'Autor',date:'Data wykonania',license:'Licencja',changes:'Zmiany',changeText:'Miniatura 960 × 720. Bez zmian w pliku; w podglądzie filtr koloru, scanlines i opcjonalne kadrowanie.',copy:'Kopiuj adres',copied:'Adres skopiowany.',copyError:'Schowek niedostępny — zaznacz i skopiuj widoczny adres.',external:'Otwórz źródło',stay:'POZOSTAŃ W CHAOS',go:'OTWÓRZ WIKIMEDIA',warning:'Zamierzasz opuścić środowisko CHAOS i przejść do Wikimedia Commons. Opuścisz bieżący widok. W PWA może nastąpić przełączenie do przeglądarki. Czy chcesz kontynuować?',close:'Zamknij kamerę',hide:'Zamknij informacje',pause:'Pauza efektów',resume:'Wznów efekty',full:'Pełny kadr',detail:'Zbliżenie',frame:'01 / 01 · jedno zdjęcie',empty:'Brak zdjęć otoczenia. Wynik operacji gry pozostaje bez zmian.',lost:'Materiał niedostępny. Wynik operacji gry pozostaje bez zmian.',revoked:'Materiał wycofany. Nie jest dostępny w podglądzie.',sync:'Synchronizacja lokalnego materiału…',test:'Materiał testowy · Wikimedia Commons · Cybularny · CC0 1.0',title:'Kanał obserwacyjny',id:'Identyfikator',source:'Źródło'},
    en: {open:'Camera preview',intro:'One camera. Archived surroundings. Connected through a Ghost System application.',note:'Isolated prototype · simulated operation result · no accounts, HC, database or providers.',connect:'Run test operation',pending:'Waiting for the test camera_stream operation result.',archive:'Archive material — simulation, not a live feed',area:'Location surroundings · heading unknown',photo:'Photo: 19 Jul 2018',info:'Photo license and source',author:'Author',date:'Captured',license:'License',changes:'Changes',changeText:'960 × 720 thumbnail. File unchanged; preview adds color filtering, scanlines and optional cropping.',copy:'Copy URL',copied:'URL copied.',copyError:'Clipboard unavailable — select and copy the visible URL.',external:'Open source',stay:'STAY IN CHAOS',go:'OPEN WIKIMEDIA',warning:'You are about to leave CHAOS and visit Wikimedia Commons. This will leave the current view. In a PWA you may be switched to a browser. Do you want to continue?',close:'Close camera',hide:'Close information',pause:'Pause effects',resume:'Resume effects',full:'Full frame',detail:'Close-up',frame:'01 / 01 · one photo',empty:'No photos of the surroundings. The gameplay result remains unchanged.',lost:'Material unavailable. The gameplay result remains unchanged.',revoked:'Material withdrawn. It is unavailable in this preview.',sync:'Synchronizing local material…',test:'Test material · Wikimedia Commons · Cybularny · CC0 1.0',title:'Observation channel',id:'Identifier',source:'Source'}
};
let lang='pl', pendingApp=null, current=null, csrf='', epoch=0, busy=false, explicitOpen=false;
const documentId=crypto.randomUUID(), desktopWindows=new Map();
let fixtureContext={}, refDismissed=false, operationsDismissed=false, leaseTimer;
const t=key=>words[lang][key];
const escapeHTML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ofsVisualLiftEnabled=true, WORKSPACE_WINDOW_APPS=new Set();
const consumeProvisionalHydrationWindow=()=>null;
const buildApplicationWindowLaunchKey=id=>id;
const getCurrentAppFlowId=()=> 'fixture';
function applyApplicationLaunchContext(app){app.dataset.appTitle=fixtureContext.title;app.dataset.kind=fixtureContext.kind;return {app_name:fixtureContext.title};}
const findAvailablePosition=()=>({top:fixtureContext.kind==='preview'?100:330,left:fixtureContext.kind==='preview'?Math.max(12,(innerWidth-1000)/2):24});
function beginApplicationRenderLaunch(){return true;}
function finishApplicationRenderWindow(app){
    document.body.append(app);pendingApp=app;
    const close=app.querySelector('.close-btn');close.setAttribute('role','button');close.tabIndex=0;close.setAttribute('aria-label',t('close'));
    close.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();close.click();}});
    const name=document.createElement('span');name.className='window-name';
    name.textContent=fixtureContext.title;app.querySelector('.title-bar').firstChild.replaceWith(name);
    bindWindowMaximize(app,fixtureContext.title);makeDraggable(app);
    app.querySelector('.workspace-minimize-btn').setAttribute('aria-label',lang==='pl'?'Minimalizuj':'Minimize');
    app.querySelector('.browser-maximize-btn').setAttribute('aria-label',lang==='pl'?'Maksymalizuj':'Maximize');
    close.focus();
}
function registerWindowInTaskbar(app){app.dataset.windowId=app.dataset.appId;desktopWindows.set(app.dataset.appId,app);renderRunningApps();}
function connectedRunningWindows(){return [...desktopWindows.values()].filter(e=>e.isConnected);}
function bringWindowToFront(app){connectedRunningWindows().forEach(e=>e.classList.remove('active'));app.classList.remove('is-window-minimized');app.classList.add('active');app.style.zIndex=String(++bringWindowToFront.z);renderRunningApps();}
bringWindowToFront.z=20;
function renderRunningApps(){
    const bar=$('#tasks');if(!bar)return;bar.replaceChildren();
    connectedRunningWindows().forEach(app=>{const b=document.createElement('button');b.className='system-task-button';b.dataset.windowId=app.dataset.windowId;b.textContent=app.dataset.appTitle;b.onclick=()=>bringWindowToFront(app);bar.append(b);});
}
const isMobileSafeMode=()=>innerWidth<=600;
function applyMobileSafeModeToWindow(app){app.classList.toggle('mobile-window',isMobileSafeMode());}
function ghostText(){return t('pending');}
function ghostApplicationField(_a,_b,value){return escapeHTML(value);}
function appFlowTrace(){}
function addSystemMessage(){}
function ghostRuntimeReply(response){return response.success?'SUCCESS':'FAILURE';}
function setAppButtonGroupPending(buttons){buttons.forEach(b=>b.disabled=true);}
function startLegacyAppWaitUnlessFeedbackEnabled(){return ()=>{};}
async function api(path,data){
    const r=await fetch('/api/'+path,data===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json','X-Fixture-CSRF':csrf},body:JSON.stringify(data)});
    const value=await r.json();if(!r.ok)throw Error(value.error||'request_failed');return value;
}
async function sendGonnaWinRequest(){const receipt=await api('result',{success:$('#outcome').value==='success'});await refresh();return {success:receipt.success};}
function disposeOperationFeedbackWindow(app,reason){
    if(app.dataset.kind==='operations')operationsDismissed=true;
    app._dispose?.();clearInterval(app._countdown);clearTimeout(app._close);
    if(app.dataset.kind==='reference'&&reason!=='auto_close')refDismissed=true;
    if(app.dataset.kind==='preview'){
        clearTimeout(leaseTimer);
        if(reason!=='lease_lost'&&reason!=='logout')api('release',{document:documentId,closed:true}).catch(showError);
    }
    desktopWindows.delete(app.dataset.appId);setTimeout(renderRunningApps,0);
}
function removeWindow(app,reason){if(!app)return;disposeOperationFeedbackWindow(app,reason);app.remove();renderRunningApps();}
function scheduleOperationalAppAutoClose(app){scheduleReferenceClose(app);}
function scheduleReferenceClose(app){
    if(!current?.receipt?.success||app._countdown)return;
    const box=document.createElement('div');box.className='app-auto-close-overlay';box.setAttribute('role','timer');
    const update=()=>{
        const remaining=Math.max(0,Math.ceil(current.receipt.close_at-current.now-(performance.now()-current.received)/1000));
        box.textContent='SESSION CLOSE '+String(remaining).padStart(2,'0')+' s';
        if(!remaining){clearInterval(app._countdown);removeWindow(app,'auto_close');}
    };
    app.querySelector('.app-content').append(box);update();app._countdown=setInterval(update,100);
}
function standardWindow(id,title,kind){
    let app=desktopWindows.get(id);if(app?.isConnected)return app;
    fixtureContext={title,kind};app_window(id,[{title:'',list:[],buttons:[]}]);return pendingApp;
}
function openCamera(){
    if(!current){$('#message').textContent='LOGIN';return;}
    const r=current?.receipt;
    if(r?.file_verified){explicitOpen=true;refresh();return;}
    if(r?.success&&current.now>=r.close_at){showOperations();return;}
    const id=r?.reference_id||'reference-pending';
    const old=desktopWindows.get(id);if(old?.isConnected){bringWindowToFront(old);return;}
    fixtureContext={title:'GLASS EYE / ACCESS',kind:'reference'};
    app_window(id,[{title:lang==='pl'?'Aplikacja referencyjna':'Reference application',list:[t('pending')],buttons:r?[]:[{action:'connect',label:t('connect')}]}]);
    const app=pendingApp;
    if(r){app.querySelector('.choice-result').textContent=r.success?'SUCCESS':'FAILURE';if(r.success)scheduleReferenceClose(app);}
}
function showOperations(){
    if(!current)return;
    const app=standardWindow('operation-control',lang==='pl'?'CENTRUM OPERACJI':'OPERATION CONTROL','operations');
    const r=current.receipt, op=current.operations[0];
    const box=app.querySelector('.app-content');
    if(!op){box.innerHTML='<p>'+(lang==='pl'?'Brak pobierania.':'No download.')+'</p>';return;}
    const progress=r.progress;
    box.innerHTML='<section class="download"><p class="eyebrow">CAMERA ACTIVATION</p><h2>Glass Eye.activation</h2><p>'+(lang==='pl'?'Pobieranie na dysk gracza · 30 minut':'Download to player disk · 30 minutes')+'</p><progress max="100" value="'+progress+'"></progress><strong class="download-percent">'+progress+'%</strong><p class="download-state">'+(r.state==='READY'?(lang==='pl'?'Zapis potwierdzony · aktywator gotowy':'Write verified · activation ready'):r.state==='WRITE_FAILED'?(lang==='pl'?'Błąd zapisu — podgląd zablokowany':'Write failed — preview locked'):'DOWNLOADING')+'</p><small>'+escapeHTML(op.operation_id)+'</small></section>';
}
function showFiles(){
    if(!current)return;const app=standardWindow('files',lang==='pl'?'DYSK GRACZA':'PLAYER DISK','files');
    app.querySelector('.app-content').innerHTML='<section class="download">'+(current.files.length?current.files.map(f=>'<p>'+escapeHTML(f.name)+' · '+f.file_size+' MB</p><small>SHA-256 '+escapeHTML(f.checksum)+'</small>').join(''):(lang==='pl'?'Brak plików aktywacyjnych.':'No activation files.'))+'</section>';
}
function showError(error){$('#message').textContent=error.message;}
async function refresh(){
    if(busy)return;busy=true;const generation=epoch;
    try{
        const state=await api('state');if(generation!==epoch)return;
        if(!state.user){logoutUI();return;}
        current={...state,receipt:state.receipt?.id?state.receipt:null,received:performance.now()};$('#session').textContent=state.user;$('#login').hidden=true;$('#logout').hidden=false;$('#open').disabled=false;
        const r=current.receipt;
        if(r){
            let ref=connectedRunningWindows().find(w=>w.dataset.kind==='reference');
            if(!ref&&!refDismissed&&(!r.success||state.now<r.close_at)){openCamera();ref=connectedRunningWindows().find(w=>w.dataset.kind==='reference');}
            if(ref){
                if(r.success&&state.now>=r.close_at)removeWindow(ref,'auto_close');
                else if(r.success)scheduleReferenceClose(ref);
            }
            if(state.operations.length&&!operationsDismissed)showOperations();
            if(desktopWindows.get('files')?.isConnected)showFiles();
            if(r.file_verified&&(!r.closed||explicitOpen)){
                const started=performance.now();const lease=await api('claim',{document:documentId,explicit:explicitOpen});explicitOpen=false;
                if(generation!==epoch)return;
                if(lease&&performance.now()-started<6500){
                    const id=lease.instance_id;
                    let app=desktopWindows.get(id);
                    if(!app?.isConnected){app=standardWindow(id,'GLASS EYE','preview');mount(app);}
                    clearTimeout(leaseTimer);leaseTimer=setTimeout(()=>removeWindow(app,'lease_lost'),6500-(performance.now()-started));
                }else connectedRunningWindows().filter(w=>w.dataset.kind==='preview').forEach(w=>removeWindow(w,'lease_lost'));
            }else connectedRunningWindows().filter(w=>w.dataset.kind==='preview').forEach(w=>removeWindow(w,'lease_lost'));
        }
    }catch(error){if(generation===epoch)showError(error);}finally{busy=false;}
}
function logoutUI(){epoch++;current=null;clearTimeout(leaseTimer);connectedRunningWindows().forEach(w=>removeWindow(w,'logout'));refDismissed=false;operationsDismissed=false;$('#session').textContent='OFFLINE';$('#login').hidden=false;$('#logout').hidden=true;$('#open').disabled=true;}
function mount(app){
    app._dispose?.();
    const content=app.querySelector('.app-content');
    const scenario=$('#scenario').value;
    let disposed=false, timer, paused=matchMedia('(prefers-reduced-motion: reduce)').matches;
    const visibility=()=>{
        const value=paused||document.hidden||app.classList.contains('is-window-minimized');
        if(app.classList.contains('cvn-paused')!==value)app.classList.toggle('cvn-paused',value);
    };
    const observer=new MutationObserver(visibility);
    observer.observe(app,{attributes:true,attributeFilter:['class']});
    document.addEventListener('visibilitychange',visibility);
    const motion=matchMedia('(prefers-reduced-motion: reduce)');
    const motionChange=()=>{paused=motion.matches;visibility(); const b=content.querySelector('[data-pause]');if(b)b.textContent=t(paused?'resume':'pause');};
    motion.addEventListener('change',motionChange);
    app._dispose=()=>{disposed=true;clearTimeout(timer);observer.disconnect();document.removeEventListener('visibilitychange',visibility);motion.removeEventListener('change',motionChange);app.querySelector('dialog')?.remove();};
    content.innerHTML=`<div class="cvn-top"><span>CVN / WAŁOWA–01</span><span class="status" role="status">SYNCHRONIZING</span></div><div class="viewport"><div class="empty"><strong>SYNCHRONIZING</strong><p>${t('sync')}</p></div></div><div class="archive">${t('archive')}</div><div class="cvn-bottom"><span>${t('area')}</span><span>${t('photo')}</span></div>`;
    visibility();
    timer=setTimeout(()=>{
        if(disposed||!app.isConnected)return;
        const viewport=content.querySelector('.viewport');
        const state=scenario==='READY'?'ARCHIVE LINK':({NO_COVERAGE:'NO SIGNAL',FAILED:'SIGNAL LOST',REVOKED:'REVOKED'})[scenario];
        content.querySelector('.status').textContent=state;
        if(scenario!=='READY'){
            viewport.innerHTML=`<div class="empty"><strong>${state}</strong><p>${t(scenario==='NO_COVERAGE'?'empty':scenario==='REVOKED'?'revoked':'lost')}</p></div>`;
            content.querySelector('.cvn-bottom').textContent=t('area'); return;
        }
        viewport.innerHTML=`<img src="/walowa.jpg" alt="${lang==='pl'?'Warszawa, ulica Wałowa przy Świętojerskiej — archiwalna fotografia':'Warsaw, Wałowa Street near Świętojerska — archive photograph'}"><div class="hud"><span>ARCHIVE / 2018 · CH 01</span></div>`;
        viewport.querySelector('img').addEventListener('error',()=>{
            content.querySelector('.status').textContent='ARCHIVE CORRUPTED';
            viewport.innerHTML=`<div class="empty"><strong>ARCHIVE CORRUPTED</strong><p>${t('lost')}</p></div>`;
            content.querySelector('.cvn-controls')?.remove();content.querySelector('.cvn-panel')?.remove();
        },{once:true});
        content.insertAdjacentHTML('beforeend',`<div class="cvn-bottom credit"><span>${t('test')}</span><button data-info>${t('info')} ↗</button></div><div class="cvn-controls"><div class="frame-buttons"><button data-frame="full" aria-pressed="true">${t('full')}</button><button data-frame="detail" aria-pressed="false">${t('detail')}</button></div><span>${t('frame')}</span><button data-pause>${t(paused?'resume':'pause')}</button></div>`);
        content.querySelectorAll('[data-frame]').forEach(b=>b.onclick=()=>{
            viewport.dataset.frame=b.dataset.frame;
            content.querySelectorAll('[data-frame]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
        });
        content.querySelector('[data-pause]').onclick=e=>{paused=!paused;visibility();e.target.textContent=t(paused?'resume':'pause');};
        content.querySelector('[data-info]').onclick=()=>showInfo(content,app);
    },motion.matches?0:950);
}
function showInfo(content,app){
    const old=content.querySelector('.cvn-panel');if(old){old.remove();return;}
    const panel=document.createElement('section');panel.className='cvn-panel';
    panel.innerHTML=`<h2>${t('info')}</h2><dl><dt>${t('author')}</dt><dd>Cybularny</dd><dt>${t('date')}</dt><dd>2018-07-19</dd><dt>${t('id')}</dt><dd>2018 Warszawa Wałowa.jpg</dd><dt>${t('license')}</dt><dd>CC0 1.0 Universal</dd><dt>${t('changes')}</dt><dd>${t('changeText')}</dd><dt>${t('source')}</dt><dd><a href="${sourceURL}" data-source>${sourceURL}</a></dd></dl><button data-copy>${t('copy')}</button><button data-external>${t('external')}</button><button data-hide>${t('hide')}</button><p id="copy-status" role="status"></p>`;
    content.append(panel);
    panel.querySelector('[data-copy]').onclick=async()=>{
        try{await navigator.clipboard.writeText(sourceURL);panel.querySelector('#copy-status').textContent=t('copied');}
        catch{panel.querySelector('#copy-status').textContent=t('copyError');}
    };
    panel.querySelector('[data-hide]').onclick=()=>{panel.remove();content.querySelector('[data-info]').focus();};
    const external=e=>{e.preventDefault();confirmExternal(app,e.currentTarget);};
    panel.querySelector('[data-external]').onclick=external;
    panel.querySelector('[data-source]').onclick=external;
    panel.querySelector('[data-copy]').focus();
}
function confirmExternal(app,trigger){
    const dialog=document.createElement('dialog');
    // A fixed public source URL, frozen at click; never accepts a caller URL.
    dialog.innerHTML=`<h2>EXTERNAL CONNECTION</h2><p>${t('warning')}</p><p>Wikimedia Commons · 2018 Warszawa Wałowa.jpg</p><button>${t('stay')}</button> <a href="${sourceURL}">${t('go')}</a>`;
    app.append(dialog);dialog.querySelector('button').onclick=()=>dialog.close();
    dialog.addEventListener('close',()=>{dialog.remove();if(trigger.isConnected)trigger.focus();},{once:true});
    dialog.showModal();dialog.querySelector('button').focus();
}
function translate(){
    lang=$('#language').value.toLowerCase();document.documentElement.lang=lang;
    $('#intro').textContent=lang==='pl'?'SUCCESS → SESSION CLOSE → aktywator 30 min → osobne okno GLASS EYE':'SUCCESS → SESSION CLOSE → 30 min activation → separate GLASS EYE window';
    $('#fixture-note').textContent=lang==='pl'?'Lokalny prototyp 164.0 · izolowane konta i trwała baza testowa · bez zmian w grze':'Local 164.0 prototype · isolated accounts and persistent test database · no game changes';
    $('#open').textContent=lang==='pl'?'Uruchom GLASS EYE':'Launch GLASS EYE';
    connectedRunningWindows().filter(w=>w.dataset.kind==='preview').forEach(mount);
    if(current?.operations.length)showOperations();
}
$('#open').onclick=openCamera;$('#language').onchange=translate;
$('#scenario').onchange=()=>connectedRunningWindows().filter(w=>w.dataset.kind==='preview').forEach(mount);
$('#login').onclick=async()=>{try{await api('login',{user:$('#account').value});epoch++;refDismissed=false;await refresh();}catch(e){showError(e);}};
$('#logout').onclick=async()=>{epoch++;try{await api('logout',{document:documentId});}finally{logoutUI();}};
$('#operations').onclick=()=>{operationsDismissed=false;showOperations();};$('#files').onclick=showFiles;
$('#advance').onclick=async()=>{await api('advance',{seconds:900});await refresh();};
window.addEventListener('resize',()=>connectedRunningWindows().forEach(applyMobileSafeModeToWindow));
window.addEventListener('pagehide',()=>{fetch('/api/release',{method:'POST',headers:{'Content-Type':'application/json','X-Fixture-CSRF':csrf},body:JSON.stringify({document:documentId}),keepalive:true}).catch(()=>{});});
$('#open').disabled=true;
translate();
api('bootstrap').then(async data=>{csrf=data.csrf;$('#advance').hidden=!data.test_controls;await refresh();setInterval(refresh,1000);}).catch(showError);
