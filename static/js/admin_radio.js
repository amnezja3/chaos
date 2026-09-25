(() => {
    const form = document.getElementById('radio-settings');
    const select = document.getElementById('radio-channel');
    const save = document.getElementById('radio-save');
    const notice = document.getElementById('radio-notice');
    async function request(options) {
        const response = await fetch('/api/admin/radio', {cache: 'no-store', ...options});
        const data = await response.json();
        if (!response.ok || !data.success) throw Error(data.message || 'Nie udało się zapisać ustawień.');
        return data;
    }
    request().then(data => {
        data.channels.forEach(channel => select.add(new Option(`${channel.name} (${channel.id})`, channel.id)));
        select.value = data.default_channel;
        select.disabled = save.disabled = false;
    }).catch(error => { notice.textContent = error.message; });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        select.disabled = save.disabled = true;
        notice.textContent = 'Zapisywanie…';
        try {
            const data = await request({method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({autostart_channel: select.value})});
            select.value = data.default_channel;
            notice.textContent = 'Zapisano kanał autostartu.';
        } catch (error) { notice.textContent = error.message; }
        finally { select.disabled = save.disabled = false; }
    });
})();
