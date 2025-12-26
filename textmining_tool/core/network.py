from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Iterable, List, Tuple

import networkx as nx
import pandas as pd
from community import community_louvain
from pyvis.network import Network


def build_cooccurrence_network(token_sets: Iterable[List[str]], min_edge_weight: int = 2) -> Tuple[pd.DataFrame, pd.DataFrame]:
    counter: Counter[Tuple[str, str]] = Counter()
    for tokens in token_sets:
        unique_tokens = sorted(set(tokens))
        for a, b in combinations(unique_tokens, 2):
            counter[(a, b)] += 1
    edges = [(a, b, w) for (a, b), w in counter.items() if w >= min_edge_weight]
    if not edges:
        return pd.DataFrame(), pd.DataFrame()
    G = nx.Graph()
    G.add_weighted_edges_from(edges)
    for node in G.nodes:
        G.nodes[node]["community"] = community_louvain.best_partition(G).get(node, 0)
    nodes_df = pd.DataFrame(
        {
            "id": list(G.nodes()),
            "degree": [G.degree(n) for n in G.nodes()],
            "community": [G.nodes[n].get("community", 0) for n in G.nodes()],
        }
    )
    edges_df = pd.DataFrame({"source": [e[0] for e in edges], "target": [e[1] for e in edges], "weight": [e[2] for e in edges]})
    return nodes_df, edges_df


def render_pyvis_html(nodes_df: pd.DataFrame, edges_df: pd.DataFrame, output_path: str | Path) -> Path:
    net = Network(height="640px", width="100%", notebook=False, cdn_resources="remote")
    for _, row in nodes_df.iterrows():
        net.add_node(row["id"], title=row["id"], group=row.get("community", 0))
    for _, row in edges_df.iterrows():
        net.add_edge(row["source"], row["target"], value=row.get("weight", 1))
    output_path = Path(output_path)
    net.show(str(output_path))
    return output_path
