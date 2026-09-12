/* Reference only: no API, show authority or production trigger. */
(function () {
    'use strict';
    const scene=document.querySelector('.archive-scene'), video=document.getElementById('archive-video');
    let timer=null;
    function setState(state) {
        clearTimeout(timer);
        const playing=state==='video';
        scene.dataset.state=playing?'video':'record';
        document.getElementById('scene-title').textContent=playing?'REKONSTRUKCJA':'ZAPIS';
        document.getElementById('archive-caption').textContent=playing?'ODTWORZENIE ARCHIWALNEGO OBRAZU':'PRZYGOTOWANIE ODCZYTU';
        document.getElementById('show-time').firstChild.textContent=playing?'07:05 ':'07:00 ';
        video.pause();
        if(playing){
            if(!video.getAttribute('src'))video.src='../../video/ghostsignal_transmission_video.mp4';
            video.currentTime=0;video.muted=true;video.controls=false;
            video.play().catch(function(){});
        }
    }
    video.addEventListener('timeupdate',function(){
        const t=Math.min(38.12,video.currentTime||0);
        document.getElementById('video-time').textContent='00:'+String(Math.floor(t)).padStart(2,'0')+' / 00:38,12';
        document.getElementById('show-time').firstChild.textContent='07:'+String(5+Math.floor(t)).padStart(2,'0')+' ';
        scene.querySelector('.progress i').style.width=((425+t)/900*100)+'%';
    });
    video.addEventListener('error',function(){scene.querySelector('.video-fallback').hidden=false;});
    window.addEventListener('message',function(event){
        if(event.origin!==location.origin||event.source!==window.parent)return;
        if(event.data==='archive-record')setState('record');
        if(event.data==='archive-video')setState('video');
        if(event.data==='archive-transition'){setState('record');timer=setTimeout(function(){setState('video');},5000);}
    });
    window.addEventListener('pagehide',function(){clearTimeout(timer);video.pause();});
    document.addEventListener('visibilitychange',function(){if(document.hidden){clearTimeout(timer);video.pause();}});
    setState(new URLSearchParams(location.search).get('state'));
})();
