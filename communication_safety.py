"""Communication-only policy. Never used to authorize combat or world actions.

Schema is installed by an explicit migration. Missing schema fails closed when
enabled; neither account ages nor provider identities participate in this policy.
"""
import json
import os
import time
from flask import current_app


def enabled():
    value = current_app.config.get('CHAOS_COMMUNICATION_SAFETY_ENABLED', os.getenv('CHAOS_COMMUNICATION_SAFETY_ENABLED', '0'))
    return value is True or str(value).lower() in ('1', 'true', 'yes', 'on')


DDL = (
    '''CREATE TABLE IF NOT EXISTS communication_blocks (
        owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        target_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL, PRIMARY KEY(owner_id,target_id), CHECK(owner_id!=target_id))''',
    '''CREATE TABLE IF NOT EXISTS communication_invites (
        sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','accepted','declined')),
        PRIMARY KEY(sender_id,recipient_id), CHECK(sender_id!=recipient_id))''',
    '''CREATE TABLE IF NOT EXISTS communication_limits (
        actor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        action TEXT NOT NULL, window_start INTEGER NOT NULL, attempts INTEGER NOT NULL,
        PRIMARY KEY(actor_id,action))''',
    '''CREATE TABLE IF NOT EXISTS safety_reports (
        id INTEGER PRIMARY KEY, reporter_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        target_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        object_type TEXT NOT NULL, object_key TEXT NOT NULL, category TEXT NOT NULL,
        details TEXT NOT NULL, evidence_json TEXT NOT NULL, created_at INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','reviewing','resolved')),
        decision TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL DEFAULT '')''',
    '''CREATE TABLE IF NOT EXISTS safety_actions (
        id INTEGER PRIMARY KEY, report_id INTEGER REFERENCES safety_reports(id),
        actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        action TEXT NOT NULL, reason TEXT NOT NULL, created_at INTEGER NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS safety_hidden (
        object_type TEXT NOT NULL, object_key TEXT NOT NULL,
        report_id INTEGER NOT NULL REFERENCES safety_reports(id), PRIMARY KEY(object_type,object_key))''',
    '''CREATE TABLE IF NOT EXISTS communication_sanctions (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        until_at INTEGER NOT NULL, report_id INTEGER NOT NULL REFERENCES safety_reports(id))''',
    '''CREATE TABLE IF NOT EXISTS safety_paused_sources (
        source_scope TEXT PRIMARY KEY,report_id INTEGER NOT NULL REFERENCES safety_reports(id))''',
)


def initialize(conn):
    for statement in DDL:
        conn.execute(statement)


def uid(conn, username):
    row = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
    if not row:
        raise ValueError('contact_unavailable')
    return row[0]


def blocked(conn, left, right):
    return bool(conn.execute('''SELECT 1 FROM communication_blocks
        WHERE (owner_id=? AND target_id=?) OR (owner_id=? AND target_id=?)''',
        (left, right, right, left)).fetchone())


def friends(conn, left, right):
    return bool(conn.execute('''SELECT 1 FROM contacts a JOIN contacts b
        ON a.owner_username=b.contact_name AND a.contact_name=b.owner_username
        WHERE a.owner_username=? AND a.contact_name=?''', (left, right)).fetchone())


def limited(conn, actor, action, maximum, window):
    now = int(time.time())
    row = conn.execute('SELECT window_start,attempts FROM communication_limits WHERE actor_id=? AND action=?', (actor, action)).fetchone()
    if row and row[0] > now-window:
        if row[1] >= maximum:
            raise ValueError('safety_rate_limited')
        conn.execute('UPDATE communication_limits SET attempts=attempts+1 WHERE actor_id=? AND action=?', (actor, action))
    else:
        conn.execute('INSERT OR REPLACE INTO communication_limits VALUES (?,?,?,1)', (actor, action, now))


def require_sender(conn, actor):
    row = conn.execute('SELECT until_at FROM communication_sanctions WHERE user_id=?', (actor,)).fetchone()
    if row and row[0] > time.time():
        raise ValueError('communication_restricted')


def require_send(conn, sender, route):
    actor = uid(conn, sender)
    require_sender(conn, actor)
    if route['channel'] == 'direct':
        target = uid(conn, route['peer'])
        if actor == target or blocked(conn, actor, target) or not friends(conn, sender, route['peer']):
            raise ValueError('contact_unavailable')
    limited(conn, actor, 'message', 30, 60)


def set_block(conn, owner, target_name, value):
    target = uid(conn, target_name)
    if target == owner:
        raise ValueError('contact_unavailable')
    if value:
        conn.execute('INSERT OR IGNORE INTO communication_blocks VALUES (?,?,?)', (owner,target,int(time.time())))
        # A block also withdraws contact permission, not gameplay relations.
        names = [r[0] for r in conn.execute('SELECT username FROM users WHERE id IN (?,?)', (owner,target))]
        if len(names) == 2:
            conn.execute('DELETE FROM contacts WHERE (owner_username=? AND contact_name=?) OR (owner_username=? AND contact_name=?)', (*names,*reversed(names)))
        conn.execute("UPDATE communication_invites SET status='declined' WHERE (sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?)", (owner,target,target,owner))
    else:
        conn.execute('DELETE FROM communication_blocks WHERE owner_id=? AND target_id=?', (owner,target))


def invite(conn, sender, recipient):
    actor, target = uid(conn,sender), uid(conn,recipient)
    require_sender(conn,actor)
    if actor == target or blocked(conn,actor,target):
        raise ValueError('contact_unavailable')
    if friends(conn,sender,recipient):
        return 'already_friend'
    row = conn.execute('SELECT created_at,status FROM communication_invites WHERE sender_id=? AND recipient_id=?', (actor,target)).fetchone()
    if row and row[1] == 'pending':
        return 'already_pending'
    if row and row[0] > time.time()-86400:
        raise ValueError('safety_rate_limited')
    limited(conn,actor,'invite',5,3600)
    conn.execute("INSERT OR REPLACE INTO communication_invites VALUES (?,?,?,'pending')", (actor,target,int(time.time())))
    return 'requested'


