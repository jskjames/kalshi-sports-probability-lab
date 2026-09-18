"""Capture market metadata, a linked schedule, and pre-start minute bars."""
import argparse, json, concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter
from .client import Client
from .markets import get_adapter
SERIES={'NBA':'KXNBAGAME','MLB':'KXMLBGAME','NFL':'KXNFLGAME','NHL':'KXNHLGAME'}
def ts(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp())
def iso(n):return datetime.fromtimestamp(n,timezone.utc).isoformat()

def collect(root,league='NBA',max_games=500):
    root=Path(root); out=root/'data'/'processed';out.mkdir(parents=True,exist_ok=True)
    client=Client(root/'data'/'cache'); series=SERIES[league]
    cutoff=client.get('/historical/cutoff'); threshold=ts(cutoff['market_settled_ts'])
    # Freeze one discovery page from each tier; record that this is a capped recent cohort.
    markets={}
    discovery=[]
    for path,params in [('/markets',{'status':'settled'}),('/historical/markets',{})]:
        page=client.get(path,series_ticker=series,limit=1000,**params)
        discovery.append({'endpoint':path,'rows':len(page.get('markets',[])),'more_available':bool(page.get('cursor'))})
        for m in page.get('markets',[]): markets[m['ticker']]=m
    groups=defaultdict(list)
    for m in markets.values():groups[m['event_ticker']].append(m)
    selected=sorted(groups,key=lambda e:max(m.get('settlement_ts','') for m in groups[e]),reverse=True)[:max_games]
    games=[];bars=[];exclusions=[]
    def one(event):
        ms=groups[event]
        reason=get_adapter('winner').exclusion_reason(ms)
        if reason:return None,[],{'event':event,'reason':reason}
        milestones=client.get('/milestones',limit=100,related_event_ticker=event).get('milestones',[])
        linked=[x for x in milestones if event in x.get('related_event_tickers',[])+x.get('primary_event_tickers',[])]
        if len(linked)!=1:return None,[],{'event':event,'reason':'missing_or_ambiguous_schedule'}
        milestone=linked[0];detail=milestone.get('details',{})
        home=detail.get('home_team_id'); away=detail.get('away_team_id')
        home_ms=[m for m in ms if home and home in m.get('custom_strike',{}).values()]
        away_ms=[m for m in ms if away and away in m.get('custom_strike',{}).values()]
        if len(home_ms)!=1 or len(away_ms)!=1 or home==away:
            return None,[],{'event':event,'reason':'unmapped_home_away'}
        m=home_ms[0];start=ts(milestone['start_date'])
        if start>=ts(m['settlement_ts']):return None,[],{'event':event,'reason':'start_after_settlement'}
        archived=ts(m['settlement_ts'])<threshold
        path=f"/historical/markets/{m['ticker']}/candlesticks" if archived else f"/series/{series}/markets/{m['ticker']}/candlesticks"
        candles=client.get(path,start_ts=start-25*3600,end_ts=start-1,period_interval=1).get('candlesticks',[])
        # No fields containing post-event player form/injuries enter model inputs.
        game={'event':event,'ticker':m['ticker'],'league':league,'market_type':'winner','home':m['yes_sub_title'],'away':away_ms[0]['yes_sub_title'],'start_ts':start,'start_utc':iso(start),'schedule_source':'kalshi_milestone_start_date','schedule_updated_at':milestone.get('last_updated_ts'),'milestone_id':milestone['id'],'result':int(m['result']=='yes'),'settled_ts':ts(m['settlement_ts']),'occurrence_ts':ts(m['occurrence_datetime']) if m.get('occurrence_datetime') else None,'archived':archived,'bar_count':len(candles)}
        bs=[{'event':event,**c} for c in candles]
        return game,bs,None
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(one,e):e for e in selected}
        for i,f in enumerate(concurrent.futures.as_completed(futures),1):
            try:
                g,b,e=f.result()
                if g:games.append(g);bars.extend(b)
                if e:exclusions.append(e)
            except Exception as e:exclusions.append({'event':futures[f],'reason':'api_error','detail':str(e)})
            if i%20==0 or i==len(selected): print(f'{league}: {i}/{len(selected)} events; {len(games)} linked; {len(bars)} bars; {len(exclusions)} excluded',flush=True)
    games.sort(key=lambda g:(g['start_ts'],g['event']));bars.sort(key=lambda c:(c['event'],c['end_period_ts']))
    (out/f'{league}_games.json').write_text(json.dumps(games))
    with (out/f'{league}_bars.jsonl').open('w') as f:
        for b in bars:f.write(json.dumps(b)+'\n')
    report={'league':league,'collected_at':datetime.now(timezone.utc).isoformat(),'cutoff':cutoff,'discovery':discovery,'discovered_markets':len(markets),'discovered_events':len(groups),'selected_events':len(selected),'linked_events':len(games),'bars':len(bars),'exclusion_counts':dict(Counter(e['reason'] for e in exclusions)),'exclusions':exclusions,'sampling':'Latest settlement timestamps, capped before exclusions; one 1000-market page per tier','start_time_limitation':'Latest retrospective scheduled start, not independently verified actual tipoff; schedule revision history unavailable.'}
    (out/f'{league}_collection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report|{'exclusions':len(exclusions)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--league',choices=SERIES,default='NBA');p.add_argument('--max-games',type=int,default=500)
    a=p.parse_args();collect(a.root,a.league,a.max_games)
