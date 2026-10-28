"""Loopback-only, disposable Identity Gateway UI fixture; no production secrets."""
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]


def main():
    with tempfile.TemporaryDirectory(prefix='chaos-identity-ui-') as directory:
        os.chdir(directory)
        os.environ['CHAOS_SECRET_KEY']='identity-browser-fixture-only'
        os.environ['CHAOS_SESSION_FILE_DIR']=str(Path(directory)/'sessions')
        from test_identity_gateway_web import GatewayWebTests
        from flask import redirect,session,request
        from identity_gateway.store import digest
        from database import db_connect
        import secrets,time
        import run
        fixture=GatewayWebTests()
        fixture.setUp()
        if '--directory' in sys.argv:
            from test_ghostnetwork_suite_snapshot import valid_profile
            for provider,nick in [('google','Trinity'),('discord','Neo'),('steam','Żółw'),('github','Octocat')]:
                profile=valid_profile('id_'+provider+'_fixture')
                profile.update(nick=nick,password='',email=provider+'@example.test')
                fixture.users.save_profile(profile)
        if '--safety' in sys.argv:
            import communication_safety
            from database import MailStore
            from unittest.mock import patch
            with db_connect(fixture.path) as conn:
                communication_safety.initialize(conn)
            fixture.stack.enter_context(patch.object(run,'mail_store',MailStore(fixture.path)))
            run.app.config['CHAOS_COMMUNICATION_SAFETY_ENABLED']=True
        if '--adult' in sys.argv:
            run.app.config['CHAOS_AGE_POLICY_ENABLED']=True
        if '--legacy-contacts' in sys.argv:
            from database import MailStore
            from unittest.mock import patch
            mail=MailStore(fixture.path)
            fixture.stack.enter_context(patch.object(run,'mail_store',mail))
            fixture.stack.enter_context(patch.object(run,'add_cyberner_direct_notification',side_effect=mail.add_direct_notification))
            run.app.config['CHAOS_COMMUNICATION_SAFETY_ENABLED']=False
        if '--mock-providers' in sys.argv:
            from unittest.mock import patch
            def resolved_provider(provider, args, flow):
                return dict(provider=provider.name, subject=secrets.token_hex(16),
                            email='provider@example.test', email_verified=True)
            fixture.stack.enter_context(patch('identity_gateway.providers.resolve', side_effect=resolved_provider))
        @run.app.get('/__fixture/workspace')
        def identity_workspace_fixture():
            # Render the actual desktop with the fixture stores. The launch
            # controller has its own captured stores and is tested separately.
            return run.desktop()
        @run.app.get('/__fixture/map-player')
        def directory_map_profile_fixture():
            # The production profile renderer, isolated from map tiles and workers.
            source=(ROOT/'templates/map_template.html').read_text(encoding='utf8')
            start=source.index('            window.playerActorRelationLabels =')
            code=source[start:source.index('            window.showPlayerActorProfile =',start)]
            return '''<!doctype html><meta charset="utf-8"><title>Map player profile fixture</title>
<script>
window.GhostLocale={t:key=>key};window.ghostLabel=key=>key;window.ghostReply=()=>'';
window.escapeMapText=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
</script><script>'''+code+'''</script><body><script>
document.body.append(window.renderPlayerActorProfileModal({username:'id_google_fixture',nick:'Trinity'}));
</script></body>'''
        @run.app.get('/__fixture/account/<name>')
        def seed_account(name):
            if name not in ('admin','alice','bob','id_google_fixture','id_discord_fixture','id_steam_fixture','id_github_fixture'):
                return '',404
            run.begin_authenticated_session(name)
            lang='en' if request.args.get('locale')=='en' else 'pl'
            session['identity_locale']=lang
            profile=fixture.users.get_profile_with_revision(name)
            candidate=profile['profile']
            candidate['desktop_settings']['locale']=lang
            fixture.users.save_profile_guarded(candidate,expected_revision=profile['profile_revision'],source='browser.locale')
            run.identity_projection_store.update_desktop_settings(name,{'locale':lang},normalize=run.normalize_desktop_settings)
            target='/account/identity' if name!='admin' else '/dev?tab=identity&_session_generation='+run._session_generation_query_token(session[run.SESSION_GENERATION_KEY])
            return redirect(target)
        @run.app.get('/__fixture/registration')
        def seed_registration():
            session.clear()
            session['identity_client']=secrets.token_urlsafe(32)
            session['identity_ticket']=secrets.token_urlsafe(32)
            session['identity_locale']='en' if request.args.get('locale')=='en' else 'pl'
            email='browser-'+secrets.token_hex(4)+'@example.test'
            verified=None if request.args.get('unverified')=='1' else email
            with db_connect(fixture.path) as conn:
                conn.execute('INSERT INTO identity_tickets VALUES (?,?,?,?,?,?,?)',
                    (digest(session['identity_ticket']),digest(session['identity_client']),'google',secrets.token_hex(8),
                     email,verified,int(time.time())+1800))
            return redirect('/auth/register')
        @run.app.get('/__fixture/mail-code')
        def fixture_mail_code():
            from flask import jsonify
            messages=run.app.config.get('IDENTITY_TEST_OUTBOX',[])
            return jsonify(code=messages[-1]['code'] if messages else '')
        run.SESSION_GENERATION_PUBLIC_ENDPOINTS.update({'seed_account','seed_registration','identity_workspace_fixture','fixture_mail_code','directory_map_profile_fixture'})
        try:
            run.app.run(host='127.0.0.1',port=8997,debug=False,use_reloader=False)
        finally:
            fixture.doCleanups()
            os.chdir(ROOT)


if __name__=='__main__':main()
