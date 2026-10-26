"""Isolated production message renderer; no accounts, DB or external network."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def page():
    source=(ROOT/'static/js/terminal.js').read_text(encoding='utf8')
    start=source.index('    const renderMessages = (messages, forceScroll = false) => {')
    code=source[start:source.index('    const loadMessages = async',start)]
    return '''<!doctype html><meta charset="utf-8"><title>Cyberner nick regression</title>
<body data-communication-safety="1" style="background:#00190b;color:#4f9;font:16px monospace">
<h1>Cyberner</h1><div id="messages"></div><output id="action"></output><script>
let currentMessages=[],currentUser='id_self',currentChat={scope:'direct',peer:'id_other'};
const messagesBox=document.getElementById('messages');
const replaceCurrentMessages=m=>currentMessages=m,isNearMessageBottom=()=>true;
const messageSenderLabel=m=>m.sender||m.from||'System';
const isSystemMessage=m=>m.sender==='System',isKnownContact=()=>true;
const cybernerSourceKeyForMessage=()=> 'player',cybernerIcon=()=> '🌐';
const escapeHTML=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const ghostLabel=()=>'';
window.createIdentitySettingsWindow=data=>document.getElementById('action').textContent=JSON.stringify(data);
CODE
renderMessages([
{sender:'id_self',sender_display_name:'Neo',body:'Moja wiadomość'},
{sender:'id_other',sender_display_name:'Trinity <img src=x onerror=alert(1)>',body:'Wiadomość kontaktu',safety_key:'safe'},
{sender:'System',body:'System działa'}]);
</script>'''.replace('CODE',code)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body=page().encode('utf8');self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(body)

if __name__=='__main__':HTTPServer(('127.0.0.1',8998),Handler).serve_forever()
