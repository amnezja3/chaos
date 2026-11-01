(() => {
    const form=document.querySelector('#camera-admin-action');
    if(!form)return;
    form.addEventListener('submit',async event=>{
        event.preventDefault();
        const button=form.querySelector('button'), output=document.querySelector('#camera-admin-result');
        if(button.disabled)return;
        button.disabled=true;
        try {
            const data=Object.fromEntries(new FormData(form));
            const response=await fetch('/api/admin/camera',{method:'POST',headers:{'Content-Type':'application/json','X-Chaos-CSRF':form.dataset.csrf},body:JSON.stringify(data)});
            const result=await response.json();
            output.textContent=response.ok?'OK':result.reason || result.error || 'Request failed';
        } catch (_) { output.textContent='Connection unavailable'; }
        finally {button.disabled=false;}
    });
})();
