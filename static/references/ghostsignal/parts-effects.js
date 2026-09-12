/* Reference-only ambient preview. No game state, API, audio or trigger. */
(function () {
    "use strict";
    const scene = document.querySelector('.parts-scene');
    const glitch = document.querySelector('.parts-glitch');
    if (!scene) return;
    let seed = 139140;
    if (glitch && window.ChaosMapGlitch) window.ChaosMapGlitch.seed(glitch, document, function () {
        seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
        return seed / 4294967296;
    });
    document.querySelectorAll('.part').forEach(function (part, index) {
        part.style.setProperty('--fx-offset', (index * 2.4) + 's');
    });
    const origin = performance.now();
    const start = Number(scene.getAttribute('data-ambient-start')) || 75;
    let timer = null;
    function tick() {
        const elapsed = start + (performance.now() - origin) / 1000;
        scene.style.setProperty('--fx-clock', -elapsed + 's');
        scene.style.setProperty('--light', (0.5 - 0.5 * Math.cos(elapsed * Math.PI * 2 / 5.4)).toFixed(4));
        if (glitch) glitch.className = 'chaos-map-glitch-overlay is-visible parts-glitch is-slow'
            + (elapsed % 12 >= 7 ? ' is-heavy is-overloaded' : '');
    }
    function stop() { clearInterval(timer); timer = null; }
    function resume() { stop(); tick(); if (!document.hidden) timer = setInterval(tick, 1000); }
    document.addEventListener('visibilitychange', resume);
    window.addEventListener('pagehide', stop);
    window.addEventListener('pageshow', resume);
    resume();
})();
