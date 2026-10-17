(() => {
  const dialog = document.querySelector('.legal-dialog');
  if (!dialog) return;
  document.querySelectorAll('[data-legal-link]').forEach(link => {
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const locale = document.documentElement.lang.startsWith('en') ? 'en' : 'pl';
      const frame = dialog.querySelector('iframe');
      frame.title = link.querySelector('[lang="' + locale + '"]').textContent;
      frame.src = link.getAttribute('href') + '?locale=' + locale;
      dialog.showModal();
    });
  });
  dialog.querySelector('button').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => dialog.querySelector('iframe').removeAttribute('src'));
})();
