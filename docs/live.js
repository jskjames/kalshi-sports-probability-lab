'use strict';
(() => {
const data=window.LIVE_MARKET_DATA,$=id=>document.getElementById(id);
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const percent=n=>n==null?'—':(n*100).toFixed(1)+'%';
const cents=n=>n==null?'—':(n*100).toFixed(n*100<10?1:0)+'¢';
const compact=n=>n==null?'—':new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:1}).format(n);
if(!data||!data.latest){
  $('live-status').textContent='NO SNAPSHOT';$('live-status').className='status-pill delayed';
  $('live-updated').textContent='The automated collector has not published data yet.';
  $('live-table').innerHTML='<tr><td colspan="8">Live market data is not available yet.</td></tr>';return;
}
const latest=data.latest,generated=new Date(data.generated_at),now=new Date();
const stale=now-generated>45*60*1000;
$('live-status').textContent=stale?'UPDATE DELAYED':'AUTO-UPDATING';
$('live-status').className='status-pill'+(stale?' delayed':'');
$('live-updated').textContent=`Latest snapshot ${generated.toLocaleString()} · scheduled every ${data.collection_interval_minutes} minutes`;
const allMarkets=latest.events.flatMap(event=>event.markets.map(market=>({event,market})));
const quoted=allMarkets.filter(row=>row.market.probability!=null);
const spreads=quoted.map(row=>row.market.spread).sort((a,b)=>a-b);
const median=spreads.length?(spreads[Math.floor((spreads.length-1)/2)]+spreads[Math.ceil((spreads.length-1)/2)])/2:null;
$('live-events').textContent=latest.events.length.toLocaleString('en-US');
$('live-markets').textContent=allMarkets.length.toLocaleString('en-US');
$('live-quoted').textContent=quoted.length.toLocaleString('en-US');
$('live-spread').textContent=cents(median);
const history=new Map();
for(const snapshot of data.history||[]){
  const time=new Date(snapshot.captured_at).getTime();
  for(const market of snapshot.markets){
    if(!history.has(market.ticker))history.set(market.ticker,[]);
    history.get(market.ticker).push({time,p:market.probability});
  }
}
function movement(ticker,current){
  if(current==null)return null;
  const points=(history.get(ticker)||[]).filter(point=>point.time>=generated.getTime()-24*60*60*1000).sort((a,b)=>a.time-b.time);
  return points.length>1?current-points[0].p:null;
}
function startLabel(value){
  if(!value)return 'Schedule unavailable';
  const date=new Date(value),delta=date-now;
  const status=delta<=0&&delta>-6*60*60*1000?' · open/in progress':'';
  return date.toLocaleString(undefined,{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+status;
}
function render(){
  const q=$('live-search').value.trim().toLowerCase(),windowValue=$('live-window').value;
  const hours=windowValue==='all'?Infinity:Number(windowValue);
  const events=latest.events.filter(event=>{
    const start=event.start_at?new Date(event.start_at):null;
    const delta=start?start-now:Infinity;
    const inWindow=hours===Infinity||(delta<=hours*60*60*1000&&delta>=-6*60*60*1000);
    const haystack=(event.title+' '+event.sub_title+' '+event.event_ticker+' '+event.markets.map(m=>m.team+' '+m.ticker).join(' ')).toLowerCase();
    return inWindow&&(!q||haystack.includes(q));
  });
  const rows=events.flatMap(event=>event.markets.map(market=>({event,market}))).sort((a,b)=>(a.event.start_at||'9999').localeCompare(b.event.start_at||'9999')||b.market.probability-a.market.probability);
  $('live-count').textContent=`${events.length} games · ${rows.length} contracts`;
  $('live-table').innerHTML=rows.map(({event,market})=>{
    const move=movement(market.ticker,market.probability),moveClass=move==null?'':move>0?'up':move<0?'down':'';
    const moveText=move==null?'—':`${move>0?'+':''}${(move*100).toFixed(1)} pts`;
    return `<tr><td><strong>${escape(event.title)}</strong><small>${escape(startLabel(event.start_at))}</small><small>${escape(event.event_ticker)}</small></td><td><strong>${escape(market.team)}</strong><small>${escape(market.ticker)}</small></td><td><div class="probability"><strong>${percent(market.probability)}</strong><span><i style="width:${market.probability==null?0:market.probability*100}%"></i></span></div></td><td class="move ${moveClass}">${moveText}</td><td>${cents(market.bid)} / ${cents(market.ask)}<small>${compact(market.bid_size)} / ${compact(market.ask_size)} contracts</small></td><td>${cents(market.spread)}</td><td>${compact(market.volume_24h)}</td><td>${compact(market.open_interest)}</td></tr>`;
  }).join('');
  $('live-empty').hidden=rows.length>0;
}
['live-window','live-search'].forEach(id=>$(id).addEventListener(id==='live-search'?'input':'change',render));
render();
})();
