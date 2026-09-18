"""Winner-market snapshots and chronological probability evaluation.

No volume-weighting of outcome scores. One home-team contract per game.
"""
import argparse,json,math,sqlite3
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

HORIZONS={'24h':86400,'6h':21600,'1h':3600,'5m':300}
SEED=20260917

def number(d,new,old):
    v=d.get(new,d.get(old))
    if v is None:return None
    v=float(v)
    return v if math.isfinite(v) else None

def normalize_bar(c):
    """Historical prices are dollar strings even without the _dollars suffix."""
    return {'event':c['event'],'end_ts':int(c['end_period_ts']),
      'bid':number(c.get('yes_bid',{}),'close_dollars','close'),
      'ask':number(c.get('yes_ask',{}),'close_dollars','close'),
      'trade':number(c.get('price',{}),'close_dollars','close'),
      'volume':number(c,'volume_fp','volume') or 0}

def snapshot(game,bars,horizon,max_age=120,max_spread=.10):
    target=game['start_ts']-HORIZONS[horizon]
    prior=[b for b in bars if b['end_ts']<=target]
    base={'event':game['event'],'horizon':horizon,'target_ts':target}
    if not prior:return base|{'reason':'no_prior_bar'}
    # Never walk backwards to conceal an invalid latest quote.
    b=max(prior,key=lambda x:x['end_ts']); age=target-b['end_ts']
    if age>max_age:return base|{'reason':'bar_too_old','age_seconds':age}
    bid,ask=b['bid'],b['ask']
    if bid is None or ask is None or not (0<bid<=ask<1):return base|{'reason':'invalid_quote'}
    spread=ask-bid
    if spread>max_spread+1e-12:return base|{'reason':'wide_spread','spread':spread}
    recent=[x for x in prior if x['end_ts']>target-3600]
    return base|{'reason':'included','bar_ts':b['end_ts'],'age_seconds':age,'p':(bid+ask)/2,
        'bid':bid,'ask':ask,'spread':spread,'trade_p':b['trade'] if b['volume']>0 else None,
        'contracts_last_hour':sum(x['volume'] for x in recent),
        'active_minutes_last_hour':sum(x['volume']>0 for x in recent)}

def scores(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    if not len(y):return {'n':0,'brier':None,'log_loss':None}
    if not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid probability or outcome')
    pc=np.clip(p,1e-6,1-1e-6)
    return {'n':len(y),'brier':float(np.mean((p-y)**2)),'log_loss':float(-np.mean(y*np.log(pc)+(1-y)*np.log(1-pc)))}

def wilson(w,n):
    if n==0:return [None,None]
    z=1.95996398454;p=w/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(center-half),float(center+half)]

def calibration(y,p):
    y=np.asarray(y);p=np.asarray(p);buckets=np.minimum((p*10).astype(int),9);out=[]
    for b in range(10):
        mask=buckets==b;n=int(mask.sum())
        if n:out.append({'bucket':b,'n':n,'predicted':float(p[mask].mean()),'observed':float(y[mask].mean()),'wilson':wilson(int(y[mask].sum()),n)})
    return out

def day_bootstrap(frame, values, repetitions=2000):
    """Resample UTC game dates as blocks; paired values stay together."""
    days=frame['day'].to_numpy();values=np.asarray(values,float)
    if len(set(days))<5:return [None,None]
    groups=[values[days==d] for d in sorted(set(days))]
    sums=np.array([x.sum() for x in groups]);counts=np.array([len(x) for x in groups])
    rng=np.random.default_rng(SEED);ix=rng.integers(0,len(groups),(repetitions,len(groups)))
    means=sums[ix].sum(axis=1)/counts[ix].sum(axis=1)
    return [float(x) for x in np.quantile(means,[.025,.975])]

def date_splits(games):
    dates=sorted(games['day'].unique())
    if len(dates)<10:raise ValueError('At least 10 distinct game dates are required')
    a=dates[max(1,int(len(dates)*.6))];b=dates[max(2,int(len(dates)*.8))]
    return a,b

def logit(p):
    p=np.clip(np.asarray(p,float),1e-6,1-1e-6)
    return np.log(p/(1-p)).reshape(-1,1)

