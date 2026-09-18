"""Execute the shipped SQL and reconcile score queries with the JSON report."""
import json,sqlite3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'outputs'/'report.json').read_text())
def statements(text):
    """Split SQL with SQLite's parser so semicolons in comments are harmless."""
    buffer=''
    for line in text.splitlines(True):
        buffer+=line
        if sqlite3.complete_statement(buffer):
            yield buffer
            buffer=''
    if buffer.strip():raise ValueError('Incomplete SQL statement')

with sqlite3.connect(root/'data'/'warehouse.sqlite') as db:
    queries=list(statements((root/'sql'/'research_queries.sql').read_text()))
    results=[db.execute(q).fetchall() for q in queries if q.strip()]
    for h,n,brier,spread in results[0]:
        assert n==r['horizons'][h]['available']['n']
        assert abs(brier-r['horizons'][h]['available']['brier'])<1e-12
    for h,n,brier in results[1]:
        assert n==r['common_games']
        assert abs(brier-r['horizons'][h]['common_cohort']['brier'])<1e-12
    assert results[-1]==[(0,)]
print('PASS: five SQL queries; metric parity, matched cohorts and no future observations.')
