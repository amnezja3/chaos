/* Presentation-only 164.0. This file is never loaded by the game. */
'use strict';
const $ = s => document.querySelector(s);
const sourceURL = 'https://commons.wikimedia.org/wiki/File:2018_Warszawa_Wa%C5%82owa.jpg';
const words = {
    pl: {open:'Podgląd kamery',intro:'Jedna kamera. Archiwalne otoczenie. Połączenie przez aplikację Ghost System.',note:'Izolowany prototyp · wynik operacji jest symulowany · bez kont, HC, bazy i dostawców.',connect:'Uruchom testową operację',pending:'Oczekiwanie na wynik testowej operacji camera_stream.',archive:'Materiał archiwalny — symulacja, nie transmisja na żywo',area:'Otoczenie lokalizacji · kierunek nieznany',photo:'Zdjęcie: 19.07.2018',info:'Licencja i źródło zdjęcia',author:'Autor',date:'Data wykonania',license:'Licencja',changes:'Zmiany',changeText:'Miniatura 960 × 720. Bez zmian w pliku; w podglądzie filtr koloru, scanlines i opcjonalne kadrowanie.',copy:'Kopiuj adres',copied:'Adres skopiowany.',copyError:'Schowek niedostępny — zaznacz i skopiuj widoczny adres.',external:'Otwórz źródło',stay:'POZOSTAŃ W CHAOS',go:'OTWÓRZ WIKIMEDIA',warning:'Zamierzasz opuścić środowisko CHAOS i przejść do Wikimedia Commons. Opuścisz bieżący widok. W PWA może nastąpić przełączenie do przeglądarki. Czy chcesz kontynuować?',close:'Zamknij kamerę',hide:'Zamknij informacje',pause:'Pauza efektów',resume:'Wznów efekty',full:'Pełny kadr',detail:'Zbliżenie',frame:'01 / 01 · jedno zdjęcie',empty:'Brak zdjęć otoczenia. Wynik operacji gry pozostaje bez zmian.',lost:'Materiał niedostępny. Wynik operacji gry pozostaje bez zmian.',revoked:'Materiał wycofany. Nie jest dostępny w podglądzie.',sync:'Synchronizacja lokalnego materiału…',test:'Materiał testowy · Wikimedia Commons · Cybularny · CC0 1.0',title:'Kanał obserwacyjny',id:'Identyfikator',source:'Źródło'},
    en: {open:'Camera preview',intro:'One camera. Archived surroundings. Connected through a Ghost System application.',note:'Isolated prototype · simulated operation result · no accounts, HC, database or providers.',connect:'Run test operation',pending:'Waiting for the test camera_stream operation result.',archive:'Archive material — simulation, not a live feed',area:'Location surroundings · heading unknown',photo:'Photo: 19 Jul 2018',info:'Photo license and source',author:'Author',date:'Captured',license:'License',changes:'Changes',changeText:'960 × 720 thumbnail. File unchanged; preview adds color filtering, scanlines and optional cropping.',copy:'Copy URL',copied:'URL copied.',copyError:'Clipboard unavailable — select and copy the visible URL.',external:'Open source',stay:'STAY IN CHAOS',go:'OPEN WIKIMEDIA',warning:'You are about to leave CHAOS and visit Wikimedia Commons. This will leave the current view. In a PWA you may be switched to a browser. Do you want to continue?',close:'Close camera',hide:'Close information',pause:'Pause effects',resume:'Resume effects',full:'Full frame',detail:'Close-up',frame:'01 / 01 · one photo',empty:'No photos of the surroundings. The gameplay result remains unchanged.',lost:'Material unavailable. The gameplay result remains unchanged.',revoked:'Material withdrawn. It is unavailable in this preview.',sync:'Synchronizing local material…',test:'Test material · Wikimedia Commons · Cybularny · CC0 1.0',title:'Observation channel',id:'Identifier',source:'Source'}
};
let lang='pl', pendingApp=null, accepted=false;
const t = key => words[lang][key];
const escapeHTML = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// The fixture executes app_window and findCameraApplicationWindow from terminal.js.
// Only its environment and operation transport are stubs. No production endpoint.
function beginApplicationRenderLaunch(){return true;}
function prepareApplicationRenderWindow(id){
    const app=document.createElement('section'); app.className='app-window';
    app.dataset.cameraLaunchKey='fixture:walowa'; app.dataset.appId=id;
    pendingApp=app; return {app,hydrated:false,appTitle:'GHOST SYSTEM / '+id};
}
function finishApplicationRenderWindow(app){
    $('#windows').append(app);
    const close=app.querySelector('.close-btn'); close.setAttribute('role','button');
    close.tabIndex=0;close.setAttribute('aria-label',t('close'));
    close.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();close.click();}});
    close.focus();
}
function ghostText(){return t('pending');}
function ghostApplicationField(_a,_b,value){return escapeHTML(value);}
function appFlowTrace(){}
function addSystemMessage(){}
function ghostRuntimeReply(){return '';}
function setAppButtonGroupPending(buttons){buttons.forEach(b=>b.disabled=true);}
function startLegacyAppWaitUnlessFeedbackEnabled(){return ()=>{};}
async function sendGonnaWinRequest(){accepted=true;return {success:true,created_operations:[{operation_type:'camera_stream',operation_id:'fixture-stream-01'}]};}
function disposeOperationFeedbackWindow(app){app._dispose?.();$('#open').focus();}
function scheduleOperationalAppAutoClose(app){mount(app);}
function openCamera(){
    const existing=findCameraApplicationWindow('fixture:walowa');
    if(existing){existing.querySelector('.close-btn').focus();return;}
    const id=$('#application').value==='new'?'Spectral Eye / new':'Spectral Eye / legacy';
    app_window(id,[{title:t('title'),list:[t('pending')],buttons:[{action:'connect',label:t('connect')}]}]);
    if(accepted) mount(pendingApp);
}
function mount(app){
    app._dispose?.();
    const content=app.querySelector('.app-content');
    const scenario=$('#scenario').value;
    let disposed=false, timer, paused=matchMedia('(prefers-reduced-motion: reduce)').matches;
    const visibility=()=>app.classList.toggle('cvn-paused',paused||document.hidden);
    document.addEventListener('visibilitychange',visibility);
    const motion=matchMedia('(prefers-reduced-motion: reduce)');
    const motionChange=()=>{paused=motion.matches;visibility(); const b=content.querySelector('[data-pause]');if(b)b.textContent=t(paused?'resume':'pause');};
    motion.addEventListener('change',motionChange);
    app._dispose=()=>{disposed=true;clearTimeout(timer);document.removeEventListener('visibilitychange',visibility);motion.removeEventListener('change',motionChange);app.querySelector('dialog')?.remove();};
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
    $('#intro').textContent=t('intro');$('#fixture-note').textContent=t('note');$('#open').textContent=t('open');
    const app=findCameraApplicationWindow('fixture:walowa');if(app){disposeOperationFeedbackWindow(app);app.remove();openCamera();}
}
$('#open').onclick=openCamera;$('#language').onchange=translate;
$('#scenario').onchange=()=>{const app=findCameraApplicationWindow('fixture:walowa');if(app&&accepted)mount(app);};
translate();