def fit_predict(kind,train,test):
    if kind=='market':return test.p.to_numpy(),{}
    if len(train)<50 or train.result.nunique()<2:raise ValueError('Insufficient training sample')
    if kind=='logistic':
        m=LogisticRegression(C=1.0,solver='lbfgs',random_state=SEED).fit(logit(train.p),train.result)
        return m.predict_proba(logit(test.p))[:,1],{'intercept':float(m.intercept_[0]),'slope':float(m.coef_[0,0])}
    if kind=='isotonic':
        if len(train)<1000:raise ValueError('Isotonic requires at least 1000 training games by project policy')
        m=IsotonicRegression(out_of_bounds='clip').fit(train.p,train.result)
        return m.predict(test.p),{}
    raise ValueError('Unknown model')

def purge_resolutions(train,evaluation):
    return train[train.settled_ts<evaluation.target_ts.min()].copy()

def model_evaluation(df):
    train=df[df.split=='train'];val=df[df.split=='validation'];test=df[df.split=='test']
    if len(val)<20 or len(test)<20:return {'status':'insufficient_evaluation_sample'},[]
    train=purge_resolutions(train,val)
    validation={};preds={};errors={}
    for kind in ['market','logistic','isotonic']:
        try:
            p,_=fit_predict(kind,train,val);validation[kind]=scores(val.result,p)
        except ValueError as e:errors[kind]=str(e)
    # Pick on validation only, retain market unless improvement exceeds 0.002 Brier.
    selected='market'
    for kind in ['logistic','isotonic']:
        if kind in validation and validation[kind]['brier']<validation[selected]['brier']-.002:selected=kind
    fitting=purge_resolutions(df[df.split!='test'],test)
    model_parameters={}
    # Report prespecified comparator too, without reselecting on held-out results.
    for kind in ['market','logistic','isotonic']:
        if kind not in validation:continue
        p,params=fit_predict(kind,fitting,test);preds[kind]=p;model_parameters[kind]=params
    result={'status':'evaluated','selected_on_validation':selected,'train_games':len(train),'validation_games':len(val),'refit_games':len(fitting),'test_games':len(test),'test_dates':int(test.day.nunique()),'validation':validation,'unavailable_models':errors,'parameters':model_parameters,'test':{}}
    for kind,p in preds.items():
        loss=(p-test.result.to_numpy())**2;delta=loss-(test.p-test.result).to_numpy()**2
        result['test'][kind]=scores(test.result,p)|{'brier_95ci':day_bootstrap(test,loss),'delta_brier_vs_market':float(delta.mean()),'delta_95ci':day_bootstrap(test,delta),'calibration':calibration(test.result,p)}
    exported=[]
    for i,(_,row) in enumerate(test.iterrows()):exported.append({'event':row.event,'day':row.day,'result':int(row.result),**{k:float(v[i]) for k,v in preds.items()}})
    return result,exported

