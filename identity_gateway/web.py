"""Gateway integration using CHAOS profiles, session generations and CSRF."""
import copy
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from flask import Blueprint, g, jsonify, redirect, render_template, request, session, url_for
from database import atomic_runtime_transaction, db_connect
from .config import load_config
from .store import issue_intent, consume_intent, digest, cleanup
from . import service as svc, providers, mail
from . import adult_policy
from session_generation_store import SessionGenerationStateError

TERMS_VERSION = '157-v1'


def install(runtime):
    from .logging import install as install_log_filter
    install_log_filter()
    app = runtime.app
    bp = Blueprint('identity',__name__)

    def config():
        if app.testing and app.config.get('IDENTITY_TEST_CONFIG'):
            return app.config['IDENTITY_TEST_CONFIG']
        try:
            return load_config()
        except ValueError:
            g.identity_config_error=True
            return load_config({})  # Keep local login available when gateway config is invalid.

    def schema_ready():
        with db_connect(runtime.user_store.db_path) as conn:
            return svc.ready(conn)

    @contextmanager
    def tx():
        with atomic_runtime_transaction(runtime.user_store.db_path,foreign_keys=True) as conn:
            if not svc.ready(conn):
                raise svc.IdentityError('migration_required')
            if adult_policy.enabled():
                adult_policy.require_schema(conn)
            yield conn

    def client():
        if not session.get('identity_client'):
            session['identity_client'] = secrets.token_urlsafe(32)
        return session['identity_client']

    def locale():
        return session.get('identity_locale') or runtime.request_ui_locale()

    def actor(conn):
        if not session.get('user') or not session.get(runtime.SESSION_GENERATION_KEY):
            raise svc.IdentityError('authentication_required')
        guard = runtime.current_request_profile_precommit_guard()
        if guard is None:
            raise svc.IdentityError('authentication_required')
        try:
            guard(conn=conn,username=session['user'],current_revision=0)
        except SessionGenerationStateError:
            raise svc.IdentityError('stale_session') from None
        if not getattr(g,'transaction_precommit_guard_token',None):
            g.session_lineage=session.get(runtime.SESSION_LINEAGE_KEY)
            g.session_generation=generation()
            g.session_generation_user=session['user']
            g.session_login_identity=session.get(runtime.SESSION_LOGIN_IDENTITY_KEY)
            g.session_account_revision=session.get(runtime.SESSION_ACCOUNT_REVISION_KEY)
            runtime.bind_request_profile_precommit_guard()
        return svc.account(conn,session['user'])[0]

    def generation():
        return session.get(runtime.SESSION_GENERATION_KEY,'')

    def csrf():
        # Also protects anonymous registration/mail confirmation; no tokens in URLs.
        expected = session.get('session_csrf') if session.get('user') else session.get('identity_csrf')
        supplied = request.headers.get('X-Chaos-CSRF','')
        if (request.headers.get('Origin') not in (config().origin,request.host_url.rstrip('/') if app.testing else config().origin)
                or request.headers.get('Sec-Fetch-Site')=='cross-site'
                or not expected or not secrets.compare_digest(expected,supplied)):
            raise svc.IdentityError('csrf_rejected')
        if session.get('user') and request.headers.get('X-Chaos-Session-Generation') != generation():
            raise svc.IdentityError('stale_session')

    def page(name, **values):
        session.setdefault('identity_csrf',secrets.token_urlsafe(32))
        return render_template(name, identity_locale=locale(),
            identity_csrf=session.get('session_csrf') if session.get('user') else session['identity_csrf'],
            identity_generation=generation(), terms_version=adult_policy.TERMS_VERSION if adult_policy.enabled() else TERMS_VERSION, **values)

    def available(provider):
        cfg = config()
        item = next((p for p in cfg.providers if p.name==provider),None)
        if not cfg.enabled or not item or not item.enabled or not item.configured:
            raise svc.IdentityError('provider_disabled')
        return item

    def ticket(conn):
        token = session.get('identity_ticket')
        row = conn.execute('SELECT * FROM identity_tickets WHERE token_hash=? AND client_hash=? AND expires_at>?',
            (digest(token or '-'),digest(client()),int(time.time()))).fetchone()
        if not row:
            raise svc.IdentityError('registration_expired')
        return row

    def mail_config(conn):
        return mail.load(conn,config().mail,app.secret_key)

    def send_code(binding, address, authorized_until=None):
        code = f'{secrets.randbelow(100000000):08d}'
        expires=min(int(time.time())+1800,authorized_until) if authorized_until else int(time.time())+1800
        if expires<=time.time():
            raise svc.IdentityError('reauth_required')
        minutes=max(1,int((expires-time.time()+59)//60))
        with tx() as conn:
            svc.rate_limit(conn,'mail:'+address,5,3600)
            svc.rate_limit(conn,'mail-client:'+client(),5,3600)
            cfg = mail_config(conn)
            if not cfg.configured and not (cfg.mode=='mock' and app.testing):
                raise svc.IdentityError('mail_unavailable')
            owner=svc.account(conn,session['user'])[0] if session.get('user') else None
            conn.execute('INSERT OR REPLACE INTO identity_mail_challenges VALUES (?,?,?,?,0,?)',
                         (digest(binding),address,digest(binding+code),expires,owner))
        try:
            mail.deliver(cfg,address,code,locale(),minutes=minutes,testing=app.testing,
                         outbox=app.config.setdefault('IDENTITY_TEST_OUTBOX',[]) if app.testing else None)
        except svc.IdentityError:
            with tx() as conn:
                conn.execute('DELETE FROM identity_mail_challenges WHERE binding_hash=?',(digest(binding),))
            raise

    def check_code(binding, code):
        # Failed guesses must commit their counter, not roll back with an error.
        result = None
        with tx() as conn:
            row = conn.execute('SELECT * FROM identity_mail_challenges WHERE binding_hash=?',(digest(binding),)).fetchone()
            if row and row['expires_at']>time.time() and row['attempts']<5:
                if secrets.compare_digest(row['code_hash'],digest(binding+str(code))):
                    result = row['email']
                    conn.execute('DELETE FROM identity_mail_challenges WHERE binding_hash=?',(digest(binding),))
                else:
                    conn.execute('UPDATE identity_mail_challenges SET attempts=attempts+1 WHERE binding_hash=?',(digest(binding),))
        if not result:
            raise svc.IdentityError('invalid_code')
        return result

    @bp.before_request
    def protect():
        g.suppress_session_cookie = False
        if request.method=='POST':
            csrf()
            if not isinstance(request.get_json(silent=True),dict):
                raise svc.IdentityError('invalid_request')
        if request.path.startswith(('/account/','/api/account/','/api/admin/identity')):
            with tx() as conn:
                actor(conn)
            if request.path.startswith('/api/admin/') and not runtime.require_dev_admin():
                raise svc.IdentityError('forbidden')
        elif not config().enabled:
            raise svc.IdentityError('provider_disabled')

    @app.errorhandler(svc.IdentityError)
    def error(exc):
        key = str(exc)
        status={'authentication_required':401,'forbidden':403,'csrf_rejected':403,
                'stale_session':409,'rate_limited':429,'migration_required':503,
                'provider_unavailable':503,'mail_delivery_failed':503,'mail_unavailable':503}.get(key,400)
        if request.path.startswith('/api/') or request.method=='POST':
            response = jsonify(ok=False,error=key,**({'retry_after_seconds': exc.retry_after}
                if key=='rate_limited' and hasattr(exc,'retry_after') else {}))
            if key=='rate_limited' and hasattr(exc,'retry_after'):
                response.headers['Retry-After']=str(exc.retry_after)
            return response,status
        return page('identity_gateway.html',mode='error',identity_error=key),status

    @bp.errorhandler(sqlite3.IntegrityError)
    def collision(_exc):
        return error(svc.IdentityError('identity_collision'))

    @bp.after_request
    def private(response):
        response.headers['Cache-Control']='no-store'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Frame-Options']='SAMEORIGIN'
        return response

    def start_flow(provider, purpose, user_id=None, reauth_expires=None):
        item = available(provider)
        with tx() as conn:
            cleanup(conn)
            svc.rate_limit(conn,'auth-client:'+client(),20)
            svc.rate_limit(conn,'auth-ip:'+str(runtime.get_request_ip()),60)
            state = issue_intent(conn,purpose=purpose,provider=provider,client=client(),ttl=600,
                                 user_id=user_id,generation=generation() if user_id else None)
            target, flow = providers.authorization(item,state,config().origin)
            if user_id:
                if not reauth_expires or reauth_expires<=time.time():
                    raise svc.IdentityError('reauth_required')
                flow['reauth_expires']=reauth_expires
            conn.execute('INSERT INTO identity_flow_data VALUES (?,?)',(digest(state),json.dumps(flow)))
        return target

    @bp.get('/auth/<provider>')
    def start(provider):
        if session.get('user'):
            return redirect('/account/identity')
        session['identity_locale'] = 'en' if request.args.get('locale')=='en' else 'pl'
        return redirect(start_flow(provider,'login'))

    @bp.get('/auth/<provider>/callback')
    def callback(provider):
        item = available(provider)
        if any(len(request.args.getlist(k))!=1 for k in request.args):
            raise svc.IdentityError('invalid_provider_response')
        state = request.args.get('state','')
        if not state or len(state)>256 or not session.get('identity_client'):
            raise svc.IdentityError('callback_context_lost')
        with tx() as conn:
            row = conn.execute('SELECT * FROM identity_intents WHERE token_hash=?',(digest(state),)).fetchone()
            if not row:
                raise svc.IdentityError('invalid_or_expired_intent')
            if row['purpose']=='link':
                user_id = actor(conn)
            else:
                user_id = None
                if session.get('user'):
                    raise svc.IdentityError('callback_context_lost')
            flow_row = conn.execute('SELECT data_json FROM identity_flow_data WHERE token_hash=?',(digest(state),)).fetchone()
            consume_intent(conn,state,purpose=row['purpose'],provider=provider,client=client(),
                           user_id=user_id,generation=generation() if user_id else None)
            flow = json.loads(flow_row[0]) if flow_row else {}
            if user_id and flow.get('reauth_expires',0)<=time.time():
                raise svc.IdentityError('reauth_required')
        try:
            identity = providers.resolve(item,request.args.to_dict(),flow)
        except svc.IdentityError:
            raise
        except Exception:
            raise svc.IdentityError('invalid_provider_response') from None
        address, invalid = runtime.validate_registration_email(identity.get('email'))
        identity['email'] = None if invalid else address
        identity['email_verified'] = bool(identity['email'] and identity.get('email_verified'))
        with tx() as conn:
            if user_id:
                if actor(conn)!=user_id:
                    raise svc.IdentityError('stale_session')
                if flow.get('reauth_expires',0)<=time.time():
                    raise svc.IdentityError('reauth_required')
                svc.link(conn,user_id,identity)
                return redirect('/account/identity')
            if conn.execute('SELECT 1 FROM identity_retired_subjects WHERE provider=? AND subject_hash=?',
                            (provider,digest(identity['subject']))).fetchone():
                raise svc.IdentityError('identity_retired')
            linked = conn.execute('''SELECT u.username FROM user_identities i JOIN users u ON u.id=i.user_id
                WHERE i.provider=? AND i.provider_user_id=?''',(provider,identity['subject'])).fetchone()
            if linked:
                username = linked[0]
                record = runtime.user_store.get_profile_with_revision(username)
                if not record or record.get('state')!='valid':
                    raise svc.IdentityError('account_unavailable')
                conn.execute('UPDATE user_identities SET last_used_at=? WHERE provider=? AND provider_user_id=?',
                             (int(time.time()),provider,identity['subject']))
            else:
                if not config().registration_enabled:
                    raise svc.IdentityError('registration_disabled')
                token = secrets.token_urlsafe(32)
                conn.execute('INSERT INTO identity_tickets VALUES (?,?,?,?,?,?,?)',
                    (digest(token),digest(client()),provider,identity['subject'],identity['email'],
                     identity['email'] if identity['email_verified'] else None,int(time.time())+1800))
                session['identity_ticket']=token
                return redirect('/auth/register')
        gen = runtime.begin_authenticated_session(username)
        return redirect('/launch' if app.config.get('CHAOS_LAUNCH_CONTROLLER_ENABLED') else
                        url_for('desktop',_session_generation=runtime._session_generation_query_token(gen)))

    @bp.get('/auth/register')
    def registration():
        with tx() as conn:
            row = ticket(conn)
        return page('identity_registration.html',mode='register',registration_email=row['email'] or '',
                    verified_email=row['verified_email'] or '',
                    factions={f:runtime.locale_translator().t(f'onboarding.faction.{f}.name',locale=locale()) for f in runtime.FACTION_NAMES},
                    faction_descriptions={f:runtime.locale_translator().t(f'onboarding.faction.{f}.summary',locale=locale()) for f in runtime.FACTION_NAMES},
                    roles={str(f):[dict(role_slot=str(r),profession_name=runtime.locale_translator().t(
                        f'onboarding.role.{f}.{r}',locale=locale())) for r in range(1,6)] for f in runtime.FACTION_NAMES})

    @bp.post('/auth/register/email')
    def registration_email():
        data=request.get_json(silent=True) or {}
        with tx() as conn:
            ticket(conn)
        address, invalid=runtime.validate_registration_email(data.get('email'))
        if invalid:
            raise svc.IdentityError('invalid_email')
        binding='register:'+session['identity_ticket']
        if data.get('code'):
            verified=check_code(binding,data['code'])
            with tx() as conn:
                row=ticket(conn)
                conn.execute('UPDATE identity_tickets SET email=?,verified_email=? WHERE token_hash=?',
                             (verified,verified,row['token_hash']))
        else:
            send_code(binding,address)
        return jsonify(ok=True, **({'verified_email': verified} if data.get('code') else {'code_sent': True}))

    @bp.post('/auth/complete-registration')
    def complete():
        if not config().registration_enabled or session.get('user'):
            raise svc.IdentityError('registration_disabled')
        data=request.get_json(silent=True) or {}
        nick, invalid=runtime.validate_registration_nick(data.get('nick'))
        email, bad_email=runtime.validate_registration_email(data.get('email'))
        if adult_policy.enabled():
            adult_policy.validate(data)
        if invalid or bad_email or (not adult_policy.enabled() and data.get('terms')!=TERMS_VERSION):
            raise svc.IdentityError('invalid_registration')
        try:
            identity=runtime.build_registration_identity_contract(data.get('faction'),data.get('role'))
        except ValueError:
            raise svc.IdentityError('invalid_registration') from None
        start=runtime.get_start_location_by_ip(runtime.get_request_ip())
        spawn=runtime.resolve_first_respawn_outside_controlled_territory({'lat':start['lat'],'lng':start['lng']})
        if not spawn.get('position'):
            raise svc.IdentityError('spawn_unavailable')
        profile=copy.deepcopy(runtime.resources_store.get('user_template',default={}))
        username='id_'+secrets.token_hex(9)
        profile.update(username=username,password='',salt='',nick=nick,email=email,hackcoins=1000,
            avatar=identity['avatar'],curently_possition=spawn['position'],clan=identity['faction_name'],
            ghost_clan=identity['clan_code'],ghost_clan_code=identity['clan_code'],
            profession=identity['profession_code'],ghost_profession=identity['profession_code'],
            fraction=dict(id=identity['faction_id'],name=identity['faction_name'],role=identity['role_slot']))
        profile['desktop_settings']={**(profile.get('desktop_settings') or {}),'locale':locale()}
        with tx() as conn:
            row=ticket(conn)
            if row['verified_email']!=email:
                raise svc.IdentityError('email_verification_required')
            svc.assert_available(conn,profile,username)
            runtime.user_store.save_profile_guarded(profile,expected_revision=0,
                source='profile_manager.registration',allow_create=True)
            user_id=svc.account(conn,username)[0]
            svc.link(conn,user_id,dict(provider=row['provider'],subject=row['subject'],email=email,email_verified=True))
            conn.execute('UPDATE identity_account_security SET verified_email=?,email_verified_at=? WHERE user_id=?',
                         (email,int(time.time()),user_id))
            if adult_policy.enabled():
                adult_policy.record(conn,user_id,data)
            else:
                conn.execute('INSERT INTO identity_consents (user_id,terms_version,accepted_at) VALUES (?,?,?)',(user_id,TERMS_VERSION,int(time.time())))
            conn.execute('DELETE FROM identity_tickets WHERE token_hash=?',(row['token_hash'],))
            svc.event(conn,'account_registered',user_id,user_id)
        gen=runtime.begin_authenticated_session(username)
        return jsonify(ok=True,redirect='/launch' if app.config.get('CHAOS_LAUNCH_CONTROLLER_ENABLED') else
                       url_for('desktop',_session_generation=runtime._session_generation_query_token(gen)))

    @bp.get('/account/identity')
    def account_page():
        return page('identity_gateway.html',mode='account')

    @bp.get('/account/terms')
    def adult_terms():
        with tx() as conn:
            actor(conn)
            reason=adult_policy.state(conn,session['user']) if adult_policy.enabled() else ''
        if not reason:
            return redirect('/launch')
        return page('identity_adult_terms.html',mode='adult',age_restricted=reason=='age_restricted')

    @bp.post('/api/account/terms')
    def accept_adult_terms():
        if not adult_policy.enabled():
            raise svc.IdentityError('adult_policy_disabled')
        data=request.get_json(silent=True) or {}
        adult_policy.validate(data)
        with tx() as conn:
            user_id=actor(conn)
            adult_policy.record(conn,user_id,data)
        return jsonify(ok=True,redirect='/launch')

    @bp.post('/api/account/terms/decline')
    def decline_adult_terms():
        if not adult_policy.enabled():
            raise svc.IdentityError('adult_policy_disabled')
        data=request.get_json(silent=True) or {}
        with tx() as conn:
            user_id=actor(conn)
            if data.get('underage') is True:
                conn.execute('UPDATE identity_account_security SET age_restricted=1 WHERE user_id=?',(user_id,))
                svc.event(conn,'age_restricted',user_id,user_id)
        return jsonify(ok=True,redirect='/account/terms')

    @bp.get('/api/account/identities')
    def identities():
        with tx() as conn:
            user_id=actor(conn)
            rows=conn.execute('SELECT provider,linked_at,last_used_at FROM user_identities WHERE user_id=?',(user_id,)).fetchall()
            state=conn.execute('SELECT local_password_enabled,verified_email FROM identity_account_security WHERE user_id=?',(user_id,)).fetchone()
        return jsonify(ok=True,username=session['user'],identities=[dict(r) for r in rows],
                       password_enabled=bool(state and state[0]),verified_email=state[1] if state else None,
                       providers=[p.status() for p in config().providers],linking_enabled=config().linking_enabled)

    @bp.post('/api/account/reauth')
    def reauth():
        data=request.get_json(silent=True) or {}
        action=data.get('action','')
        if action not in ('link','unlink','password','email','delete','mail_settings'):
            raise svc.IdentityError('invalid_action')
        with tx() as conn:
            user_id=actor(conn)
            svc.rate_limit(conn,'reauth:'+str(user_id),10)
            state=conn.execute('SELECT verified_email FROM identity_account_security WHERE user_id=?',(user_id,)).fetchone()
        if data.get('password'):
            if not runtime.user_store.authenticate(session['user'],data['password']):
                raise svc.IdentityError('reauth_failed')
        elif data.get('code'):
            verified=check_code('reauth:'+str(user_id)+generation()+action,data['code'])
            if not state or verified!=state[0]:
                raise svc.IdentityError('reauth_failed')
        else:
            if not state or not state[0]:
                raise svc.IdentityError('verified_email_required')
            send_code('reauth:'+str(user_id)+generation()+action,state[0])
            return jsonify(ok=True,code_sent=True)
        with tx() as conn:
            actor(conn)
            if data.get('code'):
                current=conn.execute('SELECT verified_email FROM identity_account_security WHERE user_id=?',(user_id,)).fetchone()
                if not current or current[0]!=verified:
                    raise svc.IdentityError('reauth_failed')
            token=svc.grant(conn,user_id,generation(),action)
            svc.event(conn,'reauth_success',user_id,user_id)
        return jsonify(ok=True,grant=token)

    @bp.post('/api/account/identities/<provider>/<action>')
    def manage(provider,action):
        if provider not in ('google','github','discord','steam') or action not in ('link','unlink'):
            raise svc.IdentityError('invalid_action')
        data=request.get_json(silent=True) or {}
        with tx() as conn:
            user_id=actor(conn)
            deadline=svc.use_grant(conn,data.get('grant'),user_id,generation(),action)
            if action=='unlink':
                svc.unlink(conn,user_id,provider)
            elif not config().linking_enabled:
                raise svc.IdentityError('linking_disabled')
        return jsonify(ok=True,redirect=start_flow(provider,'link',user_id,deadline) if action=='link' else None)

    @bp.post('/api/account/password')
    def password():
        data=request.get_json(silent=True) or {}
        new=data.get('password','')
        if not isinstance(new,str) or new!=data.get('confirm') or runtime.validate_registration_password(new):
            raise svc.IdentityError('invalid_password')
        with tx() as conn:
            user_id=actor(conn)
            svc.use_grant(conn,data.get('grant'),user_id,generation(),'password')
            record=runtime.user_store.get_profile_with_revision(session['user'])
            candidate=copy.deepcopy(record['profile'])
            candidate.update(password=new,salt='')
            runtime.user_store.save_profile_guarded(candidate,expected_revision=record['profile_revision'],
                                                     source='profile.identity_password')
            svc.event(conn,'password_changed',user_id,user_id)
        runtime.invalidate_authenticated_session('credentials_changed',durable_already_revoked=True)
        return jsonify(ok=True,redirect='/?login=1')

    @bp.post('/api/account/email')
    def account_email():
        data=request.get_json(silent=True) or {}
        with tx() as conn:
            user_id=actor(conn)
        binding='email:'+str(user_id)+generation()
        if data.get('code'):
            address=check_code(binding,data['code'])
            with tx() as conn:
                actor(conn)
                record=runtime.user_store.get_profile_with_revision(session['user'])
                candidate=copy.deepcopy(record['profile'])
                candidate['email']=address
                runtime.user_store.save_profile_guarded(candidate,expected_revision=record['profile_revision'],source='profile.identity_email')
                conn.execute('UPDATE identity_account_security SET verified_email=?,email_verified_at=? WHERE user_id=?',
                             (address,int(time.time()),user_id))
                svc.event(conn,'email_verified',user_id,user_id)
        else:
            address,bad=runtime.validate_registration_email(data.get('email'))
            if bad:
                raise svc.IdentityError('invalid_email')
            with tx() as conn:
                actor(conn)
                deadline=svc.use_grant(conn,data.get('grant'),user_id,generation(),'email')
            send_code(binding,address,authorized_until=deadline)
        return jsonify(ok=True)

    def delete_account():
        csrf()
        data=request.get_json(silent=True) or {}
        target=str(data.get('username') or session.get('user') or '').strip()
        if target=='admin' or (target!=session.get('user') and not runtime.require_dev_admin()):
            raise svc.IdentityError('forbidden')
        if data.get('confirm')!=target:
            raise svc.IdentityError('confirmation_required')
        with tx() as conn:
            actor_id=actor(conn)
            svc.use_grant(conn,data.get('grant'),actor_id,generation(),'delete')
            row=svc.account(conn,target)
            runtime.user_store.delete_user(target,preserve_peer_history=True,identity_actor_id=actor_id)
            # Existing coordinator revokes after checking the initiating session.
            conn._credential_revocations.add(target)
        if target==session.get('user'):
            runtime.invalidate_authenticated_session('account_deleted',durable_already_revoked=True)
        return jsonify(ok=True,success=True,redirect='/?login=1' if target==session.get('user') or not session.get('user') else None)

    bp.add_url_rule('/api/account/delete','delete_account',delete_account,methods=['POST'])

    @bp.get('/api/admin/identity')
    def admin_status():
        with tx() as conn:
            actor(conn)
            cfg=mail_config(conn)
            events=conn.execute('SELECT event,actor_id,target_id,created_at FROM identity_security_events ORDER BY id DESC LIMIT 50').fetchall()
            selected=request.args.get('username','').strip()
            rows=conn.execute('''SELECT u.username,i.provider,i.linked_at,i.last_used_at FROM user_identities i
                JOIN users u ON u.id=i.user_id WHERE u.username=?''',(selected,)).fetchall() if selected else []
        return jsonify(ok=True,configuration=config().status(),configuration_error=bool(getattr(g,'identity_config_error',False)),mail=mail.public(cfg),
                       events=[dict(r) for r in events],identities=[dict(r) for r in rows])

    @bp.post('/api/admin/identity/mail')
    def admin_mail():
        data=request.get_json(silent=True) or {}
        with tx() as conn:
            user_id=actor(conn)
            svc.use_grant(conn,data.get('grant'),user_id,generation(),'mail_settings')
            try:
                previous=mail_config(conn)
            except svc.IdentityError as exc:
                if str(exc)!='mail_secret_unavailable' or not (data.get('password') or data.get('clear_password') is True):
                    raise
                previous=config().mail
            cfg=mail.save(conn,data,previous,app.secret_key)
            svc.event(conn,'mail_settings_changed',user_id,None)
        return jsonify(ok=True,mail=mail.public(cfg))

    @bp.post('/api/admin/identity/mail/test')
    def admin_mail_test():
        data=request.get_json(silent=True) or {}
        address,bad=runtime.validate_registration_email(data.get('recipient'))
        if bad:
            raise svc.IdentityError('invalid_email')
        with tx() as conn:
            user_id=actor(conn)
            svc.rate_limit(conn,'mail-test:'+str(user_id),5,3600)
            cfg=mail_config(conn)
        mail.deliver(cfg,address,'SMTP TEST',locale(),testing=app.testing,
                     outbox=app.config.setdefault('IDENTITY_TEST_OUTBOX',[]) if app.testing else None)
        return jsonify(ok=True)

    @app.context_processor
    def provider_context():
        cfg=config()
        return dict(identity_gateway_enabled=cfg.enabled or schema_ready(),
                    identity_provider_ready={p.name:cfg.enabled and p.enabled and p.configured for p in cfg.providers})

    app.register_blueprint(bp)
    runtime.SESSION_GENERATION_PUBLIC_ENDPOINTS.update('identity.'+name for name in bp.view_functions)
    # Flask stores blueprint endpoint names on app, not Blueprint.view_functions.
    runtime.SESSION_GENERATION_PUBLIC_ENDPOINTS.update(name for name in app.view_functions if name.startswith('identity.'))
    return dict(actor=actor,tx=tx,config=config,csrf=csrf,delete=delete_account,error=error,schema_ready=schema_ready)
