(() => {
 'use strict';
 const panel=document.getElementById('narrative-panel'), form=document.getElementById('provider-form');

 const t=k=>adminT('narrative.'+k), node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
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
  document.getElementById('provider-meta').textContent=`${t('secret')}: ${t(data.secret_configured?'configured':'missing')} · ${t('revision')}: ${revision} · ${data.endpoint} · ${t('used')}: ${data.last_provider||'—'} · ${t('concurrency')}: 1 · ${t('circuit')}: ${data.circuit.until_at>Date.now()/1000?`${data.circuit.code} ${t('until')} ${new Date(data.circuit.until_at*1000).toLocaleString(window.adminLocale)}`:t('closed')}`;
  const list=document.getElementById('provider-calls');list.replaceChildren();
  if(!data.calls.length){list.append(node('p',t('empty')));return;}
  const table=document.createElement('table'), head=document.createElement('tr');
  ['date','provider','model','status','duration','error'].forEach(k=>head.append(node('th',t(k))));table.append(head);
  data.calls.forEach(c=>{const tr=document.createElement('tr');[new Date(c.started_at*1000).toLocaleString(window.adminLocale),c.provider,c.model,t(c.status),c.duration_ms,c.error_code||'—'].forEach(v=>tr.append(node('td',v)));table.append(tr);});list.append(table);
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
