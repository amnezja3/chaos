(function () {
 'use strict';
 const root=document.getElementById('poi-admin'); if(!root)return;
 const pl=root.dataset.locale!=='en', form=document.getElementById('routing-form');
 const words={
 title:['Hierarchia źródeł','Provider hierarchy'], layer:['Warstwa','Layer'],lane:['Tryb użycia','Usage lane'],
 live:['Skan gracza','Player scan'],background:['Uzupełnianie świata','World background'],
 poi:['POI','POI'],roads:['Drogi','Roads'],waterways:['Rzeki i kanały','Rivers and canals'],
 inland_water:['Jeziora i zbiorniki','Lakes and reservoirs'],coastline:['Wybrzeża','Coastlines'],land_water:['Ląd i morze','Land and sea'],
 hint:['Świeże dane lokalne mają pierwszeństwo przed API. Kolejność dotyczy tylko zgodnych i dopuszczonych źródeł. Zapis nie włącza źródła ani pobierania w tle.',
 'Fresh local data takes precedence over APIs. The order applies only to compatible, approved providers. Saving does not enable providers or background fetching.'],
 off:['Hierarchia skanera nieaktywna — gra używa dotychczasowej konfiguracji. Kolektor tła działa niezależnie.',
 'Scanner hierarchy inactive — the game uses the existing configuration. The background collector operates independently.'],
 on:['Hierarchia skanera aktywna. Kolejność pobierania w tle jest ustawiana osobno; ten widok nie potwierdza stanu procesu.',
 'Scanner hierarchy active. Background order is configured separately; this view does not verify process status.'],
 primary:['Źródło główne','Primary provider'],fallback1:['Pierwsze zapasowe','First fallback'],fallback2:['Drugie zapasowe','Second fallback'],
 none:['Brak','None'],save:['Zapisz kolejność','Save order'],restore:['Przywróć poprzednią kolejność','Restore previous order'],
 saved:['Kolejność zapisana. Sprawdź dostępność źródeł poniżej.','Order saved. Check provider readiness below.'],
 restored:['Poprzednia kolejność przywrócona. Uprawnienia dostawców nie zostały zmienione.','Previous order restored. Provider permissions were not changed.'],
 history:['Historia kolejności','Routing history'],ready:['Gotowy do wyboru po aktywacji hierarchii','Eligible when hierarchy is active'],
 disabled:['Wyłączony','Disabled'],approval_required:['Brak aktualnego testu lub zgody na użycie i zapis','Current technical test or usage/storage approval missing'],
 world_storage_required:['Brak zgody na zapis świata','World storage approval missing'],
 geoapify_contract_unverified:['Geoapify: diagnostyka gotowa, pełny profil CHAOS niezweryfikowany','Geoapify: diagnostics ready, full CHAOS profile unverified'],
 unsupported_layer:['Warstwa nieobsługiwana przez ten adapter','Layer unsupported by this adapter'],
 unsupported_background_profile:['Profil niedopuszczony dla tła','Profile unsupported for background'],
 observation_only:['Obserwacje geograficzne; nie jest to profil skanera gracza','Geographic observations; not a player-scanner profile'],
 provider_missing:['Brak źródła w rejestrze','Provider missing from registry'],
 routing_invalid_chain:['Wybierz każde źródło najwyżej raz, bez pustych pozycji pomiędzy.','Select each provider once, without empty positions in between.'],
 routing_revision_conflict:['Konfiguracja zmieniła się. Odśwież stan przed zapisem.','Configuration changed. Refresh before saving.'],
 routing_no_previous:['Brak poprzedniej zapisanej kolejności.','No previous saved order.'],
 budget:['Budżet wewnętrzny CHAOS (nie saldo dostawcy)','CHAOS internal budget (not provider balance)'],
 unconfigured:['Budżet nieprzygotowany','Budget not configured'],loading:['Przetwarzanie…','Working…'],empty:['Brak wybranych źródeł. Nowe zapytania API nie zostaną wykonane przez tę trasę.','No providers selected. This route will not make new API requests.']
 };
 const t=k=>words[k]?.[pl?0:1]||k, el=id=>document.getElementById(id);
 const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
 let state=null,providers=[],busy=false;
 el('routing-title').textContent=t('title');el('routing-hint').textContent=t('hint');
 el('routing-layer-label').textContent=t('layer');el('routing-lane-label').textContent=t('lane');
 el('routing-save').textContent=t('save');el('routing-restore').textContent=t('restore');el('routing-history-title').textContent=t('history');
 for(const k of ['poi','roads','waterways','inland_water','coastline','land_water'])form.elements.layer.add(new Option(t(k),k));
 for(const k of ['live','background'])form.elements.lane.add(new Option(t(k),k));
 for(const [i,k] of ['primary','fallback1','fallback2'].entries()){
  const label=node('label',t(k)),select=document.createElement('select');select.name='provider'+i;select.setAttribute('aria-label',t(k));label.append(select);el('routing-selectors').append(label);
 }
 const selected=()=>state?.routes.find(r=>r.layer===form.elements.layer.value&&r.lane===form.elements.lane.value);
 function render(){
  const route=selected();if(!route)return;
  el('routing-state').textContent=t(state.enabled?'on':'off');
  for(let i=0;i<3;i++){
   const s=form.elements['provider'+i];s.replaceChildren(new Option(t('none'),''));
   for(const p of providers)s.add(new Option(p.name+' / '+p.id,p.id));
   s.value=route.chain[i]||'';
  }
  const preview=el('routing-preview');preview.replaceChildren();
  for(const c of route.candidates)preview.append(node('li',c.id+' — '+t(c.reason||'ready')));
  if(!route.chain.length)preview.append(node('li',t('empty')));
  const budget=el('routing-budgets');budget.replaceChildren(node('strong',t('budget')));
  for(const [id,windows] of Object.entries(state.budgets))budget.append(node('p',id+': '+(windows.length?windows.map(w=>w.period+' '+w.committed+' / '+w.credit_limit).join(' · '):t('unconfigured'))));
  const history=el('routing-history');history.replaceChildren();
  for(const h of state.history)history.append(node('p',t(h.layer)+' / '+t(h.lane)+' · r'+h.revision+' · '+h.actor+' · '+new Date(h.at*1000).toLocaleString()));
  el('routing-save').disabled=busy;el('routing-restore').disabled=busy||route.revision===0;
 }
 async function call(body){
  const response=await fetch('/api/admin/poi-routing',{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Chaos-CSRF':root.dataset.csrf}:{},body:body?JSON.stringify(body):undefined});
  const data=await response.json();if(!response.ok||!data.ok)throw Error(t(data.error||String(response.status)));return data;
 }
 async function load(){
  const [routes,response]=await Promise.all([call(),fetch('/api/admin/poi-providers')]);
  const data=await response.json();if(!response.ok||!data.ok)throw Error(t(data.error||'provider_missing'));
  providers=data.providers;state=routes;render();
 }
 async function change(action){
  if(busy||!state)return;
  const r=selected(), chain=[0,1,2].map(i=>form.elements['provider'+i].value);
  if(action==='save'&&(chain.some((p,i)=>p&&chain.slice(0,i).includes(''))||new Set(chain.filter(Boolean)).size!==chain.filter(Boolean).length)){
   el('routing-feedback').textContent=t('routing_invalid_chain');return;
  }
  busy=true;el('routing-save').disabled=true;el('routing-restore').disabled=true;el('routing-feedback').textContent=t('loading');
  try{state=await call({action,layer:r.layer,lane:r.lane,revision:r.revision,...(action==='save'?{chain:chain.filter(Boolean)}:{})});
   el('routing-feedback').textContent=t(action==='save'?'saved':'restored');
  }catch(e){el('routing-feedback').textContent=e.message;}
  finally{busy=false;render();}
 }
 form.onsubmit=e=>{e.preventDefault();change('save');};el('routing-restore').onclick=()=>change('restore');
 form.elements.layer.onchange=form.elements.lane.onchange=()=>{el('routing-feedback').textContent='';render();};
 el('poi-refresh').addEventListener('click',()=>load().catch(e=>el('routing-feedback').textContent=e.message));
 load().catch(e=>el('routing-feedback').textContent=e.message);
})();
