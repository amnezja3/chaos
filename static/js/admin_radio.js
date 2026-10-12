(() => {
    const form = document.getElementById('radio-settings');
    const select = document.getElementById('radio-channel');
    const save = document.getElementById('radio-save');
    const notice = document.getElementById('radio-notice');
    async function request(options) {
        const response = await fetch('/api/admin/radio', {cache: 'no-store', ...options});
        const data = await response.json();
        if (!response.ok || !data.success) throw Error(adminT('radio_save_error'));
        return data;
    }
    request().then(data => {
        data.channels.forEach(channel => select.add(new Option(`${channel.name} (${channel.language})`, channel.id)));
        const validation = document.getElementById('radio-language-validation');
        for (const item of data.language_validation || []) {
            const row = document.createElement('li');
            row.textContent = `${item.channel}: ${item.code}${item.file ? ' — ' + item.file : ''}`;
            validation.appendChild(row);
        }
        if (!validation.children.length) validation.textContent = adminT('no_language_conflicts');
        select.value = data.default_channel;
        select.disabled = save.disabled = false;
    }).catch(error => { notice.textContent = error.message; });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        select.disabled = save.disabled = true;
        notice.textContent = adminT('saving');
        try {
            const data = await request({method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({autostart_channel: select.value})});
            select.value = data.default_channel;
            notice.textContent = adminT('radio_saved');
        } catch (error) { notice.textContent = error.message; }
        finally { select.disabled = save.disabled = false; }
    });
})();
