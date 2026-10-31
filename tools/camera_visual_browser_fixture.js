/* 164.0 isolated host. No Flask, accounts, DB, provider calls or gameplay writes.
 * Run: node tools/camera_visual_browser_fixture.js (http://127.0.0.1:8999).
 */
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const base = path.join(root, 'doc/prototypes/camera_view/v164_0');
const terminal = fs.readFileSync(path.join(root, 'static/js/terminal.js'), 'utf8');
const extract = (start, end) => {
    const a = terminal.indexOf(start), b = terminal.indexOf(end, a);
    if (a < 0 || b <= a) throw new Error('Production renderer boundary changed: ' + start);
    return terminal.slice(a, b);
};
const renderer = extract('function app_window(', 'async function app_progressbar_random(');
const dedupe = extract('function findCameraApplicationWindow(', 'function launchApplicationFromEntry(');
const files = {'/':'index.html', '/preview.js':'preview.js', '/preview.css':'preview.css', '/walowa.jpg':'walowa.jpg'};
const server = http.createServer((req, res) => {
    const route = new URL(req.url, 'http://127.0.0.1').pathname;
    if (req.method !== 'GET' || (!files[route] && route !== '/renderer.js')) {
        res.writeHead(404); return res.end();
    }
    const body = route === '/renderer.js' ? renderer + '\n' + dedupe : fs.readFileSync(path.join(base, files[route]));
    const ext = path.extname(route === '/' ? '.html' : route);
    res.writeHead(200, {'Content-Type': ({'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.jpg':'image/jpeg'})[ext] || 'text/html; charset=utf-8', 'Cache-Control':'no-store'});
    res.end(body);
});
if (require.main === module) server.listen(8999, '127.0.0.1', () => console.log('CVN 164.0: http://127.0.0.1:8999'));
module.exports = {server};
