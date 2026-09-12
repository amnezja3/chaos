/* Existing map block effect, shared without a second animation controller. */
(function(global){
"use strict";
function seed(overlay, doc, random) {
                doc = doc || global.document; random = random || Math.random;
                if (!overlay || overlay.querySelector('.chaos-map-glitch-field')) return;
                const field = doc.createElement('div');
                field.className = 'chaos-map-glitch-field';
                const colors = [
                    'rgba(255, 34, 44, 0.42)',
                    'rgba(38, 255, 106, 0.38)',
                    'rgba(42, 108, 255, 0.36)',
                    'rgba(255, 34, 44, 0.30)',
                    'rgba(38, 255, 106, 0.30)'
                ];
                for (let index = 0; index < 18; index += 1) {
                    const block = doc.createElement('i');
                    block.className = 'chaos-map-glitch-block';
                    const width = Math.round(8 + random() * 90);
                    const height = Math.round(5 + random() * 44);
                    block.style.setProperty('--glitch-x', `${Math.round(random() * 94)}%`);
                    block.style.setProperty('--glitch-y', `${Math.round(random() * 92)}%`);
                    block.style.setProperty('--glitch-w', `${width}px`);
                    block.style.setProperty('--glitch-h', `${height}px`);
                    block.style.setProperty('--glitch-opacity', (0.16 + random() * 0.36).toFixed(2));
                    block.style.setProperty('--glitch-duration', `${(1.7 + random() * 2.4).toFixed(2)}s`);
                    block.style.setProperty('--glitch-delay', `${(-random() * 3.8).toFixed(2)}s`);
                    block.style.setProperty('--glitch-rgb-x', `${Math.round(1 + random() * 4)}px`);
                    block.style.setProperty('--glitch-color', colors[index % colors.length]);
                    block.style.setProperty('--glitch-glow', colors[(index + 1) % colors.length]);
                    field.appendChild(block);
                }
                overlay.appendChild(field);
            };
global.ChaosMapGlitch = {seed:seed};
if(typeof module!=="undefined" && module.exports) module.exports=global.ChaosMapGlitch;
})(typeof window!=="undefined"?window:globalThis);
