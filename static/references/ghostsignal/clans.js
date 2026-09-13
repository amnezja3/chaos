/* Reference data only; the live finale ranking is not modified. */
(function(){'use strict';
 const clans=[{name:'VIREX',score:180,rsp:14000,members:3,logo:1},
 {name:'Strażnicy Ładu',score:140,rsp:10000,members:2,logo:4},
 {name:'Siatka Widmo',score:110,rsp:7600,members:2,logo:3},
 {name:'Echo Wolności',score:70,rsp:4800,members:1,logo:2}];
 const list=document.getElementById('ranking-rows');let current=0,timer=null;
 clans.forEach((c,i)=>{const row=document.createElement('li');row.className='ranking-row';[String(i+1).padStart(2,'0'),c.name,String(c.score)].forEach(text=>{const cell=document.createElement('span');cell.textContent=text;row.appendChild(cell);});list.appendChild(row);});
 function show(i){current=i;const c=clans[i];document.getElementById('player-nick').textContent=c.name;document.getElementById('player-level').textContent=c.score;document.getElementById('player-rsp').textContent=c.rsp;document.getElementById('clan-members').textContent=c.members;document.getElementById('player-rank-badge').textContent='#'+String(i+1).padStart(2,'0');const logo=document.getElementById('player-avatar');logo.src='../../images/ghostnetwork/clans/'+({1:'virex',2:'echo_freedom',3:'phantom_mesh',4:'sentinel_order'}[c.logo])+'.svg';logo.alt='Logo / '+c.name;['player-position','ranking-counter'].forEach(id=>document.getElementById(id).textContent=String(i+1).padStart(2,'0')+' / 04');Array.from(list.children).forEach((row,n)=>{row.classList.toggle('is-current',n===i);if(n===i)row.setAttribute('aria-current','true');else row.removeAttribute('aria-current');});}
 function stop(){clearInterval(timer);timer=null;}function play(){stop();show(0);timer=setInterval(()=>{if(current===3){stop();return;}show(current+1);},6000);}
 window.addEventListener('message',e=>{if(e.origin!==location.origin)return;if(e.data==='clans-play')play();if(e.data==='clans-pause')stop();if(e.data==='clans-next'){stop();show((current+1)%4);}});
 window.addEventListener('pagehide',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});show(0);
})();
