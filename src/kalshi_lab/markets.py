"""Market-type extension boundary. New market types must define their outcome rules."""
from typing import Protocol

class OutcomeAdapter(Protocol):
    kind: str
    def exclusion_reason(self, markets: list[dict]) -> str | None: ...

class WinnerAdapter:
    kind='winner'
    def exclusion_reason(self, markets):
        if len(markets)!=2:return 'not_exactly_two_markets'
        if sorted(m.get('result','') for m in markets)!=['no','yes']:
            return 'non_binary_or_inconsistent_settlement'
        for m in markets:
            v=m.get('settlement_value_dollars')
            if v is None or float(v)!=int(m['result']=='yes'):
                return 'non_standard_settlement'
        return None

ADAPTERS={'winner':WinnerAdapter()}
def get_adapter(kind):
    if kind not in ADAPTERS:raise ValueError(f'Unsupported market type: {kind}. Add and test an outcome adapter first.')
    return ADAPTERS[kind]
