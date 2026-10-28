/* One public player picker for Cyberner and account safety. No provider identifiers. */
window.mountPlayerDirectory = function({form,input,results,onSelect,locale,headers={}}) {
    const tr=(pl,en)=>(typeof locale==='function'?locale():locale)==='en'?en:pl;
    const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
    let version=0,controller;
    input.maxLength=100;
    input.setAttribute('aria-label',tr('Nick lub @ID CHAOS','Nickname or @CHAOS ID'));
    results.setAttribute('aria-live','polite');
    results.classList.add('player-directory');
    input.addEventListener('input',()=>{version++;controller?.abort();results.replaceChildren();});
    form.addEventListener('submit',async event=>{
        event.preventDefault();
        const query=input.value.trim(),request=++version;
        controller?.abort();controller=new AbortController();
        results.replaceChildren();
        if(query.length<2){results.append(node('p',tr('Wpisz co najmniej 2 znaki.','Enter at least 2 characters.')));return;}
        try {
            const response=await fetch('/api/players/search?q='+encodeURIComponent(query),{signal:controller.signal,headers});
            const data=await response.json();
            if(!response.ok||!data.ok)throw Error('lookup');
            if(request!==version)return;
            if(!data.players.length)results.append(node('p',tr('Nie znaleziono gracza.','No player found.')));
            for(const player of data.players){
                const row=node('div','');row.className='player-directory-card';
                const identity=node('div','');identity.className='player-directory-identity';
                const handle=node('div',player.handle);handle.className='player-directory-handle';
                identity.append(node('strong',player.nick),handle);row.append(identity);
                const status=node('div','');status.className='player-directory-status';
                status.setAttribute('role','status');
                let statusTimer;
                const notify=(text)=>{
                    clearTimeout(statusTimer);status.textContent=text;
                    statusTimer=setTimeout(()=>{status.textContent='';},3000);
                };
                const button=node('button',tr('Wybierz gracza','Select player'));button.type='button';button.className='player-directory-select';
                button.addEventListener('click',async()=>{
                    button.disabled=true;
                    try {await onSelect(player,row,notify);}
                    catch(error){notify(tr('Nie udało się wykonać operacji.','Operation failed.'));}
                    finally{button.disabled=false;}
                });
                row.append(button,status);results.append(row);
            }
            if(data.truncated)results.append(node('p',tr('Zawęź wyszukiwanie, aby zobaczyć pozostałych graczy.','Refine your search to see more players.')));
        } catch(error){if(error.name!=='AbortError'&&request===version)results.append(node('p',tr('Wyszukiwanie niedostępne. Spróbuj ponownie.','Search unavailable. Try again.')));}
    });
};
