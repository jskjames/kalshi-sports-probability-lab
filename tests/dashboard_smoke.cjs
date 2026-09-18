// Executes the dashboard controller against a minimal DOM contract, not a browser.
// This checks data binding and filter logic; it does not validate visual rendering.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'docs/index.html'),'utf8');
const ids=[...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
const elements=Object.fromEntries(ids.map(id=>[id,{innerHTML:'',textContent:'',value:'',checked:false,disabled:false,listeners:{},addEventListener(event,callback){this.listeners[event]=callback;}}]));
elements.horizon.value='1h';elements.split.value='all';
const context={window:{},document:{getElementById(id){assert.ok(elements[id],`Unknown DOM ID: ${id}`);return elements[id];},body:{insertAdjacentHTML(){throw Error('Missing analysis data');}}},console};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'docs/data.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'docs/app.js'),'utf8'),context);
const data=context.window.RESEARCH_DATA;
assert.equal(Number(elements['sample-n'].textContent.replaceAll(',','')),data.report.horizons['1h'].available.n);
assert.equal(elements.brier.textContent,data.report.horizons['1h'].available.brier.toFixed(4));
assert.ok(elements['calibration-chart'].innerHTML.includes('<svg'));
elements.split.value='test';elements.split.listeners.change();
assert.equal(Number(elements['sample-n'].textContent.replaceAll(',','')),data.games.filter(x=>x.horizon==='1h'&&x.split==='test').length);
elements.horizon.value='24h';elements.horizon.listeners.change();
assert.equal(Number(elements['sample-n'].textContent.replaceAll(',','')),data.games.filter(x=>x.horizon==='24h'&&x.split==='test').length);
elements.common.checked=true;elements.common.listeners.change();
assert.ok(Number(elements['sample-n'].textContent.replaceAll(',',''))<=data.report.common_games);
elements.search.value='NONEXISTENT_TEAM_783';elements.search.listeners.input();
assert.ok(elements['game-table'].innerHTML.includes('No matching games'));
assert.ok(elements['show-more'].disabled);
assert.ok(!elements['model-table'].innerHTML.includes('NaN'));
console.log('PASS: dashboard binding, source metric parity, period/horizon/cohort filters and empty search. Visual rendering not tested.');
