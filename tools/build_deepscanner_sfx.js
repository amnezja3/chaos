/* Original, deterministic scanner sounds. No external recordings or dependencies. */
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..', 'static/audio/sfx/scanner');
fs.mkdirSync(root, {recursive:true});
for (const kind of ['sweep', 'ping']) {
    const rate=22050, seconds=2.4, count=Math.round(rate*seconds), buffer=Buffer.alloc(44+count*2);
    buffer.write('RIFF');buffer.writeUInt32LE(buffer.length-8,4);buffer.write('WAVEfmt ',8);
    buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(1,22);
    buffer.writeUInt32LE(rate,24);buffer.writeUInt32LE(rate*2,28);buffer.writeUInt16LE(2,32);
    buffer.writeUInt16LE(16,34);buffer.write('data',36);buffer.writeUInt32LE(count*2,40);
    let phase=0;
    for (let i=0;i<count;i++) {
        const t=i/rate, x=t/seconds, pulse=(t%0.6)/0.6;
        const frequency=kind==='sweep' ? 280+600*x : 660-180*pulse;
        phase+=2*Math.PI*frequency/rate;
        const envelope=Math.min(1,t/0.03,(seconds-t)/0.12)*(kind==='ping' ? Math.exp(-pulse*7) : Math.pow(Math.sin(Math.PI*x),2));
        const sample=(Math.sin(phase)+0.2*Math.sin(phase*2))*0.24*envelope;
        buffer.writeInt16LE(Math.round(sample*32767),44+i*2);
    }
    fs.writeFileSync(path.join(root,`regular_${kind}_v1.wav`),buffer);
}
