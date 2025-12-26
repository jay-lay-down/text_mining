from __future__ import annotations

from typing import Iterable, List

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


def apriori_rules(token_sets: Iterable[List[str]], min_support: float, min_confidence: float, min_lift: float) -> pd.DataFrame:
    transactions = list(token_sets)
    if not transactions:
        return pd.DataFrame()
    all_items = sorted({item for tx in transactions for item in tx})
    one_hot = pd.DataFrame([[1 if item in tx else 0 for item in all_items] for tx in transactions], columns=all_items)
    freq = apriori(one_hot, min_support=min_support, use_colnames=True)
    rules = association_rules(freq, metric="confidence", min_threshold=min_confidence)
    rules = rules[rules["lift"] >= min_lift]
    return rules
