/* One public player picker for Cyberner and account safety. No provider identifiers. */
window.mountPlayerDirectory = function({form,input,results,onSelect,locale,headers={}}) {
    const tr=(pl,en)=>(typeof locale==='function'?locale():locale)==='en'?en:pl;
    const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
    let version=0,controller;
    input.maxLength=100;
    input.setAttribute('aria-label',tr('Nick lub @ID CHAOS','Nickname or @CHAOS ID'));
    results.setAttribute('aria-live','polite');
    results.style.cssText='max-height:260px;overflow:auto;overflow-wrap:anywhere;';
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
                const row=node('div','');row.style.cssText='padding:8px 0;border-bottom:1px solid #285741;';
                row.append(node('strong',player.nick),node('div',player.handle));
                const button=node('button',tr('Wybierz gracza','Select player'));button.type='button';
                button.addEventListener('click',async()=>{
                    button.disabled=true;
                    try {await onSelect(player,row);}
                    catch(error){row.append(node('p',tr('Nie udało się wykonać operacji.','Operation failed.')));}
                    finally{button.disabled=false;}
                });
                row.append(button);results.append(row);
            }
            if(data.truncated)results.append(node('p',tr('Zawęź wyszukiwanie, aby zobaczyć pozostałych graczy.','Refine your search to see more players.')));
        } catch(error){if(error.name!=='AbortError'&&request===version)results.append(node('p',tr('Wyszukiwanie niedostępne. Spróbuj ponownie.','Search unavailable. Try again.')));}
    });
};
