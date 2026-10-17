(() => {
 'use strict';
 const config=JSON.parse(document.getElementById('identity-config').textContent), en=config.locale==='en';
 const tr=(pl,english)=>en?english:pl, $=id=>document.getElementById(id);
 const errors={callback_context_lost:tr('Wróć do pierwotnego okna CHAOS i rozpocznij ponownie.','Return to the original CHAOS window and start again.'),
  mail_unavailable:tr('Poczta nie jest jeszcze skonfigurowana.','Mail is not configured yet.'),mail_delivery_failed:tr('Nie udało się wysłać wiadomości. Sprawdź konfigurację SMTP.','Email delivery failed. Check SMTP settings.'),
  identity_collision:tr('Te dane są już używane. Zaloguj się do istniejącego konta i podłącz dostawcę.','These details are already used. Sign in to the existing account and link the provider.'),
  last_method:tr('Nie można odłączyć ostatniej metody logowania.','You cannot remove your last sign-in method.'),
  reauth_required:tr('Potwierdź tożsamość ponownie.','Confirm your identity again.'),reauth_failed:tr('Nieprawidłowe potwierdzenie tożsamości.','Identity confirmation failed.'),
  invalid_code:tr('Kod jest nieprawidłowy, wygasł lub przekroczono limit prób.','The code is incorrect, expired, or has exceeded its attempt limit.'),
  verified_email_required:tr('Najpierw potwierdź e-mail przy użyciu hasła lokalnego.','First verify an email using your local password.'),
  email_verification_required:tr('Potwierdź dokładnie ten adres e-mail.','Verify this exact email address.'),
  rate_limited:tr('Zbyt wiele prób. Spróbuj później.','Too many attempts. Try again later.'),
  invalid_password:tr('Hasło: 8–128 znaków, litera i cyfra; oba pola muszą być zgodne.','Password: 8–128 characters, a letter and a digit; both fields must match.')};
 const embedded=window.parent!==window, returnKey='chaos.identity.return';
 document.body.classList.toggle('identity-embedded',embedded);
 function navigate(url,returnToAccount=false){
  if(embedded){if(returnToAccount){try{window.parent.sessionStorage.setItem(returnKey,String(Date.now()));}catch(_){}}window.top.location.assign(url);}
  else location.assign(url);
 }
 if(!embedded&&config.mode==='account'){
  try{const timestamp=Number(sessionStorage.getItem(returnKey));if(timestamp&&Date.now()-timestamp<600000){location.replace('/launch');return;}}catch(_){}
 }
 document.querySelectorAll('[data-identity-return]').forEach(node=>node.addEventListener('click',event=>{
  event.preventDefault();if(embedded)window.parent.postMessage({type:'chaos.identity.close'},location.origin);else navigate('/launch');
 }));
 function status(text,level='success',target=null,notify=true){
  let output=$('identity-status');
  if(target?.tagName==='BUTTON'){output=target.nextElementSibling;if(!output?.hasAttribute('data-operation-status')){output=document.createElement('p');output.dataset.operationStatus='';output.setAttribute('role','status');target.after(output);}}
  output.textContent=text;output.dataset.level=level;
  if(!notify)return;
  if(embedded)window.parent.postMessage({type:'chaos.identity.status',text,level},location.origin);
  else {
   let host=$('identity-notifications');if(!host){host=document.createElement('div');host.id='identity-notifications';document.body.append(host);}
   const toast=document.createElement('div');toast.className='identity-toast '+level;toast.setAttribute('role',level==='error'?'alert':'status');
   const title=document.createElement('strong');title.textContent=tr('Konto i bezpieczeństwo','Account & security');
   const body=document.createElement('p');body.textContent=text;
   const close=document.createElement('button');close.type='button';close.textContent='×';close.setAttribute('aria-label',tr('Zamknij','Close'));close.onclick=()=>toast.remove();
   toast.append(title,body,close);host.append(toast);setTimeout(()=>toast.remove(),level==='error'?15000:7000);
  }
 }
 async function api(path,data){const response=await fetch(path,{method:data?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-Chaos-CSRF':config.csrf,'X-Chaos-Session-Generation':config.generation},...(data?{body:JSON.stringify(data)}:{})}); const result=await response.json();if(!response.ok||result.ok===false){let message=errors[result.error]||tr('Operacja nie powiodła się. Odśwież lub zaloguj się ponownie.','Operation failed. Refresh or sign in again.');if(result.error==='rate_limited'&&result.retry_after_seconds){message+=tr(' Ponów za około ',' Retry in about ')+Math.ceil(result.retry_after_seconds/60)+tr(' min.',' min.');}throw new Error(message);}return result;}
 function run(fn,success=tr('Zmiany zapisane.','Changes saved.')){return async event=>{event?.preventDefault(); const button=event?.submitter||event?.currentTarget;if(button?.tagName==='BUTTON')button.disabled=true;if(event)status(tr('Trwa wykonywanie…','Working…'),'pending',button,false);try{await fn();if(event)status(success,'success',button);}catch(e){status(e.message,'error',button);}finally{if(button?.tagName==='BUTTON')button.disabled=false;}};}
 const formData=id=>Object.fromEntries(new FormData($(id)));
 const registration=$('identity-registration');
 async function grant(action){const result=await api('/api/account/reauth',{action,password:$('reauth-password').value,code:$('reauth-code').value});if(!result.grant)throw new Error(tr('Wysłano kod. Wpisz go i ponów operację.','Code sent. Enter it and retry the action.'));$('reauth-code').value='';return result.grant;}
 $('reauth-send')?.addEventListener('click',run(()=>api('/api/account/reauth',{action:$('reauth-action').value}),tr('Kod został wysłany.','Code sent.')));
 document.querySelectorAll('[data-identity-error]').forEach(node=>{node.textContent=errors[node.dataset.identityError]||tr('Próba wygasła, została odrzucona lub dostawca jest niedostępny.','The attempt expired, was rejected, or the provider is unavailable.');});
 async function loadAccount(){
  const data=await api('/api/account/identities');
  $('local-username').textContent=data.username;
  $('password-state').textContent=data.password_enabled?tr('hasło ustawione','password configured'):tr('bez hasła','no password');
  $('verified-email').textContent=data.verified_email||'—';
  $('identity-methods').replaceChildren();
  for(const p of data.providers){
   let linked=data.identities.some(i=>i.provider===p.provider);
   const row=document.createElement('section'),button=document.createElement('button');
   const names={google:'Google',github:'GitHub',discord:'Discord',steam:'Steam'};
   row.className='identity-method identity-method--'+p.provider;
   const title=document.createElement('h3');title.textContent=names[p.provider]||p.provider;
   const state=document.createElement('p');state.className='identity-method-state';state.textContent=linked?tr('● Połączono','● Connected'):tr('Niepołączone','Not connected');
   button.type='button';button.textContent=linked?tr('Odłącz','Disconnect'):tr('Podłącz','Connect');
   button.disabled=!linked&&(!data.linking_enabled||!p.enabled||!p.configured);
   if(button.disabled)state.textContent=tr('Obecnie niedostępne','Currently unavailable');
   button.addEventListener('click',run(async()=>{
    const action=linked?'unlink':'link';
    const result=await api('/api/account/identities/'+p.provider+'/'+action,{grant:await grant(action)});
    if(result.redirect)navigate(result.redirect,true);
    else {linked=false;button.textContent=tr('Podłącz','Connect');state.textContent=tr('Niepołączone','Not connected');}
   },tr('Operacja wykonana.','Action completed.')));
   row.append(title,state,button);$('identity-methods').append(row);
  }
 }
 async function loadAdmin(username=''){const data=await api('/api/admin/identity'+(username?'?username='+encodeURIComponent(username):''));$('provider-status').textContent=data.configuration.providers.map(p=>p.provider+': '+(p.enabled&&p.configured?tr('włączony','enabled'):tr('wyłączony / niegotowy','disabled / unconfigured'))).join(' · ');for(const [key,value] of Object.entries(data.mail)){const field=$('identity-mail').elements.namedItem(key);if(field&&field.type!=='password')field.value=String(value);}$('smtp-secret-state').textContent=data.mail.password_configured?tr('Sekret SMTP: ustawiony','SMTP secret: configured'):tr('Sekret SMTP: brak','SMTP secret: missing');$('identity-events').textContent=JSON.stringify(data.events,null,2);$('admin-identities').textContent=JSON.stringify(data.identities,null,2);}
 $('identity-password')?.addEventListener('submit',run(async()=>{const data=formData('identity-password');data.grant=await grant('password');const result=await api('/api/account/password',data);navigate(result.redirect);}));
 $('identity-email')?.addEventListener('submit',run(async()=>{const data=formData('identity-email');data.grant=await grant('email');await api('/api/account/email',data);},tr('Kod został wysłany na podany adres.','Code sent to the supplied address.')));
 $('identity-email-confirm')?.addEventListener('submit',run(async()=>{await api('/api/account/email',formData('identity-email-confirm'));await loadAccount();}));
 $('identity-delete')?.addEventListener('submit',run(async()=>{const data=formData('identity-delete');data.username=data.confirm;data.grant=await grant('delete');const result=await api('/api/account/delete',data);if(result.redirect)navigate(result.redirect);}));
 $('identity-mail')?.addEventListener('submit',run(async()=>{const data=formData('identity-mail');data.clear_password=$('identity-mail').elements.clear_password.checked;data.grant=await grant('mail_settings');await api('/api/admin/identity/mail',data);$('identity-mail').elements.password.value='';await loadAdmin();}));
 $('identity-mail-test')?.addEventListener('submit',run(()=>api('/api/admin/identity/mail/test',formData('identity-mail-test')),tr('Serwer SMTP przyjął wiadomość. Sprawdź skrzynkę odbiorczą i spam.','The SMTP server accepted the message. Check your inbox and spam.')));
 $('identity-admin-lookup')?.addEventListener('submit',run(()=>loadAdmin(formData('identity-admin-lookup').username)));
 $('registration-send')?.addEventListener('click',run(()=>api('/auth/register/email',{email:$('identity-registration').elements.email.value}),tr('Kod został wysłany na podany adres.','Code sent to the supplied address.')));
 $('registration-verify')?.addEventListener('click',run(async()=>{const result=await api('/auth/register/email',{email:$('identity-registration').elements.email.value,code:$('registration-code').value});registration.dispatchEvent(new CustomEvent('identity:email-verified',{detail:{email:result.verified_email}}));},tr('Adres e-mail potwierdzony.','Email address verified.')));
 $('identity-registration')?.addEventListener('submit',run(async()=>{const result=await api('/auth/complete-registration',formData('identity-registration'));navigate(result.redirect);}));
 if(config.mode==='account')run(loadAccount)();if(config.mode==='admin')run(()=>loadAdmin())();
})();
