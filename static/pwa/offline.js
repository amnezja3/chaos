'use strict';
if (navigator.language.toLowerCase().startsWith('pl')) {
    document.documentElement.lang = 'pl';
    document.getElementById('offline-message').textContent = 'Brak połączenia. Połącz się z internetem, aby wrócić do gry.';
    document.getElementById('offline-retry').textContent = 'Ponów';
}
