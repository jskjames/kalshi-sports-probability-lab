"""Plain-language reporting from measured results, without invented claims."""
from pathlib import Path

def write_findings(root, report):
    r=report;m=r['model'];root=Path(root)
    text=f'''# Research findings

## Study population

Collected {r['collection']['selected_events']:,} candidate NBA winner events; linked {r['games']:,} eligible events to recorded schedules and complementary settlements. The observed window is {r['start_date']} to {r['end_date']} (UTC scheduled game dates).

The frozen extract contains **{r['bars']:,} minute observations**, **{r['snapshots']:,} eligible snapshots**, and **{r['common_games']:,} games eligible at all four horizons**. These are dependent observations of games, not independent training examples.

## Market probability scores

Lower scores are better. Available-case samples can differ. The matched cohort is the same at every horizon.

| Horizon | Available games | Brier | Matched games | Matched Brier |
|---|---:|---:|---:|---:|
'''
    f=lambda x:'—' if x is None else f'{x:.4f}'
    for h,v in r['horizons'].items():
        a=v['available'];c=v['common_cohort']
        text+=f"| {h} | {a['n']} | {f(a['brier'])} | {c['n']} | {f(c['brier'])} |\n"
    text+='\nA forecast of 50% on every game has Brier 0.25. Beating this simple reference does not establish market efficiency or profitable trading. Horizon differences are descriptive; no causal interpretation is intended.\n'
    if m['status']=='evaluated':
        selected=m['selected_on_validation']
        text+=f'''\n## Frozen one-hour model comparison

Validation selected **{selected}** using the declared 0.002 Brier improvement rule. The eligible sample had {m['train_games']} training games, {m['validation_games']} validation games and {m['test_games']} test games across {m['test_dates']} UTC dates. Final refitting used {m['refit_games']} games after resolution-time purging.

| Model | Validation Brier | Test Brier | Test log loss | Test Δ Brier vs market | Paired 95% interval |
|---|---:|---:|---:|---:|---|
'''
        for name,v in m['test'].items():
            ci=v['delta_95ci']
            text+=f"| {name} | {f(m['validation'][name]['brier'])} | {f(v['brier'])} | {f(v['log_loss'])} | {f(v['delta_brier_vs_market'])} | {f(ci[0])} to {f(ci[1])} |\n"
        if 'logistic' in m['test']:
            v=m['test']['logistic'];lo,hi=v['delta_95ci']
            if hi is not None and hi<0:
                conclusion='The paired interval favors logistic recalibration on this holdout. This is evidence within the sampled period, not proof of future superiority.'
            elif lo is not None and lo>0:
                conclusion='The paired interval favors the original market on this holdout. Recalibration did not generalize successfully in this comparison.'
            else:
                conclusion='The paired interval does not establish a reliable improvement from logistic recalibration. Do not claim that the model beats the market.'
            text+='\n'+conclusion+'\n'
        text+='\nUnavailable candidates: '+('; '.join(f'{k}: {v}' for k,v in m['unavailable_models'].items()) or 'none')+'.\n'
    else:text+='\nThe validation/test sample is too small for the predeclared model-comparison gate.\n'
    text+='''
## What the project demonstrates

The contribution is an auditable probability study: joining market contracts to schedules, respecting forecast cutoffs, checking outcomes, separating descriptive from held-out evaluation, and making exclusions inspectable. A null or negative recalibration result is a valid finding.

## Remaining uncertainty

'''+''.join('- '+c+'\n' for c in r['caveats'])
    text+='''
## Next research decision

Before presenting results as a verified pre-tipoff study, cross-check scheduled starts against an independent historical schedule or actual-start source. For a stronger out-of-sample claim, freeze this specification and collect a new period prospectively. Adding team-strength predictors should be a separately evaluated extension.

## Resume wording after reviewing and understanding the work

'''
    text+=f'- Built a Python/SQL pipeline analyzing {r["bars"]:,} Kalshi minute observations across {r["games"]} NBA games, with timestamp-based quality checks and an interactive probability dashboard.\n'
    text+='- Evaluated winner-market calibration across four forecast horizons using Brier score, log loss, chronological holdouts, and paired date-block bootstrap intervals.\n'
    (root/'docs'/'findings.md').write_text(text)
