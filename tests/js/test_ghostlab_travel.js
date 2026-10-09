'use strict';
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('static/js/terminal.js', 'utf8').replace(/\r\n/g, '\n');
function extract(name) {
    const start = source.indexOf(`function ${name}(`);
    const end = source.indexOf('\nfunction ', start + 1);
    assert(start >= 0 && end > start);
    return source.slice(start, end);
}
class Node {
    constructor(tag) { this.tag = tag; this.children = []; this.attrs = {}; this.style = {}; this.events = {}; this.dataset = {}; }
    set innerHTML(value) { this.html = value; this.children = []; this.text = String(value).replace(/<[^>]*>/g, '').replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&'); }
    get innerHTML() { return this.html || ''; }
    set textContent(value) { this.text = value; this.children = []; }
    get textContent() { return this.text || ''; }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren(...nodes) { this.children = nodes; }
    setAttribute(key,value) { this.attrs[key] = value; }
    addEventListener(event,handler) { this.events[event] = handler; }
    querySelectorAll(tag) { return this.children.flatMap(n => [...(n.tag === tag ? [n] : []), ...n.querySelectorAll(tag)]); }
}
const state = {success:true,offer:{destination:{place_name:'<img onerror=bad>',city:'Ostrowiec',country:'Polska',lat:50,lng:21},destination_revision:'place-1'},
    counts:{bad:0,happy:0,very_happy:0},historical_counts:{bad:2,happy:0,very_happy:0},mine:null,reaction_receipt:null};
const calls = [];
const context = {document:{createElement:tag => new Node(tag)},encodeURIComponent,
    escapeHTML: value => String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'),
    fetch:async(url,options) => {
        calls.push({url,options});
        if (options?.method === 'POST') {
            const data = JSON.parse(options.body);
            assert.equal(data.receipt,'confirmed-trip');
            state.mine = {reaction:data.reaction,destination_revision:'place-1'};
            state.counts = {bad:0,happy:0,very_happy:0}; state.counts[data.reaction] = 1;
        }
        return {ok:true,json:async()=>state};
    }};
vm.createContext(context);
require('./locale_fixture')(context);
vm.runInContext(extract('mountTravelTicketReactions'),context);
(async()=>{
    const card = new Node('article');
    context.mountTravelTicketReactions(card,{id:'ghostlab_ticket',ghostlab_generated:true});
    await card._refreshTravelReactions();
    let buttons = card.querySelectorAll('button');
    assert.equal(buttons.length,3);
    assert(buttons.every(b=>b.disabled),'no trip means no voting');
    assert(card.querySelectorAll('p')[0].textContent.includes('<img onerror=bad>'),'author text stays literal');
    assert.equal(card.querySelectorAll('img').length,0);
    assert(!card.querySelectorAll('p')[0].textContent.includes('(50, 21)'), 'no coordinates in public ticket text');
    state.reaction_receipt = 'confirmed-trip';
    await card._refreshTravelReactions();
    buttons = card.querySelectorAll('button');
    assert(buttons.every(b=>!b.disabled));
    await buttons[1].events.click();
    assert.equal(card.querySelectorAll('button')[1].attrs['aria-pressed'],'true');
    await card.querySelectorAll('button')[0].events.click();
    assert.equal(Object.values(state.counts).reduce((a,b)=>a+b,0),1);
    state.reaction_receipt = null;
    state.reaction_blocked_reason = 'own_ticket';
    await card._refreshTravelReactions();
    assert(card.querySelectorAll('button').every(b=>b.disabled));
    assert(card.querySelectorAll('p').some(p=>p.textContent.includes('Nie możesz ocenić własnego biletu.')));
    assert(calls.every(c=>c.url.startsWith('/api/travel-tickets/')),'feedback never loads a profile');
    const publisher = {escapeHTML:String}; vm.createContext(publisher);
    require('./locale_fixture')(publisher);
    vm.runInContext(extract('renderGhostLabPublisherPipeline'),publisher);
    const html = publisher.renderGhostLabPublisherPipeline({template_id:'travel_ticket',status:'published',revision:1,
        artifact:{artifact_id:'a',version:1},published_artifact_id:'a',publisher_contract:{runtime_status:'purchase_travel'}});
    assert(html.includes('jeden zakup wykonuje jedną podróż'));
    assert(!html.includes('W zainstalowanej aplikacji'));
    console.log('GhostLab travel reactions and publisher: PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
