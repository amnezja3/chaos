/* Reference fixtures only; no live profiles, API requests or game state. */
(function(){
 'use strict';
 const players=[
  ['NEON_VEX','VIREX',42,980,1,1],['ECHO_7','ECHO',39,850,2,2],
  ['MIRAGE','PHANTOM',38,720,3,3],['WARDEN','SENTINEL',36,640,4,1],
  ['RED_SHIFT','VIREX',34,510,1,4],['RESONANCE','ECHO',32,430,2,4],
  ['NULL_GHOST','PHANTOM',30,320,3,1],['AEGIS','SENTINEL',28,210,4,2]
 ];
 const colors=['#bf5f68','#c8af68','#73b6a5','#799cbc'];
 const list=document.getElementById('ranking-rows');
 const pad=n=>String(n).padStart(2,'0');
 players.forEach((p,i)=>{const row=document.createElement('li');row.className='ranking-row';
  const rank=document.createElement('span'),name=document.createElement('b'),clan=document.createElement('small'),rsp=document.createElement('span');
  rank.textContent=pad(i+1);name.textContent=p[0];clan.textContent=p[1];rsp.textContent=p[3];name.appendChild(clan);
  [rank,name,rsp].forEach(n=>row.appendChild(n));list.appendChild(row);
 });
 let selected=0,timer=null;
 function show(index){selected=Math.max(0,Math.min(players.length-1,index));const p=players[selected];
  document.getElementById('player-nick').textContent=p[0];
  document.getElementById('player-rank-badge').textContent='#'+pad(selected+1);
  const clan=document.getElementById('player-clan');clan.textContent=p[1];const underscore=document.createElement('span');underscore.className='underscore';underscore.textContent='_';clan.appendChild(underscore);
  document.getElementById('player-level').textContent=p[2];document.getElementById('player-rsp').textContent=p[3];
  const avatar=document.getElementById('player-avatar');avatar.src='../../images/avatar-frakcja-'+p[4]+'-player-'+p[5]+'.png';avatar.alt='Avatar / '+p[0];
  document.querySelector('.ranking-scene').style.setProperty('--clan',colors[p[4]-1]);
  ['player-position','ranking-counter'].forEach(id=>document.getElementById(id).textContent=pad(selected+1)+' / '+pad(players.length));
  Array.from(list.children).forEach((row,i)=>{row.classList.toggle('is-current',i===selected);if(i===selected)row.setAttribute('aria-current','true');else row.removeAttribute('aria-current');});
 }
 function stop(){clearInterval(timer);timer=null;}
 function play(){stop();show(0);timer=setInterval(()=>{if(selected===players.length-1){stop();return;}show(selected+1);},6000);}
 window.addEventListener('message',event=>{if(event.origin!==location.origin)return;if(event.data==='ranking-play')play();if(event.data==='ranking-next'){stop();show((selected+1)%players.length);}if(event.data==='ranking-pause')stop();});
 window.addEventListener('pagehide',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
 document.getElementById('player-avatar').onerror=function(){this.onerror=null;this.src='../../images/avatar-default.jpg';};
 show(0);
})();
