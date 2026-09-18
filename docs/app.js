'use strict';
(() => {
const data=window.RESEARCH_DATA,$=id=>document.getElementById(id);
if(!data){document.body.insertAdjacentHTML('afterbegin','<p class="notice">Analysis data is missing. Run the analysis command described in README.md.</p>');return;}
const r=data.report,fmt=n=>Number(n).toLocaleString('en-US'),dec=(n,k=4)=>n==null?'—':Number(n).toFixed(k),pct=n=>n==null?'—':(n*100).toFixed(1)+'%',horizons=['24h','6h','1h','5m'];
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const counts=new Map();for(const x of data.games){if(!counts.has(x.event))counts.set(x.event,new Set());counts.get(x.event).add(x.horizon);}const common=new Set([...counts].filter(([k,v])=>v.size===4).map(([k])=>k));
let limit=30;
const metric=rows=>{if(!rows.length)return {n:0,brier:null,logloss:null,p:null,y:null};let b=0,l=0,p=0,y=0;for(const x of rows){b+=(x.p-x.result)**2;const c=Math.max(1e-6,Math.min(1-1e-6,x.p));l-=x.result*Math.log(c)+(1-x.result)*Math.log(1-c);p+=x.p;y+=x.result;}return {n:rows.length,brier:b/rows.length,logloss:l/rows.length,p:p/rows.length,y:y/rows.length};};
function rowsFor(h,matched=false){return data.games.filter(x=>x.horizon===h&&($('split').value==='all'||x.split===$('split').value)&&(!matched||common.has(x.event)));}
function wilson(w,n){const z=1.95996398454,p=w/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,e=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [c-e,c+e];}
function calibration(rows){if(!rows.length){$('calibration-chart').innerHTML='<p class="empty">No eligible games for these filters.</p>';return;}
const x=p=>55+465*p,y=p=>270-230*p;let svg='<svg viewBox="0 0 560 325" role="img" aria-label="Predicted versus observed home-win probability">';
for(let i=0;i<=5;i++){const p=i/5;svg+=`<line x1="55" y1="${y(p)}" x2="520" y2="${y(p)}" stroke="#e7ebe2"/><text x="43" y="${y(p)+4}" text-anchor="end">${Math.round(p*100)}%</text><text x="${x(p)}" y="291" text-anchor="middle">${Math.round(p*100)}%</text>`;}
svg+='<line x1="55" y1="270" x2="520" y2="40" stroke="#a9b2a5" stroke-dasharray="5 5"/><text x="285" y="319" text-anchor="middle">Mean predicted probability</text><text x="55" y="19">Observed home wins</text>';
const points=[];for(let i=0;i<10;i++){const a=rows.filter(v=>Math.min(9,Math.floor(v.p*10))===i);if(!a.length)continue;const m=metric(a),ci=wilson(a.reduce((s,v)=>s+v.result,0),a.length);points.push(`${x(m.p)},${y(m.y)}`);svg+=`<line x1="${x(m.p)}" x2="${x(m.p)}" y1="${y(ci[0])}" y2="${y(ci[1])}" stroke="#4d8466" stroke-width="1.5"/><circle cx="${x(m.p)}" cy="${y(m.y)}" r="5" fill="#176c4c"><title>${a.length} games; predicted ${pct(m.p)}; observed ${pct(m.y)}</title></circle>`;}
svg+=`<polyline points="${points.join(' ')}" fill="none" stroke="#176c4c" stroke-width="1.5" opacity=".6"/></svg>`;$('calibration-chart').innerHTML=svg;
}
function ledger(rows){const q=$('search').value.toLowerCase();const found=rows.filter(x=>(x.home+' '+x.away+' '+x.event).toLowerCase().includes(q)).sort((a,b)=>b.start_ts-a.start_ts);$('shown-count').textContent=`${fmt(found.length)} matching games · showing ${Math.min(limit,found.length)}`;
$('game-table').innerHTML=found.slice(0,limit).map(x=>`<tr><td>${escape(x.away)} at <strong>${escape(x.home)}</strong><small>${new Date(x.start_ts*1000).toISOString().slice(0,16).replace('T',' ')} UTC</small><small>Cutoff ${new Date(x.target_ts*1000).toISOString().slice(0,16).replace('T',' ')} UTC</small><small>${escape(x.event)}</small></td><td>${pct(x.p)}</td><td>${(x.spread*100).toFixed(1)}¢</td><td>${x.age_seconds}s</td><td><span class="result ${x.result?'':'loss'}">${x.result?'WIN':'LOSS'}</span></td><td>${escape(x.split)}</td></tr>`).join('')||'<tr><td colspan="6">No matching games.</td></tr>';$('show-more').disabled=limit>=found.length;
}
function update(){const rows=rowsFor($('horizon').value,$('common').checked),m=metric(rows);$('brier').textContent=dec(m.brier);$('logloss').textContent=dec(m.logloss);$('sample-n').textContent=fmt(m.n);$('mean-p').textContent=pct(m.p);$('mean-y').textContent=pct(m.y);calibration(rows);ledger(rows);
$('horizon-chart').innerHTML=horizons.map(h=>{const v=metric(rowsFor(h,true));return `<div class="horizon-item"><small>${h.toUpperCase()} BEFORE START</small><strong>${dec(v.brier)}</strong><div class="track"><i style="width:${v.brier==null?0:Math.min(100,v.brier/.35*100)}%"></i></div><em>${v.n} matched games · Brier</em></div>`;}).join('');
const e=r.horizons[$('horizon').value].excluded;$('exclusions').innerHTML=Object.entries(e).map(([k,v])=>`<div class="audit-row"><span>${escape(k.replaceAll('_',' '))}</span><strong>${v}</strong></div>`).join('')||'<p class="caption">No exclusions at this horizon.</p>';
}
$('date-range').textContent=r.start_date+' — '+r.end_date;$('games-count').textContent=fmt(r.games);$('bars-count').textContent=fmt(r.bars);$('snap-count').textContent=fmt(r.snapshots);$('common-count').textContent=fmt(r.common_games);
$('timeline').innerHTML=`<div>TRAIN · FIRST 60% OF DATES<small>${r.start_date} → before ${r.validation_start}</small></div><div>VALIDATE · NEXT 20%<small>${r.validation_start} → before ${r.test_start}</small></div><div>TEST · FINAL 20%<small>${r.test_start} → ${r.end_date}</small></div>`;
const model=r.model,names={market:'Original market midpoint',logistic:'Logistic recalibration',isotonic:'Isotonic recalibration'};
if(model.status==='evaluated'){
const selected=model.selected_on_validation;$('model-verdict').innerHTML=`Validation selected <strong>${names[selected]}</strong>. ${selected==='market'?'Recalibration did not clear the predeclared validation improvement threshold.':'This selection was frozen before evaluating the test period.'} The holdout below is a separate check.`;
$('model-table').innerHTML=Object.entries(model.test).map(([k,v])=>`<tr><td>${names[k]}${k===selected?'<small>Selected on validation</small>':''}</td><td>${v.n}</td><td>${dec(v.brier)}</td><td>${dec(v.log_loss)}</td><td>${dec(v.delta_brier_vs_market)}</td><td>${v.delta_95ci[0]==null?'Insufficient date blocks':dec(v.delta_95ci[0])+' to '+dec(v.delta_95ci[1])}</td></tr>`).join('');
$('model-note').textContent=`${model.train_games} eligible training games; ${model.validation_games} validation games; ${model.refit_games} games in the final refit; ${model.test_games} test games across ${model.test_dates} dates. `+Object.entries(model.unavailable_models).map(([k,v])=>names[k]+': '+v+'.').join(' ');
}else{$('model-verdict').textContent='Too few eligible validation or test games for model comparison.';}
$('sensitivity-table').innerHTML=r.sensitivity.map(v=>`<tr><td>${Math.round(v.max_spread*100)}¢</td><td>${v.max_age_seconds}s</td><td>${v.n}</td><td>${dec(v.brier)}</td></tr>`).join('');
$('collection-note').textContent=`Collection: ${r.collection.selected_events} selected events; ${r.collection.linked_events} linked. Exclusions: ${Object.entries(r.collection.exclusion_counts).map(([k,v])=>k.replaceAll('_',' ')+': '+v).join('; ')||'none'}. ${r.collection.sampling}.`;
['horizon','split','common'].forEach(id=>$(id).addEventListener('change',()=>{limit=30;update();}));$('search').addEventListener('input',()=>{limit=30;update();});$('show-more').addEventListener('click',()=>{limit+=30;update();});update();
})();
