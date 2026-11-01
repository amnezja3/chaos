// One configuration projection shared by web, operations and image workers.
// Optional private JSON contains deployment settings; never commit credentials.
const fs = require('fs');
const path = require('path');
const defaults = {
    CHAOS_CAMERA_STREET_VIEW:'0', CHAOS_CAMERA_VISUAL_PILOT:'0',
    CHAOS_CAMERA_VISUAL_PILOT_USER:'main', CHAOS_CAMERA_SOURCE:'off',
    CHAOS_CAMERA_SERVE:'0', CHAOS_CAMERA_ACQUISITION:'0', CHAOS_CAMERA_WORKER:'0',
    CHAOS_CAMERA_RETENTION_SECONDS:'0', CHAOS_CAMERA_MAX_REQUESTS:'100',
    CHAOS_CAMERA_MAX_BYTES:'104857600', CHAOS_CAMERA_MAX_ARCHIVES:'1000',
    CHAOS_CAMERA_MAX_STORAGE_BYTES:'1073741824', CHAOS_CAMERA_DIAGNOSTICS:'0',
    CHAOS_DB_PATH:path.join(__dirname,'data/game.sqlite3'),
    CHAOS_CAMERA_ARCHIVE_DIR:path.join(__dirname,'data/camera_visual')
};
const filename = process.env.CHAOS_CAMERA_CONFIG;
const privateSettings = filename ? JSON.parse(fs.readFileSync(filename,'utf8')) : {};
if (!privateSettings || Array.isArray(privateSettings) || typeof privateSettings !== 'object')
    throw new Error('Camera configuration must be an object');
for (const key of Object.keys(privateSettings)) {
    if (!(key in defaults) && !['CHAOS_CAMERA_ARCHIVE_DIR','CHAOS_CAMERA_CDN_HOSTS',
        'CHAOS_CAMERA_RIGHTS_REFERENCE','CHAOS_CAMERA_LICENSE','CHAOS_CAMERA_LICENSE_URL',
        'CHAOS_DB_PATH'].includes(key)) throw new Error('Unsupported camera setting: '+key);
}
const settings = Object.fromEntries(Object.entries({...defaults,...privateSettings}).map(([k,v])=>[k,String(v)]));
for (const key of ['CHAOS_DB_PATH','CHAOS_CAMERA_ARCHIVE_DIR']) {
    if (!settings[key].trim()) throw new Error('Empty camera path: '+key);
    settings[key]=path.resolve(__dirname,settings[key]);
}
for (const key of ['CHAOS_CAMERA_STREET_VIEW','CHAOS_CAMERA_VISUAL_PILOT','CHAOS_CAMERA_SERVE',
    'CHAOS_CAMERA_ACQUISITION','CHAOS_CAMERA_WORKER','CHAOS_CAMERA_DIAGNOSTICS']) {
    if (!['0','1'].includes(settings[key])) throw new Error('Invalid camera flag: '+key);
}
for (const key of ['CHAOS_CAMERA_RETENTION_SECONDS','CHAOS_CAMERA_MAX_REQUESTS','CHAOS_CAMERA_MAX_BYTES',
    'CHAOS_CAMERA_MAX_ARCHIVES','CHAOS_CAMERA_MAX_STORAGE_BYTES']) {
    if (!/^\d+$/.test(settings[key]) || !Number.isSafeInteger(Number(settings[key])))
        throw new Error('Invalid camera limit: '+key);
}
if (!['off','fixture','mapillary'].includes(settings.CHAOS_CAMERA_SOURCE)) throw new Error('Invalid camera source');
module.exports = role => {
    if (!['web','operations','archive'].includes(role)) throw new Error('Invalid camera process role');
    return {...settings,
    CHAOS_CAMERA_WORKER:role==='archive' ? settings.CHAOS_CAMERA_WORKER : '0',
    CHAOS_CAMERA_ACQUISITION:role==='archive' ? settings.CHAOS_CAMERA_ACQUISITION : '0',
    CHAOS_CAMERA_SERVE:role==='web' ? settings.CHAOS_CAMERA_SERVE : '0',
    CHAOS_CAMERA_ROLE:role
};
};
