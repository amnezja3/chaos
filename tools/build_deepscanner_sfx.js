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

// Eight distinct, bounded PCM phrases. Existing regular v1 assets stay byte-identical.
const variants={pulse:['sonar','heartbeat'],wave:['tide','ripple'],viewfinder:['focus','tracking'],direct:['beam','radar']};
for(const [pattern,names] of Object.entries(variants)) for(const [variant,name] of names.entries()) {
    const rate=22050,seconds=2.4,count=Math.round(rate*seconds),samples=[];
    let phase=0;
    for(let i=0;i<count;i++) {
        const t=i/rate,x=t/seconds;
        let hz=300,env=1;
        if(pattern==='pulse') {const p=t%(variant?0.8:0.6);hz=variant?220:740;env=Math.exp(-p*(variant?12:8));if(variant)env+=0.5*Math.exp(-Math.max(0,p-0.18)*18)*(p>=0.18?1:0);}
        if(pattern==='wave') {hz=220+(variant?220:400)*(0.5-0.5*Math.cos(t*Math.PI*(variant?3:1)));env=0.35+0.65*Math.pow(Math.sin(Math.PI*x),2);}
        if(pattern==='viewfinder') {const p=t%(variant?0.3:0.6);hz=440+110*(Math.floor(t/(variant?0.3:0.6))%4);env=Math.exp(-p*22);}
        if(pattern==='direct') {hz=variant?380+500*(t%0.8)/0.8:180+900*x;env=variant?Math.exp(-(t%0.8)*6):Math.pow(Math.sin(Math.PI*x),0.7);}
        phase+=2*Math.PI*hz/rate;
        samples.push((Math.sin(phase)+0.15*Math.sin(phase*2))*env*Math.min(1,t/0.02,(seconds-t)/0.1));
    }
    const rms=Math.sqrt(samples.reduce((s,v)=>s+v*v,0)/count),peak=Math.max(...samples.map(Math.abs));
    const gain=Math.min(0.09/rms,0.3/peak),buffer=Buffer.alloc(44+count*2);
    buffer.write('RIFF');buffer.writeUInt32LE(buffer.length-8,4);buffer.write('WAVEfmt ',8);
    buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(1,22);
    buffer.writeUInt32LE(rate,24);buffer.writeUInt32LE(rate*2,28);buffer.writeUInt16LE(2,32);
    buffer.writeUInt16LE(16,34);buffer.write('data',36);buffer.writeUInt32LE(count*2,40);
    samples.forEach((sample,i)=>buffer.writeInt16LE(Math.round(sample*gain*32767),44+i*2));
    fs.writeFileSync(path.join(root,`${pattern}_${name}_v1.wav`),buffer);
}
