// Prepared only; starting this process is a separate deployment decision.
module.exports = {apps:[{
  name:'chaos-camera-archive', cwd:'/home/johndoe/app/chaos',
  script:'/home/johndoe/app/chaos/.venv/bin/python', interpreter:'none',
  args:'tools/camera_archive.py --action work-loop --apply',
  autorestart:true, restart_delay:5000, instances:1,
  env:require('./camera.runtime.config.js')('archive')
}]};
