// Prepared only; starting this process is a separate deployment decision.
module.exports = {apps:[{
  name:'chaos-camera-archive', cwd:'/home/johndoe/app/chaos',
  script:'/home/johndoe/app/chaos/.venv/bin/python', interpreter:'none',
  args:'tools/camera_archive.py --db data/game.sqlite3 --action work-once --apply',
  autorestart:false, cron_restart:'*/2 * * * *', instances:1,
  env:{CHAOS_CAMERA_WORKER:'0',CHAOS_CAMERA_ACQUISITION:'0',CHAOS_CAMERA_SERVE:'0',
    CHAOS_CAMERA_SOURCE:'off',CHAOS_CAMERA_RETENTION_SECONDS:'0',
    CHAOS_CAMERA_MAX_REQUESTS:'100',CHAOS_CAMERA_MAX_BYTES:'104857600',CHAOS_CAMERA_MAX_ARCHIVES:'10'}
}]};