def run(root,league='NBA'):
    root=Path(root);processed=root/'data'/'processed';out=root/'outputs';out.mkdir(exist_ok=True)
    games=pd.DataFrame(json.loads((processed/f'{league}_games.json').read_text()))
    games['day']=pd.to_datetime(games.start_ts,unit='s',utc=True).dt.strftime('%Y-%m-%d')
    a,b=date_splits(games);games['split']=np.where(games.day<a,'train',np.where(games.day<b,'validation','test'))
    bars=[normalize_bar(json.loads(line)) for line in (processed/f'{league}_bars.jsonl').open()]
    grouped=defaultdict(list)
    for bar in bars:grouped[bar['event']].append(bar)
    records=[];audit=[]
    for game in games.to_dict('records'):
        for h in HORIZONS:
            snap=snapshot(game,grouped[game['event']],h);audit.append(snap)
            if snap['reason']=='included':records.append(game|snap)
    df=pd.DataFrame(records)
    if df.empty:
        pd.DataFrame(audit).to_csv(out/'snapshot_audit.csv',index=False)
        raise ValueError('No eligible snapshots; inspect outputs/snapshot_audit.csv')
    df.to_csv(out/'snapshots.csv',index=False);pd.DataFrame(audit).to_csv(out/'snapshot_audit.csv',index=False)
    games.to_csv(out/'games.csv',index=False)
    database=root/'data'/'warehouse.sqlite'
    building=database.with_name('warehouse.building.sqlite')
    if building.exists():building.unlink()
    connection=sqlite3.connect(building)
    games.to_sql('games',connection,if_exists='replace',index=False)
    pd.DataFrame(bars).to_sql('bars',connection,if_exists='replace',index=False)
    df.drop(columns=[c for c in games.columns if c!='event']).to_sql('snapshots',connection,if_exists='replace',index=False)
    pd.DataFrame(audit).to_sql('snapshot_audit',connection,if_exists='replace',index=False)
    connection.executescript('CREATE UNIQUE INDEX IF NOT EXISTS game_id ON games(event); CREATE UNIQUE INDEX IF NOT EXISTS bar_time ON bars(event,end_ts); CREATE UNIQUE INDEX IF NOT EXISTS snapshot_id ON snapshots(event,horizon);')
    connection.commit()
    expected={'games':len(games),'bars':len(bars),'snapshots':len(df),'snapshot_audit':len(audit)}
    actual={table:connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in expected}
    if actual!=expected:raise RuntimeError(f'Warehouse row-count verification failed: expected {expected}, got {actual}')
    connection.close()
    building.replace(database)
    common=set.intersection(*(set(df.loc[df.horizon==h,'event']) for h in HORIZONS))
    horizons={}
    for h in HORIZONS:
        subset=df[df.horizon==h];matched=subset[subset.event.isin(common)]
        horizons[h]={'available':scores(subset.result,subset.p),'common_cohort':scores(matched.result,matched.p),'calibration':calibration(subset.result,subset.p),'excluded':dict(Counter(x['reason'] for x in audit if x['horizon']==h and x['reason']!='included'))}
    primary=df[df.horizon=='1h'].copy();model,predictions=model_evaluation(primary)
    sensitivity=[]
    for spread in [.05,.10,.20]:
        for age in [60,120,300]:
            rows=[]
            for g in games.to_dict('records'):
                s=snapshot(g,grouped[g['event']],'1h',age,spread)
                if s['reason']=='included':rows.append((g['result'],s['p']))
            sensitivity.append({'max_spread':spread,'max_age_seconds':age,**scores([r[0] for r in rows],[r[1] for r in rows])})
    paired=primary[primary.trade_p.notna()]
    price_comparison={'games':len(paired),'midpoint':scores(paired.result,paired.p),'same_bar_trade':scores(paired.result,paired.trade_p)}
    subgroups=[]
    for name,mask in [('spread ≤ 2¢',primary.spread<=.02000001),('spread > 2¢',primary.spread>.02000001),('no trades in previous hour',primary.contracts_last_hour==0),('trades in previous hour',primary.contracts_last_hour>0)]:
        d=primary[mask];subgroups.append({'group':name,**scores(d.result,d.p)})
    report={'league':league,'games':len(games),'bars':len(bars),'snapshots':len(df),'start_date':games.day.min(),'end_date':games.day.max(),'validation_start':a,'test_start':b,'common_games':len(common),'horizons':horizons,'model':model,'sensitivity':sensitivity,'price_comparison':price_comparison,'subgroups':subgroups,'collection':json.loads((processed/f'{league}_collection.json').read_text()),'caveats':['Retrospective milestone start dates; actual tipoff and schedule revision history not independently verified.','Minute bars provide quote observations, not true last quote-update timestamps or historical depth.','Capped recent settled cohort, not full-season or random sampling.','Calibration uses home-team win outcomes. No user P&L, fees, execution, or profitability is estimated.','Intervals resample UTC dates; dependence across dates or recurring teams may remain.','Date-blocked validation can cross regular-season/playoff regimes; performance is not guaranteed to generalize.']}
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pd.DataFrame(predictions).to_csv(out/'holdout_predictions.csv',index=False)
    data={'report':report,'games':df.replace({np.nan:None}).to_dict('records'),'holdout':predictions}
    (root/'docs'/'data.js').write_text('window.RESEARCH_DATA = '+json.dumps(data,allow_nan=False)+';\n')
    from .reporting import write_findings
    write_findings(root,report)
    print(json.dumps({k:report[k] for k in ['games','bars','snapshots','common_games','start_date','end_date','model']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--league',default='NBA');a=p.parse_args();run(a.root,a.league)
