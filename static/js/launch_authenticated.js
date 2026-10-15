// Served only after a successful credential login, never selected by URL parameters.
try { sessionStorage.removeItem('chaos-launch-binding-v1'); } catch (_) { /* launch reports unavailable storage */ }
location.replace('/launch');