def answer_invite(conn, owner, sender_name, accept):
    sender = uid(conn,sender_name)
    if blocked(conn,owner,sender):
        raise ValueError('contact_unavailable')
    row = conn.execute("SELECT 1 FROM communication_invites WHERE sender_id=? AND recipient_id=? AND status='pending'", (sender,owner)).fetchone()
    if not row:
        raise ValueError('invitation_missing')
    conn.execute('UPDATE communication_invites SET status=? WHERE sender_id=? AND recipient_id=?', ('accepted' if accept else 'declined',sender,owner))
    if accept:
        require_sender(conn,owner)
        names = {r[0]:r[1] for r in conn.execute('SELECT id,username FROM users WHERE id IN (?,?)',(owner,sender))}
        for a,b in ((owner,sender),(sender,owner)):
            conn.execute("INSERT INTO contacts(owner_username,contact_name,status,created_at) VALUES (?,?,'offline',datetime('now')) ON CONFLICT(owner_username,contact_name) DO NOTHING", (names[a],names[b]))


def message_key(route, message):
    if route['channel'] in ('world','clan') and message.get('message_id'):
        return str(message['message_id'])
    return str(message.get('delivery_id') or message.get('message_id') or ('legacy:'+str(message.get('id'))))


def visible_messages(conn, viewer, route, messages):
    actor = uid(conn,viewer)
    hidden = {r[0] for r in conn.execute("SELECT object_key FROM safety_hidden WHERE object_type='message'")}
    muted = {r[0] for r in conn.execute('SELECT u.username FROM communication_blocks b JOIN users u ON u.id=b.target_id WHERE b.owner_id=?',(actor,))}
    result=[]
    for item in messages:
        key=message_key(route,item)
        # Preserve explicit system/domain events even when they mention a blocked player.
        player_text=item.get('source') not in ('system','domain_event','ai')
        if key in hidden or (route['channel'] != 'direct' and player_text and item.get('sender') in muted):
            continue
        result.append({**item,'safety_key':key})
    return result


def report(conn, actor, kind, key, category, details, evidence, target=None):
    if category not in ('harassment','threat','privacy','unsafe','spam') or kind not in ('message','profile','publication'):
        raise ValueError('invalid_report')
    if not isinstance(details,str) or len(details)>2000:
        raise ValueError('invalid_report')
    previous=conn.execute("SELECT id FROM safety_reports WHERE reporter_id=? AND object_type=? AND object_key=? AND status!='resolved'",(actor,kind,key)).fetchone()
    if previous:
        return previous[0]
    limited(conn,actor,'report',10,3600)
    cursor=conn.execute('''INSERT INTO safety_reports(reporter_id,target_id,object_type,object_key,category,details,evidence_json,created_at)
        VALUES (?,?,?,?,?,?,?,?)''',(actor,target,kind,key,category,details,json.dumps(evidence,ensure_ascii=False),int(time.time())))
    return cursor.lastrowid


def decide(conn, moderator, report_id, action, reason, hours=24):
    if action not in ('review','dismiss','hide','restore','restrict','release','pause_source','resume_source') or not isinstance(reason,str) or not 3<=len(reason.strip())<=2000:
        raise ValueError('invalid_decision')
    row=conn.execute('SELECT * FROM safety_reports WHERE id=?',(report_id,)).fetchone()
    if not row:
        raise ValueError('report_missing')
    if action in ('hide','restore'):
        if row['object_type'] not in ('message','publication'):
            raise ValueError('invalid_decision')
        if action=='hide':
            conn.execute('INSERT OR REPLACE INTO safety_hidden VALUES (?,?,?)',(row['object_type'],row['object_key'],report_id))
        else:
            conn.execute('DELETE FROM safety_hidden WHERE object_type=? AND object_key=?',(row['object_type'],row['object_key']))
    if action in ('restrict','release'):
        if not row['target_id'] or type(hours) is not int or not 1<=hours<=168:
            raise ValueError('invalid_decision')
        if action=='restrict':
            conn.execute('INSERT OR REPLACE INTO communication_sanctions VALUES (?,?,?)',(row['target_id'],int(time.time())+hours*3600,report_id))
        else:
            conn.execute('DELETE FROM communication_sanctions WHERE user_id=?',(row['target_id'],))
    if action in ('pause_source','resume_source'):
        source=json.loads(row['evidence_json']).get('source_scope')
        if row['object_type']!='publication' or not source:
            raise ValueError('invalid_decision')
        if action=='pause_source':
            conn.execute('INSERT OR REPLACE INTO safety_paused_sources VALUES (?,?)',(source,report_id))
        else:
            conn.execute('DELETE FROM safety_paused_sources WHERE source_scope=?',(source,))
    conn.execute('UPDATE safety_reports SET status=?,decision=?,reason=? WHERE id=?',('reviewing' if action=='review' else 'resolved',action,reason,report_id))
    conn.execute('INSERT INTO safety_actions(report_id,actor_id,action,reason,created_at) VALUES (?,?,?,?,?)',(report_id,moderator,action,reason,int(time.time())))


def visible_publications(conn, records):
    hidden={r[0] for r in conn.execute("SELECT object_key FROM safety_hidden WHERE object_type='publication'")}
    paused={r[0] for r in conn.execute('SELECT source_scope FROM safety_paused_sources')}
    return [r for r in records if r.get('medium_record_id') not in hidden and r.get('source_scope') not in paused]
