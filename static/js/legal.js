(() => {
  const dialog = document.querySelector('.legal-dialog');
  if (!dialog) return;
  document.addEventListener('click', event => {
      const link = event.target.closest('[data-legal-link]');
      if (!link) return;
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const locale = document.documentElement.lang.startsWith('en') ? 'en' : 'pl';
      const frame = dialog.querySelector('iframe');
      frame.title = link.querySelector('[lang="' + locale + '"]').textContent;
      frame.src = link.getAttribute('href') + '?locale=' + locale;
      dialog.showModal();
  });
  dialog.querySelector('button').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => dialog.querySelector('iframe').removeAttribute('src'));
})();
