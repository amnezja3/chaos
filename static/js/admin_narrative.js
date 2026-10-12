(() => {
 'use strict';
 const panel=document.getElementById('narrative-panel'), form=document.getElementById('provider-form');
 const en=panel.dataset.locale==='en';
 const words={
  title:['Modele narracji','Narrative models'], intro:['Klucz API jest sekretem serwera. Fallback na Ollamę jest automatyczny. Zmiany dotyczą kolejnych zadań.','The API key is a server secret. Ollama fallback is automatic. Changes apply to subsequent tasks.'],
  primary:['Główny dostawca','Primary provider'],model:['Model Mistrala','Mistral model'],remote:['Limit Mistrala (s)','Mistral deadline (s)'],total:['Limit całej generacji (s)','Total generation deadline (s)'],tokens:['Maks. tokenów odpowiedzi','Maximum output tokens'],budget:['Dzienny budżet tokenów UTC (0 = bez limitu)','Daily UTC token budget (0 = unlimited)'],save:['Zapisz konfigurację','Save configuration'],refresh:['Odśwież','Refresh'],models:['Pobierz modele','Fetch models'],health:['Sprawdź obu dostawców','Check provider health'],probe:['Sprawdź i odblokuj Mistrala','Probe and recover Mistral'],generate:['Test generacji Mistrala (bez publikacji)','Test Mistral generation (no publication)'],history:['Ostatnie próby generacji','Recent generation attempts'],loading:['Trwa operacja…','Working…'],saved:['Zapisano. Nowe zadania użyją tej konfiguracji.','Saved. New tasks will use this configuration.'],ready:['Gotowe','Ready'],configured:['ustawiony','configured'],missing:['brak','missing'],secret:['Sekret','Secret'],revision:['Rewizja','Revision'],used:['Ostatnio używany','Last used'],circuit:['Wstrzymanie Mistrala','Mistral circuit'],until:['do','until'],closed:['nieaktywne','closed'],empty:['Brak prób generacji.','No generation attempts.'],error:['Błąd','Error'],conflict:['Konfiguracja została zmieniona w innym oknie. Odśwież przed zapisem.','Configuration changed in another window. Refresh before saving.'],date:['Czas','Time'],provider:['Dostawca','Provider'],status:['Wynik','Result'],duration:['Czas (ms)','Duration (ms)'],published:['Opublikowano','Published'],no:['nie','no'],healthy:['dostępny','available'],unhealthy:['niedostępny','unavailable'],completed:['zakończono','completed'],failed:['niepowodzenie','failed'],started:['rozpoczęto','started'],concurrency:['Współbieżność na dostawcę','Concurrency per provider']};
 const t=k=>(words[k]||[k,k])[en?1:0], node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
 panel.querySelectorAll('[data-copy]').forEach(n=>n.textContent=t(n.dataset.copy));
 let revision=0;
 const status=document.getElementById('provider-status'), health=document.getElementById('provider-health');
 async function request(action,config){
  const response=await fetch('/api/admin/narrative-providers',{cache:'no-store',...(action==='status'?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...(config?{config}:{})})})});
  const data=await response.json();if(!response.ok||!data.success)throw Error(data.error==='revision_conflict'?t('conflict'):`${t('error')}: ${data.error||response.status}`);return data;
 }
 function fill(data){
  revision=data.config.revision;
  const select=form.elements.model;select.replaceChildren(new Option(data.config.model||'—',data.config.model));
  Object.entries(data.config).forEach(([k,v])=>{if(form.elements[k])form.elements[k].value=v;});
  document.getElementById('provider-meta').textContent=`${t('secret')}: ${t(data.secret_configured?'configured':'missing')} · ${t('revision')}: ${revision} · ${data.endpoint} · ${t('used')}: ${data.last_provider||'—'} · ${t('concurrency')}: 1 · ${t('circuit')}: ${data.circuit.until_at>Date.now()/1000?`${data.circuit.code} ${t('until')} ${new Date(data.circuit.until_at*1000).toLocaleString(en?'en-GB':'pl-PL')}`:t('closed')}`;
  const list=document.getElementById('provider-calls');list.replaceChildren();
  if(!data.calls.length){list.append(node('p',t('empty')));return;}
  const table=document.createElement('table'), head=document.createElement('tr');
  ['date','provider','model','status','duration','error'].forEach(k=>head.append(node('th',t(k))));table.append(head);
  data.calls.forEach(c=>{const tr=document.createElement('tr');[new Date(c.started_at*1000).toLocaleString(en?'en-GB':'pl-PL'),c.provider,c.model,t(c.status),c.duration_ms,c.error_code||'—'].forEach(v=>tr.append(node('td',v)));table.append(tr);});list.append(table);
 }
 async function perform(action,config){
  panel.querySelectorAll('button').forEach(n=>n.disabled=true);status.textContent=t('loading');
  try{const data=await request(action,config);
   if(action==='status')fill(data);
   if(action==='save'){fill(await request('status'));status.textContent=t('saved');return;}
   if(action==='models'){const select=form.elements.model, old=select.value;select.replaceChildren(new Option('—',''));data.models.forEach(m=>select.add(new Option(m,m)));select.value=old;}
   if(data.health){const states=data.health.providers||{mistral:data.health};health.textContent=Object.entries(states).map(([k,v])=>`${k}: ${t(v.ok?'healthy':'unhealthy')} ${(v.errors||[]).join(', ')}`).join(' · ');}
   if(data.diagnostic)health.textContent=`Mistral: ${data.diagnostic.model} · ${data.diagnostic.validation_status} ${(data.diagnostic.errors||[]).join(', ')} · ${t('published')}: ${t('no')}`;
   status.textContent=t('ready');
  }catch(error){status.textContent=error.message;}finally{panel.querySelectorAll('button').forEach(n=>n.disabled=false);}
 }
 form.addEventListener('submit',e=>{e.preventDefault();const config={revision};new FormData(form).forEach((v,k)=>config[k]=['primary','model'].includes(k)?v:Number(v));perform('save',config);});
 document.getElementById('provider-actions').addEventListener('click',e=>{if(e.target.dataset.action)perform(e.target.dataset.action);});
 perform('status');
})();
