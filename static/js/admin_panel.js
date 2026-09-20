(() => {
 'use strict';
 const section=window.adminSection, listing=document.getElementById('listing'), detail=document.getElementById('detail'), notice=document.getElementById('notice');
 let offset=0, listSerial=0, detailSerial=0, resourceSerial=0, selected='';
 const labels={username:'Login',nick:'Nazwa gracza',clan:'Klan',profession:'Profesja',hackcoins:'Saldo HC',level:'Poziom',respect:'Respekt',lat:'Szerokość',lng:'Długość',storage_capacity:'Pojemność (MB)',storage_used:'Zajęte (MB)',id:'ID',owner:'Właściciel',area_size:'Powierzchnia (m²)',status:'Status',updated_at:'Aktualizacja',label:'Nazwa',name:'Nazwa',reporter:'Zgłaszający',type:'Typ',app_id:'Aplikacja',folder:'Katalog',operation_id:'Operacja',target_key:'Cel',captured_at:'Przejęto'};
 const node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 const value=v=>v===null||v===undefined||v===''?'—':String(v);
 labels.created_at='Utworzono konto';
 const createdDate=v=>{
  if(!v)return 'Brak daty';
  const raw=String(v).trim(),date=new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw)?raw:raw+'Z');
  return Number.isNaN(date.getTime())?'Brak daty':date.toLocaleString('pl-PL',{timeZone:'Europe/Warsaw',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})+' (Warszawa)';
 };
 async function request(url,options={}) {
  const response=await fetch(url,{cache:'no-store',...options});
  const data=await response.json().catch(()=>null);
  if(!response.ok||!data||data.success===false)throw Error(data?.error==='ghostsystem_restart_required'?'Epoka świata zmieniła się. Odśwież panel.':data?.error==='admin_required'?'Brak uprawnień administratora.':data?.error==='player_not_found'?'Konto nie istnieje lub wymaga naprawy projekcji.':data?.message||`Nie udało się wykonać operacji (HTTP ${response.status}). Odśwież panel i spróbuj ponownie.`);
  return data;
 }
 function table(items){
  if(!items.length)return node('p','Brak danych.');
  const wrap=node('div');wrap.className='table-scroll';const t=node('table'),head=node('tr');
  const keys=Object.keys(items[0]);keys.forEach(k=>head.append(node('th',labels[k]||k)));const thead=node('thead');thead.append(head);t.append(thead);
  const body=node('tbody');items.forEach(item=>{const row=node('tr');keys.forEach(k=>row.append(node('td',value(item[k]))));body.append(row);});t.append(body);wrap.append(t);return wrap;
 }
 async function loadList(){
  const serial=++listSerial;notice.textContent='Ładowanie listy…';
  try{
   const data=await request('/api/admin/panel/list?'+new URLSearchParams({section,offset,search:document.getElementById('search').value}));
   if(serial!==listSerial)return;
   listing.replaceChildren();
   if(section==='users'){
    if(!data.items.length)listing.append(node('p','Nie znaleziono użytkowników.'));
    data.items.forEach(user=>{
     const b=node('button');b.className=user.is_new?'user-row user-row-new':'user-row';b.dataset.username=user.username;b.setAttribute('aria-pressed',String(selected===user.username));
     if(user.is_new){const badge=node('span','NOWE · ostatnie 7 dni');badge.className='new-account-badge';b.append(badge);}
     b.append(node('strong',user.nick||user.username),node('small',`${user.username} / ${user.clan||'bez klanu'}`),node('small',`Utworzono: ${createdDate(user.created_at)}`));
     b.onclick=()=>loadUser(user.username);listing.append(b);
    });
   }else listing.append(table(data.items));
   document.getElementById('prev').disabled=offset===0;document.getElementById('next').disabled=!data.has_more;document.getElementById('page-label').textContent=`Strona ${Math.floor(offset/50)+1}`;notice.textContent=`Wyświetlono ${data.items.length} pozycji.`;
  }catch(error){if(serial===listSerial)notice.textContent=error.message;}
 }
 async function loadUser(username){
  selected=username;const serial=++detailSerial;++resourceSerial;
  listing.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.username===username)));
  detail.replaceChildren(node('p','Ładowanie konta…'));
  try{
   const data=await request('/api/admin/panel/user?'+new URLSearchParams({username}));if(serial!==detailSerial)return;
   detail.replaceChildren(node('h2',data.user.nick||username));const fields=node('dl');
   Object.entries(data.user).forEach(([key,v])=>{fields.append(node('dt',labels[key]||key),node('dd',key==='created_at'?createdDate(v):value(v)));});detail.append(fields);
   const settings=node('section');settings.className='settings';settings.append(node('h3','Zarządzanie kontem'));
   if(data.profession.choices.length){
    const form=node('form');form.className='toolbar';const label=node('label','Profesja'),select=node('select');
    data.profession.choices.forEach(p=>select.add(new Option(p.name,p.code)));select.value=data.profession.selected?.code||data.user.profession;label.append(select);const save=node('button','Zapisz profesję'),status=node('p');status.setAttribute('role','status');form.append(label,save);settings.append(form,status);
    form.onsubmit=async event=>{event.preventDefault();save.disabled=true;status.textContent='Zapisywanie…';try{await request('/api/admin/users/profession',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,profession_code:select.value})});if(serial===detailSerial){await loadUser(username);notice.textContent='Profesja została zmieniona.';}}catch(error){status.textContent=error.message;}finally{save.disabled=false;}};
   }else settings.append(node('p','Brak profesji dostępnych dla klanu tego konta.'));
   detail.append(settings);const tabs=node('div');tabs.className='resource-tabs';const resources=node('div');
   for(const [key,title] of [['apps','Aplikacje'],['tools','Narzędzia'],['files','Pliki'],['operations','Operacje'],['captures','Przejęte cele'],['security','Zabezpieczenia']]){
    const b=node('button',title);tabs.append(b);b.onclick=()=>{
     if(key==='security'){++resourceSerial;resources.replaceChildren(table(Object.entries(data.security).map(([name,v])=>({name,status:typeof v==='boolean'?(v?'Włączone':'Wyłączone'):v}))));}
     else loadResource(key,0);
    };
   }
   detail.append(tabs,resources);resources.append(node('p','Wybierz kategorię zasobów.'));
   async function loadResource(key,start){
    const token=++resourceSerial;resources.replaceChildren(node('p','Ładowanie zasobów…'));
    try{const result=await request('/api/admin/panel/list?'+new URLSearchParams({section:key,username,offset:start}));if(token!==resourceSerial||serial!==detailSerial)return;
     resources.replaceChildren(table(result.items));const pager=node('div');pager.className='pager';const prev=node('button','← Wstecz'),next=node('button','Dalej →');prev.disabled=start===0;next.disabled=!result.has_more;prev.onclick=()=>loadResource(key,start-50);next.onclick=()=>loadResource(key,start+50);pager.append(prev,node('span',`Strona ${Math.floor(start/50)+1}`),next);resources.append(pager);
    }catch(error){if(token===resourceSerial&&serial===detailSerial)resources.replaceChildren(node('p',error.message));}
   }
  }catch(error){if(serial===detailSerial)detail.replaceChildren(node('p',error.message));}
 }
 document.getElementById('search-form').onsubmit=e=>{e.preventDefault();offset=0;loadList();};
 document.getElementById('prev').onclick=()=>{offset=Math.max(0,offset-50);loadList();};document.getElementById('next').onclick=()=>{offset+=50;loadList();};
 loadList();
})();
