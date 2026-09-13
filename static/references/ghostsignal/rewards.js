/* Reference-only reward groups; no game API, writes or audio. */
(function(){'use strict';
 const groups=[
  {label:'KONTROLA WĘZŁÓW',rsp:200,count:20,description:'Utrzymanie części sieci do chwili wysłania sygnału.'},
  {label:'ZAMKNIĘCIE SYGNAŁU',rsp:40,count:1,description:'Domknięcie sieci i uruchomienie finału cyklu.'},
  {label:'TERYTORIA FINAŁU',rsp:124,count:23,description:'Rozliczenie terytoriów objętych wysłaniem sygnału.'}
 ];
 const list=document.getElementById('reward-rows'),total=groups.reduce((s,g)=>s+g.rsp,0);let index=0,timer=null;
 groups.forEach((g,i)=>{const row=document.createElement('li');row.className='reward-row';const line=document.createElement('div'),label=document.createElement('span'),value=document.createElement('b'),count=document.createElement('small');label.textContent=String(i+1).padStart(2,'0')+' / '+g.label;value.textContent=g.rsp+' RSP';count.textContent='ZAPISY NAGRÓD / '+g.count;line.appendChild(label);line.appendChild(value);row.appendChild(line);row.appendChild(count);list.appendChild(row);});
 function show(i){index=i;const g=groups[i];document.getElementById('reward-index').textContent=String(i+1).padStart(2,'0')+' / '+g.label;document.getElementById('reward-rsp').textContent=g.rsp;document.getElementById('reward-count').textContent=g.count;document.getElementById('reward-description').textContent=g.description;document.getElementById('reward-meter').style.width=(100*g.rsp/total)+'%';document.getElementById('reward-step').textContent=String(i+1).padStart(2,'0')+' / 03';Array.from(list.children).forEach((row,n)=>{row.classList.toggle('is-current',n===i);if(n===i)row.setAttribute('aria-current','true');else row.removeAttribute('aria-current');});}
 function stop(){clearInterval(timer);timer=null;}function play(){stop();show(0);timer=setInterval(()=>{if(index===groups.length-1){stop();return;}show(index+1);},10000);}
 window.addEventListener('message',e=>{if(e.origin!==location.origin)return;if(e.data==='rewards-play')play();if(e.data==='rewards-pause')stop();if(e.data==='rewards-next'){stop();show((index+1)%groups.length);}});
 window.addEventListener('pagehide',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});show(0);
})();
