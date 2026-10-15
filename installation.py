"""Public, account-independent installation resources and rollback worker."""
from flask import abort, jsonify, send_from_directory, Response
from ghost_i18n import translator


def register_installation(app):
    def enabled():
        return all(app.config.get(key, False) for key in (
            'CHAOS_INSTALL_UI_ENABLED', 'CHAOS_LAUNCH_CONTROLLER_ENABLED',
            'CHAOS_PERSISTENT_SESSION_ENABLED'))

    @app.context_processor
    def context():
        active = enabled()
        keys = ('title', 'optional', 'manual', 'ios', 'ready', 'cancelled', 'accepted',
                'installed', 'standalone', 'unavailable', 'shortcut', 'update', 'recommend', 'error')
        return {'chaos_install_enabled': active,
                'chaos_install_text': {locale: {key: translator().t('entry.install.' + key, locale=locale)
                    for key in keys} for locale in ('pl', 'en')} if active else {}}

    @app.get('/chaos.webmanifest', endpoint='installation_manifest')
    def manifest():
        if not enabled():
            abort(404)
        response = jsonify(id='/chaos', name='CHAOS — Ghost System', short_name='CHAOS',
                       start_url='/launch', scope='/', display='standalone',
                       background_color='#020802', theme_color='#020802',
                       icons=[{'src': f'/static/pwa/icon-{size}.png?v=156-4',
                               'sizes': f'{size}x{size}', 'type': 'image/png',
                               'purpose': 'any maskable'} for size in (192, 512)])
        response.mimetype = 'application/manifest+json'
        return response

    @app.get('/chaos-sw.js', endpoint='installation_worker')
    def worker():
        if enabled():
            response = send_from_directory(app.static_folder, 'pwa/worker.js')
        else:
            # Keep this URL alive after rollback. Retire only our own caches;
            # no reload, cookie changes or deletion of other applications' data.
            response = Response("self.addEventListener('install',()=>self.skipWaiting());"
                "self.addEventListener('activate',e=>e.waitUntil((async()=>{"
                "for(const k of await caches.keys())if(k.startsWith('chaos-install-'))await caches.delete(k);"
                "await self.registration.unregister();})()));", mimetype='application/javascript')
        response.headers['Service-Worker-Allowed'] = '/'
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/chaos.desktop', endpoint='installation_shortcut')
    def shortcut():
        return Response('[Desktop Entry]\nType=Link\nName=CHAOS\n'
                        'URL=https://chaos.re/launch\nIcon=applications-internet\n',
                        mimetype='application/x-desktop',
                        headers={'Content-Disposition': 'attachment; filename="CHAOS.desktop"'})
