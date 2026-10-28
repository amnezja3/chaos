(function(){
 'use strict';
 const root=document.getElementById('poi-admin'); if(!root)return;
 const pl=root.dataset.locale!=='en';
 const labels={
  intro:['Dostępność techniczna i dopuszczenie źródła są oceniane osobno. Odświeżenie panelu nie wywołuje Overpass.','Technical availability and provider approval are separate. Refreshing this panel does not call Overpass.'],
  refresh:['Odśwież stan','Refresh status'],edit:['Dodaj / edytuj źródło','Add / edit provider'],name:['Nazwa','Name'],group:['Grupa operatora','Operator group'],priority:['Priorytet','Priority'],save:['Zapisz kandydata','Save candidate'],decision:['Decyzja o zakresie użycia','Usage scope decision'],scopeHint:['Wybierz zapisane źródło. Zgoda na probe nie oznacza zgody na skany ani trwały zapis. Decyzja nie włącza źródła.','Select a saved provider. Probe approval does not approve scans or storage. A decision does not enable the provider.'],policy:['Warunki','Policy'],scopes:['Dozwolony zakres','Allowed scopes'],source:['Adres źródła warunków','Terms source URL'],reference:['Referencja dowodu','Evidence reference'],notes:['Uzasadnienie','Notes'],review:['Następny przegląd','Next review'],saveDecision:['Zapisz decyzję','Save decision'],health:['Ostatnie obserwacje','Recent observations'],probe:['Sprawdź interpreter','Probe interpreter'],enable:['Włącz','Enable'],disable:['Wyłącz','Disable'],saved:['Zapisano.','Saved.'],loading:['Przetwarzanie…','Processing…'],empty:['Brak danych.','No data.']
 };
 Object.assign(labels,{
  worldHint:['Zapis świata wymaga osobnej zgody world_storage. Ten widok nie uruchamia pobierania danych.','World storage requires separate world_storage approval. This view does not fetch provider data.'],
  demandTitle:['Zapotrzebowanie na regiony','Regional demand'],
  demandHint:['Sektory zainteresowania graczy, nie dowód pokrycia. Do 100 ostatnich sektorów; bez tras i identyfikatorów graczy.','Player demand sectors, not coverage evidence. Up to 100 recent sectors; no player routes or identifiers.'],
  worldReady:['Magazyn przygotowany','Storage prepared'],worldMissing:['Magazyn nieprzygotowany','Storage not prepared'],
  snapshots:['Snapshoty','Snapshots'],canonical:['Kanoniczne','Canonical'],ingest:['Zapis','Ingest'],read:['Odczyt','Read'],
  pending:['Oczekujące warstwy regionów','Pending region layers'],backgroundOff:['Pobieranie w tle: wyłączone','Background fetching: disabled'],
  credits:['Kredyty: wykorzystane / limit','Credits: committed / limit'],extent:['Zakres widoku (lon, lat)','View extent (lon, lat)'],
  audit:['Historia zmian','Change history'],
  provider_not_approved:['Źródło wymaga poprawnego testu i zatwierdzenia zakresu użycia.','The provider needs a successful test and approved usage scope.'],
  provider_probe_not_approved:['Najpierw zatwierdź zakres small_probe na podstawie warunków dostawcy.','Approve the small_probe scope based on provider terms first.'],
  provider_revision_conflict:['Konfiguracja zmieniła się. Odśwież panel i spróbuj ponownie.','Configuration changed. Refresh the panel and try again.'],
  provider_invalid_url:['Podaj poprawny adres HTTPS endpointu interpreter.','Enter a valid HTTPS interpreter endpoint.'],
  provider_invalid_review_date:['Wybierz datę przeglądu w ciągu najbliższego roku.','Choose a review date within the next year.'],
  probe_rate_limited:['Test był niedawno uruchomiony. Obowiązuje odstęp 15 minut.','A probe was recently requested. The interval is 15 minutes.'],
  circuit_open:['Źródło jest w okresie oczekiwania. Test nie omija tej blokady.','The provider is cooling down. Probes do not bypass this block.'],
  upstream_busy:['Trwa inne zapytanie. Spróbuj później.','Another request is running. Try later.']
 });
 Object.assign(labels,{
  priority:['Priorytet listy (hierarchia jest ustawiana osobno)','List priority (hierarchy is configured separately)'],
  intro:['Test techniczny, dopuszczenie źródła i zgodność profilu są oceniane osobno. Odświeżenie panelu nie odpytuje dostawców.','Technical tests, usage approval and profile compatibility are separate. Refreshing this panel does not query providers.'],
  feature_budgeted_probe_required:['To API wymaga ograniczonego testu CLI z budżetem.','This API requires a bounded CLI test with a budget.']
 });
 Object.assign(labels,{
  untested:['Nieprzetestowany','Not tested'],tested_ok:['Test poprawny','Test passed'],tested_failed:['Test nieudany','Test failed'],
  unknown:['Nieustalone','Not established'],public_declaration_only:['Deklaracja publiczna','Public declaration'],operator_confirmation_pending:['Oczekuje na potwierdzenie','Awaiting confirmation'],approved_for_defined_use:['Zatwierdzony zakres','Approved scope'],restricted:['Ograniczony','Restricted'],rejected:['Odrzucony','Rejected'],expired_review:['Przegląd wygasł','Review expired'],
  small_probe:['Mały test połączenia','Small diagnostic probe'],normal_scan:['Skan gracza','Player scan'],wide_fetch:['Pobieranie rozszerzone','Wide fetch'],background_refresh:['Pobieranie w tle','Background collection'],storage:['Pamięć podręczna','Response cache'],world_storage:['Archiwum geometrii świata','World geometry archive'],
  network_failed:['Nie udało się połączyć ze źródłem.','Could not connect to the provider.'],http_read_timeout:['Przekroczono czas oczekiwania na odpowiedź.','Provider response timed out.'],
  roads:['Drogi','Roads'],waterways:['Rzeki i kanały','Rivers and canals'],inland_water:['Jeziora i zbiorniki','Lakes and reservoirs'],coastline:['Wybrzeża','Coastlines'],land_water:['Ląd i morze','Land and sea'],poi:['Punkty zainteresowania','Points of interest'],
  COMMITTED:['Zapisane','Stored'],FAILED_TERMINAL:['Próba zakończona błędem','Attempt failed'],PENDING:['Oczekuje','Pending'],POLICY_BLOCKED:['Wstrzymane','On hold']
 });
 const t=k=>labels[k]?.[pl?0:1]||k;
 root.querySelectorAll('#poi-decision option').forEach(o=>{const value=o.value;o.value=value;o.textContent=t(value);});
 root.querySelectorAll('#poi-decision input[name=scope]').forEach(input=>{input.parentElement.lastChild.textContent=t(input.value);input.title=t(input.value);});
 root.querySelectorAll('[data-copy]').forEach(e=>e.textContent=t(e.dataset.copy));
 let providers=[];
 const node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
 function table(target,headers,rows){target.replaceChildren();if(!rows.length){target.append(node('p',t('empty')));return;}const grid=node('table'),head=node('thead'),body=node('tbody'),hr=node('tr');headers.forEach(label=>{const cell=node('th',label);cell.scope='col';hr.append(cell);});head.append(hr);for(const values of rows){const row=node('tr');values.forEach(value=>row.append(node('td',value)));body.append(row);}grid.append(head,body);target.append(grid);}
 function renderWorld(w){
  if(!w)return;
  const summary=document.getElementById('poi-world-summary');summary.replaceChildren();
  summary.append(node('p',t(w.world_prepared?'worldReady':'worldMissing')),
   node('p',`${t('snapshots')}: ${w.snapshots} · ${t('canonical')}: ${w.canonical_snapshots} · ${(w.payload_bytes/1048576).toFixed(2)} MiB`),
   node('p',`${pl?'Świeże':'Fresh'}: ${w.fresh} · ${pl?'Starsze':'Stale'}: ${w.stale} · ${pl?'Wygasłe':'Expired'}: ${w.expired}`),
   node('p',`${pl?'Zapis ze skanera':'Scanner ingest'}: ${w.ingest_enabled?'ON':'OFF'} · ${pl?'Odczyt świata przez skaner':'Scanner world read'}: ${w.read_enabled?'ON':'OFF'} · ${pl?'Zapotrzebowanie':'Demand'}: ${w.discovery_mode==='passive'?(pl?'zbierane pasywnie':'collected passively'):w.discovery_mode}`),
   node('p',pl?'Zebrane obserwacje i aktualne pokrycie skanera są rozliczane osobno.':'Collected observations and current scanner coverage are tracked separately.'));
  const jobs=w.jobs;
  if(jobs){
   const queue=node('section');queue.id='poi-job-summary';
   const heartbeat=jobs.heartbeat;
   if(heartbeat){
    const states=pl?{running:'Pracuje',waiting:'Oczekuje',stopped:'Zatrzymany',error:'Zakończył się błędem',unknown:'Brak aktualnego sygnału'}:{running:'Working',waiting:'Waiting',stopped:'Stopped',error:'Exited with error',unknown:'No current signal'};
    const live=node('p',(pl?'Kolektor (stan przy odczycie): ':'Collector (state when loaded): ')+(states[heartbeat.status]||states.unknown));live.id='poi-worker-heartbeat';
    if(heartbeat.observed_at)live.append(' · '+(pl?'Ostatni sygnał: ':'Last signal: ')+new Date(heartbeat.observed_at*1000).toLocaleString());
    live.title=pl?'Sygnał życia procesu, niezależny od wyniku pobrania. Wygasły sygnał nie potwierdza pracy kolektora.':'Process liveness, independent of fetch outcomes. An expired signal does not confirm a running collector.';
    queue.append(live);
   }
   queue.append(node('h3',pl?'Kolejka discovery':'Discovery queue'));
   queue.append(node('p',jobs.prepared?(pl?'Schemat kolejki gotowy.':'Queue schema ready.'):(pl?'Schemat kolejki nieprzygotowany.':'Queue schema not prepared.')));
   queue.append(node('p',`${pl?'Zadania':'Jobs'}: ${jobs.total} · ${pl?'Gotowe czasowo':'Ready by time'}: ${jobs.ready_by_time} · ${pl?'Nierozstrzygnięte':'Unresolved'}: ${jobs.unresolved}`));
   queue.append(node('p',`${pl?'Wygasłe oczekujące':'Expired waiting'}: ${jobs.expired_waiting} · ${pl?'Wygasłe dzierżawy':'Expired leases'}: ${jobs.expired_leases}`));
   queue.append(node('p',pl?'Gotowość czasowa nie oznacza zgody na pobranie. Widok nie uruchamia zadań.':'Time readiness is not permission to fetch. This view does not start jobs.'));
   const recent=node('ul');
   for(const job of jobs.recent||[])recent.append(node('li',`${job.provider} / ${t(job.profile)}: ${t(job.state)} · ${pl?'Próby':'Attempts'}: ${job.attempts}${job.reason?' · '+t(job.reason):''}`));
   if(!jobs.total)recent.append(node('li',pl?'Brak zadań.':'No jobs.'));
   queue.append(recent);summary.append(queue);
  }
  const budgets=document.getElementById('poi-world-budget');budgets.replaceChildren();
  const policy=node('p',pl?'Archiwum geografii: 7 dni. Pełne POI: odświeżenie najwyżej raz na godzinę, po nowej wizycie lub skanie. Świeżość skanera: 5 minut; dane starsze: do 30 minut.':'Geography archive: 7 days. Full POI: refresh at most hourly after a new visit or scan. Scanner freshness: 5 minutes; stale data: up to 30 minutes.');
  policy.id='poi-refresh-policy';budgets.append(policy);
  for(const [account,b] of Object.entries(w.background_budgets||{})){
   if(!b)continue;
   const line=node('p',`${account} · ${pl?'Budżet tła':'Background budget'}: ${b.committed} / ${b.credit_limit} · ${pl?'Pozostało':'Remaining'}: ${b.remaining}`);
   line.title=pl?'Osobny podlimit kolektora w ramach budżetu konta. Wolne środki konta nie zwiększają tego limitu.':'Separate collector allowance within the account budget. Remaining account credits do not increase this limit.';
   budgets.append(line);
  }
  for(const b of w.budget_windows||[])budgets.append(node('p',`${t('credits')} · ${b.period}: ${b.committed} / ${b.credit_limit}`));
  const demand=w.demand||{pending:0,cells:[],layers:{}};
  document.getElementById('poi-demand-summary').textContent=`${t('pending')}: ${demand.pending} · `+Object.entries(demand.layers).map(([k,v])=>`${t(k)}: ${v}`).join(' · ');
  const svg=document.getElementById('poi-demand-map');svg.replaceChildren();svg.setAttribute('aria-label',t('demandTitle'));
  const extent=document.getElementById('poi-demand-extent');
  if(!demand.cells.length){extent.textContent=t('empty');return;}
  const xs=demand.cells.map(c=>c.cell_x),ys=demand.cells.map(c=>c.cell_y);
  const minX=Math.min(...xs)-1,maxX=Math.max(...xs)+2,minY=Math.min(...ys)-1,maxY=Math.max(...ys)+2;
  for(const c of demand.cells){
   const r=document.createElementNS('http://www.w3.org/2000/svg','rect');
   r.setAttribute('x',20+(c.cell_x-minX)/(maxX-minX)*600);
   r.setAttribute('y',220-(c.cell_y-minY+1)/(maxY-minY)*200);
   r.setAttribute('width',Math.max(2,600/(maxX-minX)));r.setAttribute('height',Math.max(2,200/(maxY-minY)));
   r.setAttribute('fill','#43ffa1');r.setAttribute('opacity','.65');
   const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=`${c.cell_x/100}, ${c.cell_y/100} · ${c.layers} layers · ${c.hits} demands`;
   r.append(title);svg.append(r);
  }
  extent.textContent=`${t('extent')}: ${(minX/100).toFixed(2)}, ${(minY/100).toFixed(2)} — ${(maxX/100).toFixed(2)}, ${(maxY/100).toFixed(2)}`;
 }
 async function call(body){
  const response=await fetch('/api/admin/poi-providers',{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Chaos-CSRF':root.dataset.csrf}:{},body:body?JSON.stringify(body):undefined});
  const data=await response.json();if(!response.ok||!data.ok)throw Error(t(data.error||String(response.status)));return data;
 }
 async function action(button,output,body){button.disabled=true;output.textContent=t('loading');try{await call(body);const provider=output.dataset.provider;await refresh();if(provider)output=root.querySelector('[data-provider="'+provider+'"]')||output;output.textContent=t('saved');}catch(e){output.textContent=e.message;}finally{button.disabled=false;}}
 async function refresh(){
  const data=await call();providers=data.providers;
  renderWorld(data.world);
  const list=document.getElementById('poi-providers');list.replaceChildren();
  if(!providers.length)list.textContent=t('empty');
  for(const p of providers){
   const card=node('section');card.className='ops-card';
   card.append(node('h3',p.name));
   for(const [label,tone] of [[p.enabled?(pl?'Włączony':'Enabled'):(pl?'Wyłączony':'Disabled'),p.enabled?'ok':'off'],[t(p.technical_status),p.technical_status==='tested_ok'?'ok':'warning']]){const badge=node('span',label);badge.className='ops-badge';badge.dataset.tone=tone;card.append(badge);}
   card.append(node('p',t(p.policy_status)),node('p',p.scopes.map(t).join(' · ')||(pl?'Brak dopuszczonego zakresu':'No approved scope')));
   const details=node('details');details.append(node('summary',pl?'Dane źródła i warunki':'Source details and terms'),node('p',p.id),node('p',p.url));
   if(p.evidence)details.append(node('p',p.evidence.source_url),node('p',p.evidence.reference),node('p',p.evidence.notes),node('p',p.evidence.checked_by+' · '+new Date(p.evidence.checked_at*1000).toLocaleString()),node('p',t('review')+': '+new Date(p.review_due_at*1000).toLocaleDateString()));
   card.append(details);const actions=node('div');actions.className='ops-actions';card.append(actions);
   const feedback=node('p');feedback.setAttribute('role','status');feedback.dataset.provider=p.id;
   const edit=node('button',t('edit'));edit.type='button';edit.title=pl?'Edytuj adres i parametry źródła':'Edit source endpoint and settings';edit.onclick=()=>{const f=document.getElementById('poi-form');for(const k of ['id','name','url','operator_group','priority'])f.elements[k].value=p[k];document.getElementById('poi-decision').elements.id.value=p.id;document.getElementById('provider-editor').open=true;f.scrollIntoView({block:'center'});f.elements.name.focus({preventScroll:true});};actions.append(edit);
   const decision=node('button',pl?'Zakres użycia':'Usage scope');decision.type='button';decision.onclick=()=>{const f=document.getElementById('poi-decision');f.elements.id.value=p.id;f.elements.policy.value=p.policy_status;for(const input of f.querySelectorAll('[name=scope]'))input.checked=p.scopes.includes(input.value);for(const key of ['source_url','reference','notes'])f.elements[key].value=p.evidence?.[key]||'';f.elements.review.value=p.review_due_at?new Date(p.review_due_at*1000).toISOString().slice(0,10):'';document.getElementById('provider-permissions').open=true;f.scrollIntoView({block:'center'});f.elements.policy.focus({preventScroll:true});};actions.append(decision);
   for(const type of ['probe','enable']){const b=node('button',t(type==='enable'?(p.enabled?'disable':'enable'):type));b.type='button';
    if(type==='probe'&&['https://api.maplark.com/v3/osm_features','https://api.geoapify.com/v2/places'].includes(p.url)){
     b.disabled=true;b.textContent=pl?'Test API przez ograniczone narzędzie CLI':'API test through bounded CLI';
    }else b.onclick=()=>action(b,feedback,{action:type,id:p.id,revision:p.revision,...(type==='enable'?{enabled:!p.enabled}:{})});b.title=type==='probe'?(pl?'Wykonuje zapytanie do dostawcy. Obowiązuje limit testów.':'Makes a provider request. Probe rate limits apply.'):(pl?'Zmienia dostępność w zatwierdzonym zakresie.':'Changes availability within the approved scope.');actions.append(b);}
   card.append(feedback);list.append(card);
  }
  table(document.getElementById('poi-health'),[pl?'Źródło':'Provider',pl?'Operacja':'Operation',pl?'Wynik':'Result',pl?'Czas':'Duration',pl?'Data':'Date'],data.health.map(h=>[h.provider_id,t(h.kind),t(h.status),h.latency.toFixed(2)+' s',new Date(h.at*1000).toLocaleString()]));
  table(document.getElementById('poi-audit'),[pl?'Źródło':'Provider',pl?'Zmiana':'Change',pl?'Operator':'Actor',pl?'Data':'Date'],(data.audit||[]).map(a=>[a.provider_id,t(a.action),a.actor,new Date(a.at*1000).toLocaleString()]));
 }
 document.getElementById('poi-refresh').onclick=async event=>{const button=event.currentTarget,output=document.getElementById('poi-status');button.disabled=true;output.textContent=t('loading');try{await refresh();output.textContent=pl?'Stan odświeżony.':'Status refreshed.';}catch(e){output.textContent=e.message;}finally{button.disabled=false;}};
 document.getElementById('poi-form').onsubmit=e=>{e.preventDefault();const f=e.target,d=new FormData(f),id=d.get('id');action(f.querySelector('button'),f.querySelector('.poi-feedback'),{action:'save',id,revision:providers.find(p=>p.id===id)?.revision||0,fields:{name:d.get('name'),url:d.get('url'),operator_group:d.get('operator_group'),priority:Number(d.get('priority'))}});};
 document.getElementById('poi-decision').onsubmit=e=>{e.preventDefault();const f=e.target,d=new FormData(f),id=d.get('id');action(f.querySelector('button'),f.querySelector('.poi-feedback'),{action:'decision',id,revision:providers.find(p=>p.id===id)?.revision||0,policy:d.get('policy'),scopes:d.getAll('scope'),evidence:{source_url:d.get('source_url'),reference:d.get('reference'),notes:d.get('notes')},review_due_at:Date.parse(d.get('review')+'T23:59:59Z')/1000});};
 root.querySelectorAll('button[disabled]').forEach(b=>b.disabled=false);
 root.dataset.ready='true';
 refresh().catch(e=>document.getElementById('poi-status').textContent=e.message);
})();
