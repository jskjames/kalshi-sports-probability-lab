"""Integration gates for a locally rebuilt research bundle."""
import unittest,json
from pathlib import Path
import pandas as pd
from kalshi_lab.analysis import scores
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless((ROOT/'outputs'/'report.json').exists(),'Run analysis to generate outputs')
class OutputIntegrity(unittest.TestCase):
    def test_snapshot_integrity_and_score_parity(self):
        df=pd.read_csv(ROOT/'outputs'/'snapshots.csv');r=json.loads((ROOT/'outputs'/'report.json').read_text())
        self.assertFalse(df.duplicated(['event','horizon']).any())
        self.assertTrue((df.bar_ts<=df.target_ts).all())
        self.assertTrue((df.target_ts<df.start_ts).all())
        self.assertTrue((df.age_seconds<=120).all())
        self.assertTrue((df.spread<=.100000001).all())
        self.assertEqual(len(df),r['snapshots'])
        for h,d in df.groupby('horizon'):
            self.assertAlmostEqual(scores(d.result,d.p)['brier'],r['horizons'][h]['available']['brier'])
        self.assertTrue((df.groupby('day').split.nunique()==1).all())
    def test_holdout_membership(self):
        p=pd.read_csv(ROOT/'outputs'/'holdout_predictions.csv');d=pd.read_csv(ROOT/'outputs'/'snapshots.csv')
        self.assertEqual(set(p.event),set(d.loc[(d.horizon=='1h')&(d.split=='test'),'event']))
        self.assertFalse(p.event.duplicated().any())
