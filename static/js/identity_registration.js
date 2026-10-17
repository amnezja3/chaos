(() => {
 'use strict';
 const form=document.getElementById('identity-registration');
 if(!form)return;
 const en=document.documentElement.lang==='en', tr=(pl,enText)=>en?enText:pl;
 const $=id=>document.getElementById(id), roles=JSON.parse($('identity-roles').textContent);
 let step=0, verified=form.dataset.verifiedEmail||'';
 const key=value=>value.trim().toLowerCase();
 const titles=[tr('Twoja historia zaczyna się tutaj.','Your story starts here.'),tr('Wybierz, po której stronie stoisz.','Choose where you stand.'),tr('Znajdź swoje miejsce w klanie.','Find your place in the clan.'),tr('Gotowość do wejścia w świat CHAOS.','Ready to enter the world of CHAOS.')];
 const copies=[tr('Wybierz imię, pod którym poznają Cię inni operatorzy.','Choose the name other operators will know you by.'),tr('Każdy klan ma własną ideę i sposób działania.','Every clan has its own identity and approach.'),tr('Wybierz avatar swojej profesji.','Choose your profession’s avatar.'),tr('Sprawdź postać i adres kontaktowy. Konto powstanie dopiero po Twoim potwierdzeniu.','Review your character and contact address. Your account is only created when you confirm.')];
 function message(button,text){let node=button.nextElementSibling;if(!node?.hasAttribute('data-operation-status')){node=document.createElement('p');node.dataset.operationStatus='';node.setAttribute('role','status');button.after(node);}node.dataset.level='error';node.textContent=text;}
 function chosen(){return form.querySelector('[data-faction="'+form.elements.faction.value+'"]');}
 function avatar(){return '/static/images/avatar-frakcja-'+form.elements.faction.value+'-player-'+form.elements.role.value+'.png?v=156-7-art';}
 function syncEmail(){
  const confirmed=Boolean(verified)&&key(form.elements.email.value)===key(verified);
  $('registration-email-verification').hidden=confirmed;
  $('registration-email-state').textContent=confirmed?tr('Adres potwierdzony — nie musisz wysyłać kodu.','Address verified — no code is needed.'):tr('Potwierdź adres, aby zakończyć rejestrację.','Verify your address to finish registration.');
  $('registration-email-state').dataset.verified=String(confirmed);
  return confirmed;
 }
 function renderRoles(){
  $('setup-roles').replaceChildren();$('setup-clan-name').textContent=chosen()?.dataset.name||'';
  for(const role of roles[form.elements.faction.value]||[]){
   const button=document.createElement('button');button.type='button';button.className='choice-card avatar-button';button.dataset.role=role.role_slot;
   button.setAttribute('aria-pressed',String(form.elements.role.value===role.role_slot));
   const img=document.createElement('img');img.src='/static/images/avatar-frakcja-'+form.elements.faction.value+'-player-'+role.role_slot+'.png?v=156-7-art';img.alt='';img.loading='lazy';
   const title=document.createElement('strong');title.textContent=role.profession_name;
   button.append(img,title);button.addEventListener('click',()=>{
    form.elements.role.value=role.role_slot;
    $('setup-roles').querySelectorAll('button').forEach(node=>node.setAttribute('aria-pressed',String(node===button)));
    $('setup-story-title').textContent=role.profession_name;
    $('setup-story-copy').textContent=tr('Wybrana profesja w klanie: ','Selected profession in clan: ')+chosen().dataset.name;
   });$('setup-roles').append(button);
  }
 }
 function show(next){
  step=next;
  form.querySelectorAll('[data-setup-step]').forEach(node=>node.hidden=Number(node.dataset.setupStep)!==step);
  $('identity-steps').querySelectorAll('li').forEach((node,index)=>{node.classList.toggle('complete',index<step);if(index===step)node.setAttribute('aria-current','step');else node.removeAttribute('aria-current');});
  $('setup-back').hidden=step===0;$('setup-next').hidden=step===3;
  $('setup-progress').textContent=(step+1)+' / 4';$('progress-fill').style.width=((step+1)*25)+'%';
  $('setup-story').src='/static/images/onboarding/156-7/story-'+[1,2,3,6][step]+'.png';
  $('setup-story-title').textContent=titles[step];$('setup-story-copy').textContent=copies[step];
  if(step===1&&chosen()){$('setup-story-title').textContent=chosen().dataset.name;$('setup-story-copy').textContent=chosen().dataset.description;}
  if(step===2)renderRoles();
  if(step===3){$('setup-summary-nick').textContent=form.elements.nick.value;$('setup-summary-clan').textContent=chosen().dataset.name;$('setup-summary-role').textContent=(roles[form.elements.faction.value]||[]).find(r=>r.role_slot===form.elements.role.value)?.profession_name||'';$('setup-summary-avatar').src=avatar();syncEmail();}
  form.querySelectorAll('[data-operation-status]').forEach(node=>node.remove());
  if(next!==0)form.querySelector('[data-setup-step="'+step+'"] h2').focus({preventScroll:false});
 }
 function advance(){
  if(step===0&&!form.elements.nick.reportValidity())return;
  if(step===1&&!form.elements.faction.value){message($('setup-next'),tr('Wybierz avatar klanu.','Choose a clan avatar.'));return;}
  if(step===2&&!form.elements.role.value){message($('setup-next'),tr('Wybierz avatar profesji.','Choose a profession avatar.'));return;}
  show(Math.min(3,step+1));
 }
 form.querySelectorAll('[data-faction]').forEach(button=>button.addEventListener('click',()=>{
  if(form.elements.faction.value!==button.dataset.faction)form.elements.role.value='';
  form.elements.faction.value=button.dataset.faction;
  form.querySelectorAll('[data-faction]').forEach(node=>node.setAttribute('aria-pressed',String(node===button)));
  $('setup-story-title').textContent=button.dataset.name;$('setup-story-copy').textContent=button.dataset.description;
 }));
 $('setup-next').addEventListener('click',advance);$('setup-back').addEventListener('click',()=>show(Math.max(0,step-1)));
 form.elements.email.addEventListener('input',syncEmail);
 form.addEventListener('identity:email-verified',event=>{verified=event.detail.email;syncEmail();$('registration-code').value='';});
 for(const id of ['registration-send','registration-verify'])$(id).addEventListener('click',event=>{
  if(!form.elements.email.reportValidity()){event.preventDefault();event.stopImmediatePropagation();}
  else if(id==='registration-verify'&&!$('registration-code').value.trim()){
   event.preventDefault();event.stopImmediatePropagation();message($(id),tr('Wpisz kod z wiadomości.','Enter the code from your email.'));
  }
 });
 form.addEventListener('submit',event=>{
  if(step<3){event.preventDefault();event.stopImmediatePropagation();advance();return;}
  if(!syncEmail()||!form.reportValidity()){
   event.preventDefault();event.stopImmediatePropagation();
   if(!syncEmail())message($('registration-complete'),tr('Najpierw potwierdź adres e-mail.','Verify your email address first.'));
  }
 });
 show(0);syncEmail();
})();
