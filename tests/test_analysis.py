import unittest
import pandas as pd
import numpy as np
from kalshi_lab.analysis import normalize_bar,snapshot,scores,wilson,date_splits,purge_resolutions,day_bootstrap,fit_predict

class ResearchTests(unittest.TestCase):
    def test_historical_and_live_dollars(self):
        old={'event':'a','end_period_ts':10,'yes_bid':{'close':'0.58'},'yes_ask':{'close':'0.62'},'price':{'close':'0.60'},'volume':'2.50'}
        new={'event':'a','end_period_ts':10,'yes_bid':{'close_dollars':'0.58'},'yes_ask':{'close_dollars':'0.62'},'price':{'close_dollars':'0.60'},'volume_fp':'2.50'}
        self.assertEqual(normalize_bar(old),normalize_bar(new));self.assertEqual(normalize_bar(old)['bid'],.58)
    def test_future_bar_and_volume_cannot_leak(self):
        g={'event':'a','start_ts':7200};bar={'end_ts':3600,'bid':.58,'ask':.62,'trade':.6,'volume':5}
        future={**bar,'end_ts':3601,'bid':.99,'ask':1,'volume':999}
        s=snapshot(g,[future,bar],'1h')
        self.assertEqual(s['p'],.6);self.assertEqual(s['contracts_last_hour'],5)
    def test_invalid_latest_quote_not_silently_replaced(self):
        g={'event':'a','start_ts':7200};good={'end_ts':3540,'bid':.58,'ask':.62,'trade':None,'volume':0}
        bad={**good,'end_ts':3600,'bid':.7,'ask':.6}
        self.assertEqual(snapshot(g,[good,bad],'1h')['reason'],'invalid_quote')
    def test_missing_and_stale(self):
        g={'event':'a','start_ts':7200};bar={'end_ts':3479,'bid':.4,'ask':.42,'trade':None,'volume':0}
        self.assertEqual(snapshot(g,[],'1h')['reason'],'no_prior_bar')
        self.assertEqual(snapshot(g,[bar],'1h')['reason'],'bar_too_old')
    def test_no_trade_carry_forward(self):
        b=normalize_bar({'event':'x','end_period_ts':3600,'yes_bid':{'close':'0.5'},'yes_ask':{'close':'0.52'},'price':{'previous':'0.8'},'volume':'0'})
        s=snapshot({'event':'x','start_ts':7200},[b],'1h');self.assertIsNone(s['trade_p'])
    def test_scores_known_values(self):
        self.assertEqual(scores([0,1],[.5,.5])['brier'],.25)
        self.assertAlmostEqual(scores([0,1],[.5,.5])['log_loss'],np.log(2))
        self.assertEqual(scores([0,1],[0,1])['brier'],0)
        with self.assertRaises(ValueError):scores([0],[1.1])
    def test_resolution_purge(self):
        train=pd.DataFrame({'settled_ts':[99,100,101]});future=pd.DataFrame({'target_ts':[100,110]})
        self.assertEqual(len(purge_resolutions(train,future)),1)
    def test_date_blocks_and_bootstrap(self):
        frame=pd.DataFrame({'day':[f'2026-01-{i:02}' for i in range(1,21)]})
        a,b=date_splits(frame);self.assertLess(a,b)
        ci=day_bootstrap(frame,np.zeros(20));self.assertEqual(ci,[0,0])
        self.assertEqual(day_bootstrap(frame,np.arange(20)),day_bootstrap(frame,np.arange(20)))
    def test_isotonic_sample_gate(self):
        f=pd.DataFrame({'p':[.4,.6]*30,'result':[0,1]*30})
        with self.assertRaisesRegex(ValueError,'1000'):fit_predict('isotonic',f,f)
    def test_winner_outcome_rules(self):
        from kalshi_lab.markets import get_adapter
        adapter=get_adapter('winner')
        valid=[{'result':'yes','settlement_value_dollars':'1.0000'},{'result':'no','settlement_value_dollars':'0.0000'}]
        self.assertIsNone(adapter.exclusion_reason(valid))
        self.assertEqual(adapter.exclusion_reason(valid[:1]),'not_exactly_two_markets')
        self.assertEqual(adapter.exclusion_reason([valid[0],valid[0]]),'non_binary_or_inconsistent_settlement')
        self.assertEqual(adapter.exclusion_reason([dict(valid[0],settlement_value_dollars='.5'),valid[1]]),'non_standard_settlement')
        with self.assertRaises(ValueError):get_adapter('totals')
    def test_wilson_endpoints(self):
        lo,hi=wilson(0,10);self.assertAlmostEqual(lo,0);self.assertGreater(hi,0)
        lo,hi=wilson(10,10);self.assertLess(lo,1);self.assertAlmostEqual(hi,1)

if __name__=='__main__':unittest.main()
