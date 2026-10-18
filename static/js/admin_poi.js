(function(){
 'use strict';
 const root=document.getElementById('poi-admin'); if(!root)return;
 const pl=root.dataset.locale!=='en';
 const labels={
  intro:['Dostępność techniczna i dopuszczenie źródła są oceniane osobno. Odświeżenie panelu nie wywołuje Overpass.','Technical availability and provider approval are separate. Refreshing this panel does not call Overpass.'],
  refresh:['Odśwież stan','Refresh status'],edit:['Dodaj / edytuj źródło','Add / edit provider'],name:['Nazwa','Name'],group:['Grupa operatora','Operator group'],priority:['Priorytet','Priority'],save:['Zapisz kandydata','Save candidate'],decision:['Decyzja o zakresie użycia','Usage scope decision'],scopeHint:['Wybierz zapisane źródło. Zgoda na probe nie oznacza zgody na skany ani trwały zapis. Decyzja nie włącza źródła.','Select a saved provider. Probe approval does not approve scans or storage. A decision does not enable the provider.'],policy:['Warunki','Policy'],scopes:['Dozwolony zakres','Allowed scopes'],source:['Adres źródła warunków','Terms source URL'],reference:['Referencja dowodu','Evidence reference'],notes:['Uzasadnienie','Notes'],review:['Następny przegląd','Next review'],saveDecision:['Zapisz decyzję','Save decision'],health:['Ostatnie obserwacje','Recent observations'],probe:['Sprawdź interpreter','Probe interpreter'],enable:['Włącz','Enable'],disable:['Wyłącz','Disable'],saved:['Zapisano.','Saved.'],loading:['Przetwarzanie…','Processing…'],empty:['Brak danych.','No data.']
 };
 Object.assign(labels,{
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
 const t=k=>labels[k]?.[pl?0:1]||k;
 root.querySelectorAll('[data-copy]').forEach(e=>e.textContent=t(e.dataset.copy));
 let providers=[];
 const node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
 async function call(body){
  const response=await fetch('/api/admin/poi-providers',{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Chaos-CSRF':root.dataset.csrf}:{},body:body?JSON.stringify(body):undefined});
  const data=await response.json();if(!response.ok||!data.ok)throw Error(t(data.error||String(response.status)));return data;
 }
 async function action(button,output,body){button.disabled=true;output.textContent=t('loading');try{await call(body);const provider=output.dataset.provider;await refresh();if(provider)output=root.querySelector('[data-provider="'+provider+'"]')||output;output.textContent=t('saved');}catch(e){output.textContent=e.message;}finally{button.disabled=false;}}
 async function refresh(){
  const data=await call();providers=data.providers;
  const list=document.getElementById('poi-providers');list.replaceChildren();
  if(!providers.length)list.textContent=t('empty');
  for(const p of providers){
   const card=node('section');card.className='panel';
   card.append(node('h3',p.name+' / '+p.id),node('p',p.url),node('p',p.technical_status+' · '+p.policy_status),node('p',p.scopes.join(', ')||'—'));
   if(p.evidence)card.append(node('p',p.evidence.source_url),node('p',p.evidence.reference),node('p',p.evidence.notes),node('p',p.evidence.checked_by+' · '+new Date(p.evidence.checked_at*1000).toLocaleString()),node('p',t('review')+': '+new Date(p.review_due_at*1000).toLocaleDateString()));
   const feedback=node('p');feedback.setAttribute('role','status');feedback.dataset.provider=p.id;
   const edit=node('button',t('edit'));edit.type='button';edit.onclick=()=>{const f=document.getElementById('poi-form');for(const k of ['id','name','url','operator_group','priority'])f.elements[k].value=p[k];document.getElementById('poi-decision').elements.id.value=p.id;f.scrollIntoView({block:'start'});};card.append(edit);
   for(const type of ['probe','enable']){const b=node('button',t(type==='enable'?(p.enabled?'disable':'enable'):type));b.type='button';b.onclick=()=>action(b,feedback,{action:type,id:p.id,revision:p.revision,...(type==='enable'?{enabled:!p.enabled}:{})});card.append(b);}
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
