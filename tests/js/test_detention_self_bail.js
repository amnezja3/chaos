const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let posts=[], dialogs=[], accepted=true, hold;
let sentence={sanction_id:'own-sentence',duration_seconds:600,bail_hc:500000,prison_name:'Prison',private_messages_remaining:1};
let canPay=false;
const context={window:{showGhostDecisionDialog: async opts => {
    dialogs.push(opts);
    if (hold) await hold;
    return accepted;
}}, fetch:async (url,opts) => {
    if (opts?.method==='POST') posts.push(JSON.parse(opts.body));
    return {ok:true,json:async()=>url.includes('bail_offer=1')
        ? {detention:sentence,bail_offer:{can_pay:canPay}}
        : url.endsWith('/bail') ? {paid:true} : {detention:null}};
}};
vm.runInNewContext(fs.readFileSync('static/js/detention.js','utf8'),context);
const ui=context.window.DetentionUI;
(async()=>{
    await ui.blockedAction();
    assert.equal(dialogs[0].showConfirm,false);
    assert(dialogs[0].message.includes('10 min więzienia w zakładzie karnym Prison'));
    assert(dialogs[0].details.includes('jedną wiadomość'));
    assert.equal(posts.length,0,'even an accepted information dialog cannot pay');
    dialogs=[]; sentence={...sentence,private_messages_remaining:0};
    await ui.blockedAction();
    assert(dialogs[0].details.includes('już wykorzystana'));
    dialogs=[]; canPay=true; accepted=false;
    await ui.blockedAction(); assert.equal(posts.length,0);
    assert.equal(dialogs[0].showConfirm,true);
    dialogs=[]; accepted=true;
    let release; hold=new Promise(resolve=>{release=resolve;});
    const first=ui.blockedAction();
    await new Promise(resolve=>setImmediate(resolve));
    await ui.blockedAction();
    assert.equal(dialogs.length,1,'simultaneous denials only open one dialog');
    hold=null; release(); await first;
    assert.equal(posts.length,1);
    assert.equal(posts[0].sanction_id,'own-sentence');
    posts=[]; dialogs=[]; sentence=null;
    await ui.blockedAction(); assert.equal(dialogs.length,0); assert.equal(posts.length,0);
    console.log('self bail affordability, allowance, cancellation and concurrent prompts: OK');
})().catch(err=>{console.error(err);process.exitCode=1;});
