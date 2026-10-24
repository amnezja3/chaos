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
 const t=k=>labels[k]?.[pl?0:1]||k;
 root.querySelectorAll('[data-copy]').forEach(e=>e.textContent=t(e.dataset.copy));
 let providers=[];
 const node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
 function renderWorld(w){
  if(!w)return;
  const summary=document.getElementById('poi-world-summary');summary.replaceChildren();
  summary.append(node('p',t(w.world_prepared?'worldReady':'worldMissing')),
   node('p',`${t('snapshots')}: ${w.snapshots} · ${t('canonical')}: ${w.canonical_snapshots} · ${(w.payload_bytes/1048576).toFixed(2)} MiB`),
   node('p',`fresh: ${w.fresh} · stale: ${w.stale} · expired: ${w.expired}`),
   node('p',`${t('ingest')}: ${w.ingest_enabled?'ON':'OFF'} · ${t('read')}: ${w.read_enabled?'ON':'OFF'} · discovery: ${w.discovery_mode}`),
   node('p',pl?'Stan procesu pobierania w tle: niepotwierdzony.':'Background process status: unverified.'));
  const jobs=w.jobs;
  if(jobs){
   const queue=node('section');queue.id='poi-job-summary';
   queue.append(node('h3',pl?'Kolejka discovery':'Discovery queue'));
   queue.append(node('p',jobs.prepared?(pl?'Schemat kolejki gotowy.':'Queue schema ready.'):(pl?'Schemat kolejki nieprzygotowany.':'Queue schema not prepared.')));
   queue.append(node('p',`${pl?'Zadania':'Jobs'}: ${jobs.total} · ${pl?'Gotowe czasowo':'Ready by time'}: ${jobs.ready_by_time} · ${pl?'Nierozstrzygnięte':'Unresolved'}: ${jobs.unresolved}`));
   queue.append(node('p',`${pl?'Wygasłe oczekujące':'Expired waiting'}: ${jobs.expired_waiting} · ${pl?'Wygasłe dzierżawy':'Expired leases'}: ${jobs.expired_leases}`));
   queue.append(node('p',pl?'Gotowość czasowa nie oznacza zgody na pobranie. Widok nie uruchamia zadań.':'Time readiness is not permission to fetch. This view does not start jobs.'));
   const recent=node('ul');
   for(const job of jobs.recent||[])recent.append(node('li',`${job.provider} / ${job.profile}: ${job.state} · ${pl?'Próby':'Attempts'}: ${job.attempts}${job.reason?' · '+job.reason:''}`));
   if(!jobs.total)recent.append(node('li',pl?'Brak zadań.':'No jobs.'));
   queue.append(recent);summary.append(queue);
  }
  const budgets=document.getElementById('poi-world-budget');budgets.replaceChildren();
  for(const b of w.budget_windows||[])budgets.append(node('p',`${t('credits')} · ${b.period}: ${b.committed} / ${b.credit_limit}`));
  const demand=w.demand||{pending:0,cells:[],layers:{}};
  document.getElementById('poi-demand-summary').textContent=`${t('pending')}: ${demand.pending} · `+Object.entries(demand.layers).map(([k,v])=>`${k}: ${v}`).join(' · ');
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
   const card=node('section');card.className='panel';
   card.append(node('h3',p.name+' / '+p.id),node('p',p.url),node('p',p.technical_status+' · '+p.policy_status),node('p',p.scopes.join(', ')||'—'));
   if(p.evidence)card.append(node('p',p.evidence.source_url),node('p',p.evidence.reference),node('p',p.evidence.notes),node('p',p.evidence.checked_by+' · '+new Date(p.evidence.checked_at*1000).toLocaleString()),node('p',t('review')+': '+new Date(p.review_due_at*1000).toLocaleDateString()));
   const feedback=node('p');feedback.setAttribute('role','status');feedback.dataset.provider=p.id;
   const edit=node('button',t('edit'));edit.type='button';edit.onclick=()=>{const f=document.getElementById('poi-form');for(const k of ['id','name','url','operator_group','priority'])f.elements[k].value=p[k];document.getElementById('poi-decision').elements.id.value=p.id;f.scrollIntoView({block:'start'});};card.append(edit);
   for(const type of ['probe','enable']){const b=node('button',t(type==='enable'?(p.enabled?'disable':'enable'):type));b.type='button';
    if(type==='probe'&&['https://api.maplark.com/v3/osm_features','https://api.geoapify.com/v2/places'].includes(p.url)){
     b.disabled=true;b.textContent=pl?'Test API przez ograniczone narzędzie CLI':'API test through bounded CLI';
    }else b.onclick=()=>action(b,feedback,{action:type,id:p.id,revision:p.revision,...(type==='enable'?{enabled:!p.enabled}:{})});card.append(b);}
   card.append(feedback);list.append(card);
  }
  const health=document.getElementById('poi-health');health.replaceChildren();
  for(const h of data.health)health.append(node('p',`${h.provider_id} · ${h.kind} · ${h.status} · ${h.latency.toFixed(2)} s · ${new Date(h.at*1000).toLocaleString()}`));
  if(!data.health.length)health.textContent=t('empty');
  const audit=document.getElementById('poi-audit');audit.replaceChildren();
  for(const a of data.audit||[])audit.append(node('p',`${a.provider_id} · ${a.action} · ${a.actor} · ${new Date(a.at*1000).toLocaleString()}`));
 }
 document.getElementById('poi-refresh').onclick=()=>refresh().catch(e=>document.getElementById('poi-status').textContent=e.message);
 document.getElementById('poi-form').onsubmit=e=>{e.preventDefault();const f=e.target,d=new FormData(f),id=d.get('id');action(f.querySelector('button'),f.querySelector('.poi-feedback'),{action:'save',id,revision:providers.find(p=>p.id===id)?.revision||0,fields:{name:d.get('name'),url:d.get('url'),operator_group:d.get('operator_group'),priority:Number(d.get('priority'))}});};
 document.getElementById('poi-decision').onsubmit=e=>{e.preventDefault();const f=e.target,d=new FormData(f),id=d.get('id');action(f.querySelector('button'),f.querySelector('.poi-feedback'),{action:'decision',id,revision:providers.find(p=>p.id===id)?.revision||0,policy:d.get('policy'),scopes:d.getAll('scope'),evidence:{source_url:d.get('source_url'),reference:d.get('reference'),notes:d.get('notes')},review_due_at:Date.parse(d.get('review')+'T23:59:59Z')/1000});};
 root.querySelectorAll('button[disabled]').forEach(b=>b.disabled=false);
 root.dataset.ready='true';
 refresh().catch(e=>document.getElementById('poi-status').textContent=e.message);
})();
