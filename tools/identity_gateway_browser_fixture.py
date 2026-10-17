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
        @run.app.get('/__fixture/workspace')
        def identity_workspace_fixture():
            # Render the actual desktop with the fixture stores. The launch
            # controller has its own captured stores and is tested separately.
            return run.desktop()
        @run.app.get('/__fixture/account/<name>')
        def seed_account(name):
            if name not in ('admin','alice'):
                return '',404
            run.begin_authenticated_session(name)
            lang='en' if request.args.get('locale')=='en' else 'pl'
            session['identity_locale']=lang
            profile=fixture.users.get_profile_with_revision(name)
            candidate=profile['profile']
            candidate['desktop_settings']['locale']=lang
            fixture.users.save_profile_guarded(candidate,expected_revision=profile['profile_revision'],source='browser.locale')
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
        run.SESSION_GENERATION_PUBLIC_ENDPOINTS.update({'seed_account','seed_registration','identity_workspace_fixture','fixture_mail_code'})
        try:
            run.app.run(host='127.0.0.1',port=8997,debug=False,use_reloader=False)
        finally:
            fixture.doCleanups()
            os.chdir(ROOT)


if __name__=='__main__':main()
