(() => {
 'use strict';
 const section=window.adminSection, listing=document.getElementById('listing'), detail=document.getElementById('detail'), notice=document.getElementById('notice');
 let offset=0, listSerial=0, detailSerial=0, resourceSerial=0, selected='';
 const labels={username:adminT('username'),nick:adminT('nick'),clan:adminT('clan'),profession:adminT('profession'),hackcoins:adminT('hackcoins'),level:adminT('level'),respect:adminT('respect'),lat:adminT('lat'),lng:adminT('lng'),storage_capacity:adminT('storage_capacity'),storage_used:adminT('storage_used'),id:adminT('id'),owner:adminT('owner'),area_size:adminT('area_size'),status:adminT('status'),updated_at:adminT('updated_at'),label:adminT('label'),name:adminT('label'),reporter:adminT('reporter'),type:adminT('type'),app_id:adminT('app_id'),folder:adminT('folder'),operation_id:adminT('operation_id'),target_key:adminT('target_key'),captured_at:adminT('captured_at')};
 const node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 const value=v=>v===null||v===undefined||v===''?'—':String(v);
 labels.created_at=adminT('created_at');
 Object.assign(labels,{destination:adminT('destination'),reactions:adminT('reactions'),historical_reactions:adminT('historical_reactions')});
 if(section==='ghostlab') Object.assign(labels,{created_at:adminT('project_created'),author:adminT('author'),template_id:adminT('template_id'),source_tool_id:adminT('source_tool_id'),downloads:adminT('downloads'),price_hc:adminT('price_hc'),creation_enabled:adminT('creation_enabled'),publication_enabled:adminT('publication_enabled'),runtime_enabled:adminT('runtime_enabled'),contract_version:adminT('contract_version'),artifact_id:adminT('artifact_id'),icon:adminT('icon')});
 const createdDate=v=>{
  if(!v)return adminT('missing_date');
  const raw=String(v).trim(),date=new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw)?raw:raw+'Z');
  return Number.isNaN(date.getTime())?adminT('missing_date'):date.toLocaleString(window.adminLocale,{timeZone:'Europe/Warsaw',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})+adminT('warsaw');
 };
 async function request(url,options={}) {
  const response=await fetch(url,{cache:'no-store',...options});
  const data=await response.json().catch(()=>null);
  if(!response.ok||!data||data.success===false)throw Error(data?.error==='ghostsystem_restart_required'?adminT('epoch_changed'):data?.error==='admin_required'?adminT('admin_required'):data?.error==='player_not_found'?adminT('player_missing'):adminT('http_error',{status:String(response.status)}));
  return data;
 }
 function table(items){
  if(!items.length)return node('p',adminT('empty'));
  const wrap=node('div');wrap.className='table-scroll';const t=node('table'),head=node('tr');
  const keys=Object.keys(items[0]);keys.forEach(k=>head.append(node('th',labels[k]||k)));const thead=node('thead');thead.append(head);t.append(thead);
  const body=node('tbody');items.forEach(item=>{const row=node('tr');keys.forEach(k=>row.append(node('td',value(item[k]))));body.append(row);});t.append(body);wrap.append(t);return wrap;
 }
 async function loadList(){
  const serial=++listSerial;notice.textContent=adminT('loading_list');
  try{
   const data=await request('/api/admin/panel/list?'+new URLSearchParams({section,offset,search:document.getElementById('search').value,template_id:document.getElementById('glab-filter')?.value||''}));
   if(serial!==listSerial)return;
   listing.replaceChildren();
   if(section==='ghostlab'){
    document.getElementById('glab-templates').replaceChildren(table(data.templates));
    document.getElementById('glab-non').textContent=adminT('outside_lab',{names:data.non_glab.join(', ')});
    const filter=document.getElementById('glab-filter');
    if(filter.options.length===1)data.templates.forEach(t=>filter.add(new Option(t.name,t.id)));
   }
   if(section==='users'){
    if(!data.items.length)listing.append(node('p',adminT('no_users')));
    data.items.forEach(user=>{
     const b=node('button');b.className=user.is_new?'user-row user-row-new':'user-row';b.dataset.username=user.username;b.setAttribute('aria-pressed',String(selected===user.username));
     if(user.is_new){const badge=node('span',adminT('new_account'));badge.className='new-account-badge';b.append(badge);}
     b.append(node('strong',user.nick||user.username),node('small',`${user.username} / ${user.clan||adminT('no_clan')}`),node('small',adminT('created',{date:createdDate(user.created_at)})));
     b.onclick=()=>loadUser(user.username);listing.append(b);
    });
   }else listing.append(table(data.items));
   document.getElementById('prev').disabled=offset===0;document.getElementById('next').disabled=!data.has_more;document.getElementById('page-label').textContent=adminT('page',{page:String(Math.floor(offset/50)+1)});notice.textContent=adminT('shown',{count:String(data.items.length)});
  }catch(error){if(serial===listSerial)notice.textContent=error.message;}
 }
 async function loadUser(username){
  selected=username;const serial=++detailSerial;++resourceSerial;
  listing.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.username===username)));
  detail.replaceChildren(node('p',adminT('loading_account')));
  try{
   const data=await request('/api/admin/panel/user?'+new URLSearchParams({username}));if(serial!==detailSerial)return;
   detail.replaceChildren(node('h2',data.user.nick||username));const fields=node('dl');
   Object.entries(data.user).forEach(([key,v])=>{fields.append(node('dt',labels[key]||key),node('dd',key==='created_at'?createdDate(v):value(v)));});detail.append(fields);
   const settings=node('section');settings.className='settings';settings.append(node('h3',adminT('account_settings')));
   if(data.profession.choices.length){
    const form=node('form');form.className='toolbar';const label=node('label',adminT('profession')),select=node('select');
    data.profession.choices.forEach(p=>select.add(new Option(p.name,p.code)));select.value=data.profession.selected?.code||data.user.profession;label.append(select);const save=node('button',adminT('save_profession')),status=node('p');status.setAttribute('role','status');form.append(label,save);settings.append(form,status);
    form.onsubmit=async event=>{event.preventDefault();save.disabled=true;status.textContent=adminT('saving');try{await request('/api/admin/users/profession',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,profession_code:select.value})});if(serial===detailSerial){await loadUser(username);notice.textContent=adminT('profession_saved');}}catch(error){status.textContent=error.message;}finally{save.disabled=false;}};
   }else settings.append(node('p',adminT('no_professions')));
   detail.append(settings);const tabs=node('div');tabs.className='resource-tabs';const resources=node('div');
   for(const [key,title] of [['apps',adminT('apps')],['tools',adminT('tools')],['files',adminT('files')],['operations',adminT('operations')],['captures',adminT('captures')],['security',adminT('security')]]){
    const b=node('button',title);tabs.append(b);b.onclick=()=>{
     if(key==='security'){++resourceSerial;resources.replaceChildren(table(Object.entries(data.security).map(([name,v])=>({name,status:typeof v==='boolean'?(v?adminT('enabled'):adminT('disabled')):v}))));}
     else loadResource(key,0);
    };
   }
   detail.append(tabs,resources);resources.append(node('p',adminT('select_resource')));
   async function loadResource(key,start){
    const token=++resourceSerial;resources.replaceChildren(node('p',adminT('loading_resources')));
    try{const result=await request('/api/admin/panel/list?'+new URLSearchParams({section:key,username,offset:start}));if(token!==resourceSerial||serial!==detailSerial)return;
     resources.replaceChildren(table(result.items));const pager=node('div');pager.className='pager';const prev=node('button',adminT('prev')),next=node('button',adminT('next'));prev.disabled=start===0;next.disabled=!result.has_more;prev.onclick=()=>loadResource(key,start-50);next.onclick=()=>loadResource(key,start+50);pager.append(prev,node('span',adminT('page',{page:String(Math.floor(start/50)+1)})),next);resources.append(pager);
    }catch(error){if(token===resourceSerial&&serial===detailSerial)resources.replaceChildren(node('p',error.message));}
   }
  }catch(error){if(serial===detailSerial)detail.replaceChildren(node('p',error.message));}
 }
 document.getElementById('search-form').onsubmit=e=>{e.preventDefault();offset=0;loadList();};
 const glabFilter=document.getElementById('glab-filter');
 if(glabFilter)glabFilter.onchange=()=>{offset=0;loadList();};
 document.getElementById('prev').onclick=()=>{offset=Math.max(0,offset-50);loadList();};document.getElementById('next').onclick=()=>{offset+=50;loadList();};
 loadList();
})();
