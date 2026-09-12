/* Local reference only. No API, gameplay state, production trigger or audio. */
(function () {
    'use strict';
    const scene=document.querySelector('.archive-scene');
    const video=document.getElementById('archive-video');
    const field=document.querySelector('.archive-video-field');
    const flash=document.createElement('div');flash.className='archive-flash';flash.setAttribute('aria-hidden','true');scene.appendChild(flash);
    const terminal=document.createElement('div');terminal.className='archive-flash-terminal';terminal.hidden=true;
    const output=document.createElement('pre');terminal.appendChild(output);field.appendChild(terminal);
    let frame=null, started=0;
    const text=[
        '> ZAPIS TRANSMISJI',
        '  ODCZYT ARCHIWUM GHOSTNETWORK',
        '> ŚLAD SYGNAŁU',
        '  PRZEJŚCIE DO KANAŁU 2108',
        '',
        'GHOSTNETWORK // 2108',
        '-------------------------',
        '> PRZEKAZ / FRAGMENT REFERENCYJNY',
        '  Z rozproszonych fragmentów',
        '  powstaje pełny obraz.',
        '',
        '> KONIEC FRAGMENTU _'
    ].join('\n');
    function stop(){if(frame!==null)cancelAnimationFrame(frame);frame=null;}
    function draw(elapsed){
        // Hard cuts for the three exposures; only the final 125 ms fades.
        let opacity=1, inset='0';
        if(elapsed<50)inset='inset(calc(50% - 1px) 0 calc(50% - 1px) 0)';
        else if(elapsed<125)inset='inset(12.5% 0 12.5% 0)';
        else if(elapsed<625)inset='inset(0)';
        else if(elapsed<750){inset='inset(0)';opacity=1-Math.pow((elapsed-625)/125,2);}
        else opacity=0;
        flash.style.clipPath=inset;flash.style.opacity=String(opacity);flash.style.visibility=opacity>0?'visible':'hidden';
        terminal.hidden=elapsed<625;
        const chars=Math.max(0,Math.floor((elapsed-750)/24));
        output.textContent=text.slice(0,chars);output.scrollTop=output.scrollHeight;
        const title=elapsed<1850?'ZAPIS':elapsed<3450?'ŚLAD SYGNAŁU':'KANAŁ 2108';
        document.getElementById('scene-title').textContent=title;
        document.querySelector('.title-sub').firstChild.textContent=elapsed<1850?'TRANSMISJI':'GHOSTNETWORK';
        document.getElementById('archive-caption').textContent=elapsed<3450?'ZAPIS TRANSMISJI / ŚLAD SYGNAŁU':'PRZEKAZ Z KANAŁU 2108';
        document.getElementById('video-time').textContent=elapsed<750?'KONIEC ZAPISU':'KANAŁ / 2108';
    }
    function play(){
        stop();video.pause();started=performance.now();
        const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        function tick(now){
            const elapsed=now-started+(reduced?750:0);draw(elapsed);
            if(elapsed<750+text.length*24+1000)frame=requestAnimationFrame(tick);else frame=null;
        }
        tick(started);
    }
    function ready(){
        stop();flash.style.visibility='hidden';terminal.hidden=true;video.pause();
        document.getElementById('scene-title').textContent='REKONSTRUKCJA';
        document.querySelector('.title-sub').firstChild.textContent='TRANSMISJI';
        document.getElementById('archive-caption').textContent='KONIEC ARCHIWALNEGO ZAPISU';
        document.getElementById('video-time').textContent='00:38,12 / 00:38,12';
    }
    window.addEventListener('message',function(event){
        if(event.origin!==location.origin||event.source!==window.parent)return;
        if(event.data==='flash-play')play();
        if(event.data==='flash-ready')ready();
        if(event.data==='flash-terminal'){stop();draw(20000);}
    });
    window.addEventListener('pagehide',stop);
    document.addEventListener('visibilitychange',function(){if(document.hidden){stop();flash.style.visibility='hidden';}});
    scene.dataset.state='video';
    document.getElementById('show-time').firstChild.textContent='07:43 ';
    scene.querySelector('.progress i').style.width='51.4578%';
    ready();
})();
