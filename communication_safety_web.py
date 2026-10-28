"""Authenticated safety UI and moderation, sharing Identity CSRF/session guards."""
import json
import sqlite3
from flask import Blueprint, jsonify, render_template, request, session
from database import db_connect, atomic_runtime_transaction
from identity_gateway.service import IdentityError
import communication_safety as safety


def install(runtime):
    bp=Blueprint('safety',__name__)
    identity=runtime.identity_gateway

    def database():
        return runtime.user_store.db_path

    @bp.before_request
    def authorize():
        if not safety.enabled():
            return jsonify(ok=False,error='safety_disabled'),404
        if request.method!='GET':
            identity['csrf']()
        with db_connect(database()) as conn:
            identity['actor'](conn)
            conn.execute('SELECT 1 FROM communication_blocks LIMIT 1')

    @bp.errorhandler(IdentityError)
    def identity_error(exc):
        return identity['error'](exc)

    @bp.errorhandler(ValueError)
    def invalid(exc):
        return jsonify(ok=False,error=str(exc)),400

    @bp.errorhandler(sqlite3.Error)
    def unavailable(exc):
        return jsonify(ok=False,error='safety_unavailable'),503

    def payload():
        data=request.get_json(silent=True)
        if not isinstance(data,dict):
            raise ValueError('invalid_request')
        return data

    @bp.get('/account/safety')
    def page():
        return render_template('communication_safety.html',locale=runtime.request_ui_locale(),
            csrf=session.get('session_csrf'),generation=session.get(runtime.SESSION_GENERATION_KEY),
            moderator=bool(runtime.require_dev_admin()))

    @bp.get('/api/safety')
    def overview():
        with db_connect(database()) as conn:
            actor=identity['actor'](conn)
            blocks=[r[0] for r in conn.execute('SELECT u.username FROM communication_blocks b JOIN users u ON u.id=b.target_id WHERE b.owner_id=?',(actor,))]
            invites=[dict(r) for r in conn.execute("SELECT u.username,i.created_at FROM communication_invites i JOIN users u ON u.id=i.sender_id WHERE i.recipient_id=? AND i.status='pending'",(actor,))]
            reports=[dict(r) for r in conn.execute('''SELECT id,object_type,object_key,status,decision,reason,created_at
                FROM safety_reports WHERE reporter_id=? OR target_id=? ORDER BY id DESC LIMIT 100''',(actor,actor))]
        names=runtime.identity_projection_store.public_names(blocks+[i['username'] for i in invites])
        return jsonify(ok=True,blocks=blocks,invites=invites,reports=reports,public_names=names)

    @bp.post('/api/safety/block')
    def block():
        data=payload()
        if type(data.get('blocked')) is not bool:
            raise ValueError('invalid_request')
        with atomic_runtime_transaction(database(),foreign_keys=True) as conn:
            target=runtime.identity_projection_store.resolve_player(str(data.get('username') or ''),conn=conn) if data['blocked'] else str(data.get('username') or '')
            safety.set_block(conn,identity['actor'](conn),target,data['blocked'])
        return jsonify(ok=True)

    @bp.post('/api/safety/invite')
    def invite():
        data=payload()
        with atomic_runtime_transaction(database(),foreign_keys=True) as conn:
            identity['actor'](conn)
            target=runtime.identity_projection_store.resolve_player(str(data.get('username') or ''),conn=conn)
            result=safety.invite(conn,session['user'],target)
        return jsonify(ok=True,status=result)

    @bp.post('/api/safety/invite/answer')
    def answer():
        data=payload()
        if type(data.get('accept')) is not bool:
            raise ValueError('invalid_request')
        with atomic_runtime_transaction(database(),foreign_keys=True) as conn:
            safety.answer_invite(conn,identity['actor'](conn),str(data.get('username') or ''),data['accept'])
        return jsonify(ok=True)

    @bp.post('/api/safety/report')
    def report():
        data=payload()
        kind=data.get('kind'); key=str(data.get('key') or '')
        if not key or len(key)>200:
            raise ValueError('invalid_report')
        # Resolve only data the reporter is already allowed to read. Never trust
        # caller-supplied evidence, sender or private conversation identifiers.
        target_name=None
        if kind=='message':
            profile=runtime.identity_projection_store.get_identity(session['user'])
            route=runtime.normalize_cyberner_route(data.get('scope','world'),data.get('peer','global'),profile)
            items=runtime._cyberner_list_route_messages(session['user'],route,100)
            evidence=next((m for m in items if safety.message_key(route,m)==key),None)
            if not evidence:
                raise ValueError('object_unavailable')
            target_name=evidence.get('sender')
            evidence={k:evidence.get(k) for k in ('sender','subject','body','created_at','source')}
        elif kind=='profile':
            profile=runtime.identity_projection_store.get_identity(key)
            if not profile:
                raise ValueError('object_unavailable')
            target_name=key
            evidence={k:profile.get(k) for k in ('username','nick','clan','profession')}
        elif kind=='publication':
            profile=runtime.identity_projection_store.get_identity(session['user']) or {}
            records=runtime.get_ghostnetwork_service().repository.list_narrative_medium_records_for_viewer('blacknet',owner=session['user'],clan=runtime.get_profile_clan(profile),limit=100)
            evidence=next((r for r in records if str(r.get('medium_record_id'))==key),None)
            if not evidence:
                raise ValueError('object_unavailable')
            evidence={k:evidence.get(k) for k in ('medium_record_id','title','body','source_scope','published_at')}
        else:
            raise ValueError('invalid_report')
        with atomic_runtime_transaction(database(),foreign_keys=True) as conn:
            actor=identity['actor'](conn)
            target=conn.execute('SELECT id FROM users WHERE username=?',(target_name,)).fetchone() if target_name else None
            report_id=safety.report(conn,actor,kind,key,data.get('category'),data.get('details',''),evidence,target[0] if target else None)
        return jsonify(ok=True,id=report_id)

    @bp.post('/api/safety/appeal')
    def appeal():
        data=payload(); reason=data.get('reason')
        if not isinstance(reason,str) or not 3<=len(reason.strip())<=2000:
            raise ValueError('invalid_request')
        with atomic_runtime_transaction(database(),foreign_keys=True) as conn:
            actor=identity['actor'](conn)
            row=conn.execute('SELECT reporter_id,target_id,status FROM safety_reports WHERE id=?',(data.get('id'),)).fetchone()
            if not row or actor not in row[:2] or row[2]!='resolved':
                raise ValueError('report_unavailable')
            safety.limited(conn,actor,'appeal',5,3600)
            conn.execute("UPDATE safety_reports SET status='reviewing' WHERE id=?",(data['id'],))
            conn.execute("INSERT INTO safety_actions(report_id,actor_id,action,reason,created_at) VALUES (?,?,'appeal',?,strftime('%s','now'))",(data['id'],actor,reason))
        return jsonify(ok=True)

    @bp.get('/api/safety/moderation')
    def moderation():
        if not runtime.require_dev_admin():
            return jsonify(ok=False,error='forbidden'),403
        with db_connect(database()) as conn:
            rows=[dict(r) for r in conn.execute('SELECT * FROM safety_reports ORDER BY id DESC LIMIT 100')]
            for row in rows:
                row['actions']=[dict(r) for r in conn.execute('SELECT action,reason,created_at FROM safety_actions WHERE report_id=? ORDER BY id',(row['id'],))]
        return jsonify(ok=True,reports=rows)

    @bp.post('/api/safety/moderation')
    def decision():
        if not runtime.require_dev_admin():
            return jsonify(ok=False,error='forbidden'),403
        data=payload()
        with atomic_runtime_transaction(database(),foreign_keys=True) as conn:
            safety.decide(conn,identity['actor'](conn),data.get('id'),data.get('action'),data.get('reason'),data.get('hours',24))
        return jsonify(ok=True)

    runtime.app.register_blueprint(bp)
    runtime.SESSION_GENERATION_PUBLIC_ENDPOINTS.update(n for n in runtime.app.view_functions if n.startswith('safety.'))
    @runtime.app.context_processor
    def context():
        return dict(communication_safety_enabled=safety.enabled())

    @runtime.app.before_request
    def legacy_guard():
        if not safety.enabled() or request.method not in ('POST','DELETE'):
            return None
        if request.path not in ('/api/chats/messages','/api/player-contact/request','/api/contacts') and not request.path.startswith('/api/contacts/'):
            return None
        try:
            identity['csrf']()
            with db_connect(database()) as conn:
                identity['actor'](conn)
                conn.execute('SELECT 1 FROM communication_blocks LIMIT 0')
        except IdentityError as exc:
            return identity['error'](exc)
        except sqlite3.Error:
            return jsonify(ok=False,error='safety_unavailable'),503

    @runtime.app.after_request
    def filter_delivery(response):
        # Filter persisted/replayed communications as well as current reads.
        # World/PvP payloads are deliberately outside this allowlist.
        paths=('/api/state/changes','/api/mail/bootstrap','/api/chats/messages','/system-messages')
        if not safety.enabled() or not session.get('user') or not response.is_json or request.path not in paths:
            return response
        try:
            with db_connect(database()) as conn:
                actor=safety.uid(conn,session['user'])
                muted={r[0] for r in conn.execute('SELECT u.username FROM communication_blocks b JOIN users u ON u.id=b.target_id WHERE b.owner_id=?',(actor,))}
                hidden={r[0] for r in conn.execute("SELECT object_key FROM safety_hidden WHERE object_type='message'")}
                def scrub(value, communication_branch=False):
                    if isinstance(value,list):
                        return [clean for v in value if (clean:=scrub(v,communication_branch)) is not None]
                    if not isinstance(value,dict):
                        return value
                    communication=(value.get('scope')=='mail' or str(value.get('type','')).startswith(('mail.','cyberner.')) or value.get('notification_type')=='cyberner')
                    communication_branch=communication_branch or communication
                    if communication:
                        # Historical deltas may not carry a stable message ID.
                        # Invalidate/refetch rather than replaying stale text.
                        for field in ('body','text','preview','subject'):
                            value.pop(field,None)
                        if isinstance(value.get('payload'),dict):
                            value['payload'].pop('thread',None)
                            value['payload'].pop('message',None)
                            value['payload']['safety_refresh']=True
                    source=value.get('source')
                    if communication_branch and source not in ('system','domain_event','ai') and value.get('sender') in muted:
                        return None
                    if communication_branch and str(value.get('delivery_id') or value.get('message_id') or '') in hidden:
                        return None
                    return {k:scrub(v,communication_branch) for k,v in value.items()}
                response.set_data(runtime.app.json.dumps(scrub(response.get_json(),request.path in ('/api/mail/bootstrap','/api/chats/messages'))))
        except sqlite3.Error:
            response=jsonify(ok=False,error='safety_unavailable')
            response.status_code=503
            return response
        return response
