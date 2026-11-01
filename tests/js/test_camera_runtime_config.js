'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const modulePath=require.resolve('../../camera.runtime.config.js');
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'chaos-camera-config-'));
const old=process.env.CHAOS_CAMERA_CONFIG;
const read=value=>{
    fs.writeFileSync(path.join(directory,'config.json'),JSON.stringify(value));
    process.env.CHAOS_CAMERA_CONFIG=path.join(directory,'config.json');
    delete require.cache[modulePath];return require(modulePath);
};
try {
    const config=read({CHAOS_CAMERA_STREET_VIEW:1,CHAOS_CAMERA_WORKER:1,CHAOS_CAMERA_ACQUISITION:1,CHAOS_CAMERA_SERVE:1,CHAOS_DB_PATH:'/private/game.sqlite3'});
    const web=config('web'),operations=config('operations'),archive=config('archive');
    for(const role of [web,operations,archive]){
        assert.equal(role.CHAOS_DB_PATH,path.resolve('/private/game.sqlite3'));
        assert.equal(role.CHAOS_CAMERA_STREET_VIEW,'1');
    }
    assert.equal(web.CHAOS_CAMERA_WORKER,'0');assert.equal(web.CHAOS_CAMERA_SERVE,'1');
    assert.equal(operations.CHAOS_CAMERA_WORKER,'0');assert.equal(operations.CHAOS_CAMERA_ACQUISITION,'0');
    assert.equal(archive.CHAOS_CAMERA_WORKER,'1');assert.equal(archive.CHAOS_CAMERA_SERVE,'0');
    for(const invalid of [{MAPILLARY_ACCESS_TOKEN:'no-secrets-in-config'},[],null,{CHAOS_CAMERA_WORKER:'yes'},{CHAOS_CAMERA_MAX_BYTES:-1},{CHAOS_CAMERA_SOURCE:'unknown'}])assert.throws(()=>read(invalid));
    assert.throws(()=>config('typo'));
    console.log('PASS shared camera configuration, role fences, invalid settings');
} finally {
    if(old===undefined)delete process.env.CHAOS_CAMERA_CONFIG;else process.env.CHAOS_CAMERA_CONFIG=old;
    fs.unlinkSync(path.join(directory,'config.json'));fs.rmdirSync(directory);
}
