if (!window.chaosIdentityStartInstalled) {
  window.chaosIdentityStartInstalled = true;
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-identity-provider]');
    if (!button || button.disabled) return;
    const lang = document.documentElement.lang.startsWith('en') ? 'en' : 'pl';
    location.assign('/auth/' + encodeURIComponent(button.dataset.identityProvider) + '?locale=' + lang);
  });
}
