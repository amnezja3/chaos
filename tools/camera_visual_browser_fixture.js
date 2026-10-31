// Compatibility launcher for the original 164.0 review command.
const path = require('node:path');
const {spawn} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const python = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const child = spawn(python, [path.join(__dirname, 'camera_visual_browser_fixture.py'), ...process.argv.slice(2)], {stdio:'inherit', cwd:root});
child.on('error', error => {console.error(error.message); process.exitCode=1;});
child.on('exit', code => {process.exitCode=code || 0;});
process.on('SIGINT',()=>child.kill('SIGINT'));
