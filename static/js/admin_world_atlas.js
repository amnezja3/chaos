(function(){
 'use strict';
 const root=document.getElementById('world-atlas');if(!root)return;
 const pl=document.getElementById('poi-admin').dataset.locale!=='en';
 const text=(a,b)=>pl?a:b,$=id=>document.getElementById(id);
 const el=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n;};
 const names={all:text('Wszystkie warstwy','All layers'),poi:'POI',roads:text('Drogi','Roads'),waterways:text('Rzeki i kanały','Waterways'),inland_water:text('Jeziora i zbiorniki','Inland water'),coastline:text('Wybrzeża','Coastline'),land_water:text('Ląd–morze','Land–water')};
 const copy={
  'atlas-title':text('Zapisany świat — dowody i obserwacje','Stored world — evidence and observations'),
  'atlas-hint':text('Obrys obserwacji nie jest dowodem pełnego pokrycia. Mapa pokazuje ograniczony zestaw snapshotów, bez pozycji graczy. Przeciągnij mapę, aby ją przesunąć.','An observation footprint is not complete coverage. This map shows a bounded snapshot set, without player positions. Drag to pan.'),
  'atlas-layer-label':text('Warstwa','Layer'),'atlas-empty-label':text('Pokaż kompletne puste wyniki','Show complete empty results'),
  'atlas-refresh':text('Odśwież dane lokalne','Refresh local data'),'atlas-fit':text('Przegląd świata','World overview'),
  'atlas-viewport':text('Wczytaj widoczny obszar','Load visible area'),
  'atlas-legend':text('Zielony: COMPLETE_FRESH. Pomarańczowy: STALE/EXPIRED. Żółty: PARTIAL. Szary przerywany: UNKNOWN / obserwacje. Blokada odczytu jest oznaczana osobno.','Green: COMPLETE_FRESH. Orange: STALE/EXPIRED. Yellow: PARTIAL. Dashed grey: UNKNOWN / observations. Read restrictions are labelled separately.'),
  'atlas-budget-title':text('Budżety CHAOS i konto dostawcy','CHAOS budgets and provider account')};
 for(const [id,value] of Object.entries(copy))$(id).textContent=value;
 for(const [key,value] of Object.entries(names)){const o=el('option',value);o.value=key;$('atlas-layer').append(o);}
 const svg=$('atlas-map');svg.setAttribute('aria-label',copy['atlas-title']);
 $('atlas-in').setAttribute('aria-label',text('Powiększ','Zoom in'));$('atlas-out').setAttribute('aria-label',text('Pomniejsz','Zoom out'));
 let items=[],view=[0,0,800,360],drag=null,sequence=0,frame=null,queryBounds=null;
 function setView(){svg.setAttribute('viewBox',view.join(' '));}
 function fit(){view=[0,0,800,360];setView();}
 function zoom(f){const w=view[2]*f,h=view[3]*f;if(w<10||w>100000)return;view=[view[0]+(view[2]-w)/2,view[1]+(view[3]-h)/2,w,h];setView();}
 $('atlas-in').onclick=()=>zoom(.7);$('atlas-out').onclick=()=>zoom(1/.7);
 $('atlas-fit').onclick=()=>{queryBounds=null;refresh();};
 $('atlas-viewport').onclick=()=>{
  if(!frame)return;
  const {west,north,scale}=frame;
  const b=[Math.max(-180,west+(view[0]-30)/scale),Math.max(-90,north-(view[1]+view[3]-30)/scale),Math.min(180,west+(view[0]+view[2]-30)/scale),Math.min(90,north-(view[1]-30)/scale)];
  if(b[0]>=b[2]||b[1]>=b[3]||b[2]-b[0]>180){$('atlas-feedback').textContent=text('Przybliż wybrany obszar przed odczytem.','Zoom into a region before loading.');return;}
  queryBounds=b;refresh();
 };
 svg.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,view:[...view],moved:false};};
 svg.onpointermove=e=>{if(!drag)return;const r=svg.getBoundingClientRect();const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.moved ||= Math.abs(dx)+Math.abs(dy)>5;view=[drag.view[0]-dx/r.width*drag.view[2],drag.view[1]-dy/r.height*drag.view[3],view[2],view[3]];setView();};
 svg.onpointerup=()=>{drag=null;};svg.onpointercancel=()=>{drag=null;};svg.onpointerleave=()=>{drag=null;};
 function details(item){const target=$('atlas-details');target.replaceChildren();
  for(const line of [item.provider+' / '+(names[item.profile]||item.profile),item.state+' · '+item.reason,
   text('Obiekty: ','Objects: ')+item.objects+' · '+text('Bajty: ','Bytes: ')+item.bytes,
   text('Lokalny odczyt regionu: ','Local region read: ')+(item.local_read_allowed?text('dopuszczony','allowed'):text('niedopuszczony','not allowed')),
   text('Aktualna zgoda na zapis: ','Current storage permission: ')+(item.policy_allowed?'OK':text('brak / zmieniona','missing / changed')),
   text('Pobrano: ','Fetched: ')+new Date(item.fetched*1000).toLocaleString(),
   text('Świeże do: ','Fresh until: ')+new Date(item.fresh_until*1000).toLocaleString(),
   text('Użyteczne do: ','Usable until: ')+new Date(item.usable_until*1000).toLocaleString(),
   text('Dowód: ','Proof: ')+(item.proof_mode||'UNKNOWN')+' · '+(item.certificate||'—'),
   text('Warstwy: ','Layers: ')+Object.entries(item.layers).filter(([,v])=>v).map(([k,v])=>(names[k]||k)+': '+v).join(', ')])target.append(el('p',line));
 }
 function draw(){svg.replaceChildren();$('atlas-list').replaceChildren();$('atlas-details').replaceChildren();
  const spatial=items.filter(i=>i.bounds);$('atlas-empty-map').textContent=spatial.length?'':text('Brak obrysów do pokazania. To nie oznacza pustego świata.','No footprints to display. This does not mean the world is empty.');
  for(const item of items){const b=el('button',`${item.provider} · ${item.profile} · ${item.state} · ${item.objects}`+(!item.policy_allowed?' · '+text('BRAK ZGODY','PERMISSION BLOCKED'):''));b.type='button';b.onclick=()=>details(item);$('atlas-list').append(b);}
  if(!spatial.length&&!queryBounds){frame=null;$('atlas-viewport').disabled=true;return;}
  const west=queryBounds?.[0]??Math.min(...spatial.map(i=>i.bounds[0])),south=queryBounds?.[1]??Math.min(...spatial.map(i=>i.bounds[1]));
  const east=queryBounds?.[2]??Math.max(...spatial.map(i=>i.bounds[2])),north=queryBounds?.[3]??Math.max(...spatial.map(i=>i.bounds[3]));
  const scale=Math.min(740/Math.max(east-west,.001),300/Math.max(north-south,.001));
  frame={west,north,scale};$('atlas-viewport').disabled=false;
  for(const item of spatial){const b=item.bounds;const rect=document.createElementNS('http://www.w3.org/2000/svg','rect');
   for(const [k,v] of Object.entries({x:30+(b[0]-west)*scale,y:30+(north-b[3])*scale,width:Math.max(3,(b[2]-b[0])*scale),height:Math.max(3,(b[3]-b[1])*scale)}))rect.setAttribute(k,v);
   const color=!item.policy_allowed?'#9aa9a3':item.state==='COMPLETE_FRESH'?'#43ffa1':item.state==='PARTIAL'?'#ffe16b':['COMPLETE_STALE','EXPIRED'].includes(item.state)?'#ff9a50':'#9aa9a3';
   rect.setAttribute('stroke',color);rect.setAttribute('stroke-width','2');rect.setAttribute('fill',item.state==='UNKNOWN'?'none':color);rect.setAttribute('fill-opacity','.18');
   if(item.state==='UNKNOWN')rect.setAttribute('stroke-dasharray','6 4');
   rect.setAttribute('tabindex','0');rect.setAttribute('role','button');rect.setAttribute('aria-label',`${item.provider} ${item.profile} ${item.state}`);
   rect.onclick=()=>details(item);rect.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();details(item);}};svg.append(rect);
  }
 }
 function budgets(accounts){const target=$('atlas-budgets');target.replaceChildren();
  for(const a of accounts){const box=el('section','');box.append(el('h4',a.account),el('p',text('Saldo bieżące nie jest synchronizowane z dostawcą. Poniżej wewnętrzna księga CHAOS.','Live balance is not synchronized with the provider. Internal CHAOS ledger below.')));
   const obs=a.provider_observation;
   box.append(el('p',obs?text('Ręczny odczyt panelu: ','Manual panel observation: ')+`${obs.used} / ${obs.credit_limit} · `+new Date(obs.observed_at*1000).toLocaleString()+(obs.stale?' · '+text('NIEAKTUALNY','STALE'):''):text('Odczyt konta dostawcy: nieznany.','Provider account observation: unknown.')));
   for(const w of a.windows){const p=el('p',`${w.period}: ${w.committed} / ${w.credit_limit} · ${text('Pozostało','Remaining')}: ${w.remaining}`);if(w.warning_threshold){p.className='budget-warning';p.append(' · '+text('Próg ostrzeżenia','Warning threshold')+' '+w.warning_threshold+'%');}box.append(p);}
   box.append(el('p',text('Nierozstrzygnięte operacje: ','Unresolved operations: ')+a.lifetime_operations.unresolved+' · '+text('Zarezerwowane kredyty: ','Reserved credits: ')+a.lifetime_operations.uncertain_reserved));
   const disclosure=el('details','');disclosure.append(el('summary',text('Zapisz odczyt panelu dostawcy','Record provider panel observation')));
   const form=el('form','');form.className='provider-form';
   const fields={credit_limit:text('Limit kredytów','Credit limit'),used:text('Wykorzystane kredyty','Used credits'),period_start:text('Początek okresu (czas lokalny)','Period start (local time)'),period_end:text('Koniec okresu (czas lokalny)','Period end (local time)'),observed_at:text('Czas odczytu (lokalny)','Observation time (local)')};
   for(const [key,label] of Object.entries(fields)){const l=el('label',label),input=el('input','');input.name=key;input.required=true;input.type=['credit_limit','used'].includes(key)?'number':'datetime-local';if(input.type==='number'){input.min=key==='used'?'0':'1';input.max='1000000000';input.step='1';}l.append(input);form.append(l);}
   form.append(el('p',text('Odczyt jest informacyjny. Nie zwalnia rezerwacji ani nie zmienia limitów CHAOS.','This observation is informational. It does not release reservations or change CHAOS limits.')));
   const button=el('button',text('Zapisz odczyt','Save observation'));button.type='submit';const feedback=el('p','');feedback.setAttribute('role','status');form.append(button,feedback);
   let revision=obs?.revision||0;
   form.onsubmit=async e=>{e.preventDefault();button.disabled=true;feedback.textContent=text('Zapisywanie…','Saving…');
    const data=Object.fromEntries(new FormData(form));for(const k of Object.keys(data))data[k]=['credit_limit','used'].includes(k)?Number(data[k]):Date.parse(data[k])/1000;
    try{const r=await fetch('/api/admin/poi-provider-observation',{method:'POST',headers:{'Content-Type':'application/json','X-Chaos-CSRF':document.getElementById('poi-admin').dataset.csrf},body:JSON.stringify({...data,account:a.account,revision})});const d=await r.json();if(!r.ok||!d.ok)throw Error(d.error||String(r.status));revision=d.observation.revision;feedback.textContent=text('Odczyt zapisany. Odśwież widok, aby zobaczyć nowe dane. Rezerwacje bez zmian.','Observation saved. Refresh to display it. Reservations unchanged.');}catch(err){feedback.textContent=err.message;}finally{button.disabled=false;}
   };disclosure.append(form);box.append(disclosure);target.append(box);
  }
 }
 async function refresh(){const id=++sequence;$('atlas-feedback').textContent=text('Odczyt lokalny…','Reading local data…');
  try{const r=await fetch('/api/admin/poi-world-view?layer='+encodeURIComponent($('atlas-layer').value)+'&empty='+($('atlas-empty').checked?'1':'0')+(queryBounds?'&bbox='+encodeURIComponent(queryBounds.join(',')):''));const d=await r.json();if(!r.ok||!d.ok)throw Error(d.error||String(r.status));if(id!==sequence)return;
   items=d.coverage.items;draw();fit();budgets(d.budgets);metrics(d.metrics);inventory(d.inventory);
   $('atlas-feedback').textContent=text('Widoczne snapshoty: ','Visible snapshots: ')+items.length+' / '+(d.coverage.matching_snapshots??'—')+' · '+text('Ukryte puste: ','Hidden empty: ')+d.coverage.hidden_empty+(d.coverage.truncated?' · '+text('Wynik ograniczony limitem','Result limited'):'')+' · '+text('API dostawców: 0 zapytań','Provider APIs: 0 requests')+(queryBounds?' · '+queryBounds.map(v=>v.toFixed(4)).join(', '):'');
  }catch(e){if(id===sequence)$('atlas-feedback').textContent=e.message;}
 }
 $('atlas-refresh').onclick=refresh;$('atlas-layer').onchange=refresh;$('atlas-empty').onchange=refresh;refresh();
 function inventory(m){const target=$('atlas-inventory');target.replaceChildren();if(!m)return;
  target.append(el('h3',text('Rozmiar i zasoby archiwum','Archive size and resources')));
  if(!m.complete){target.append(el('p',text('Pełny pomiar niedostępny — schemat lub limit czasu.','Complete measurement unavailable — schema or deadline.')));return;}
  target.append(el('p',text('Unikalne obiekty w archiwum: ','Unique retained objects: ')+m.unique_objects),
   el('p',text('Pierwszy zapis w zachowanym archiwum, ostatnie 24 h: ','First seen in retained archive, last 24 h: ')+m.first_seen_retained_24h),
   el('p',text('Baza / WAL: ','Database / WAL: ')+(m.database_bytes/1048576).toFixed(2)+' / '+(m.wal_bytes/1048576).toFixed(2)+' MiB'),
   el('p',text('Wiek oczekiwania kolejki, p95: ','Queue waiting age, p95: ')+(m.queue_p95_wait_seconds===null?'—':m.queue_p95_wait_seconds+' s')),
   el('p',text('Retencja usuwa historię. Ten pomiar nie jest przyrostem całego świata od początku projektu.','Retention removes history. This is not lifetime world growth.')));
 }
 function metrics(m){const target=$('atlas-metrics');target.replaceChildren();
  target.append(el('h3',text('Statystyki skanera POI','POI scanner statistics')));
  if(!m.prepared){target.append(el('p',text('Schemat statystyk nieprzygotowany.','Metrics schema not prepared.')));return;}
  const ratio=v=>v===null?text('brak próbek','no samples'):(100*v).toFixed(1)+'%';
  target.append(el('p',new Date(m.window_start*1000).toLocaleString()+' — '+new Date(m.window_end*1000).toLocaleString()),
   el('p',text('Próby / sukcesy / błędy: ','Attempts / successes / errors: ')+`${m.attempts} / ${m.successful} / ${m.errors}`),
   el('p',text('Sukcesy z repozytorium bez sieci: ','Successful world-only scans: ')+ratio(m.world_local_scan_ratio)),
   el('p',text('Sukcesy z udziałem sieci: ','Successful scans involving network: ')+ratio(m.network_scan_ratio)),
   el('p',text('Źródła udanych wyników: ','Successful result sources: ')+Object.entries(m.sources||{}).map(([source,count])=>({world:text('Archiwum świata','World archive'),fresh:text('Pamięć podręczna','Cache'),upstream:text('Dostawca API','Provider API'),network:text('Sieć','Network')}[source]||source)+': '+count).join(' · ')),
   el('p',text('Puste sukcesy / próby transportu: ','Empty successes / transport attempts: ')+`${m.empty_successes} / ${m.transport_attempts}`),
   el('p',text('Górna granica przedziału p50 / p95 [s]: ','Histogram upper bound p50 / p95 [s]: ')+`${m.latency_p50_upper_seconds??'—'} / ${m.latency_p95_upper_seconds??'—'}`),
   el('p',text('Wyniki pobrania POI, przed generowaniem scen gry. Puste wyniki liczą się jako sukces. Bez workera i diagnostyki.','POI retrieval outcomes, before gameplay scene generation. Empty results count as success. Excludes background and probes.')));
 }
})();
