from __future__ import annotations

from collections import Counter
import math
from itertools import combinations
from pathlib import Path
from typing import Iterable, List, Tuple

import networkx as nx
import pandas as pd
from community import community_louvain
from pyvis.network import Network


def _score_pair(method: str, n11: int, n1_: int, n_1: int, N: int) -> float:
    # 간단한 점수 계산(의존성 최소화)
    n10 = n1_ - n11
    n01 = n_1 - n11
    n00 = max(N - n11 - n10 - n01, 0)
    if method.startswith("LLR"):
        # PMI를 사용한 근사치(희귀 쌍 안정화)
        return math.log((n11 / N + 1e-9) / ((n1_ / N) * (n_1 / N) + 1e-9))
    if method == "NPMI":
        pxy = n11 / N if N else 0
        px = n1_ / N if N else 0
        py = n_1 / N if N else 0
        if pxy == 0 or px == 0 or py == 0:
            return -1.0
        pmi = math.log(pxy / (px * py))
        return pmi / (-math.log(pxy))
    if method == "Jaccard":
        denom = (n1_ + n_1 - n11)
        return n11 / denom if denom else 0.0
    if method == "Cosine":
        return n11 / math.sqrt(n1_ * n_1) if n1_ and n_1 else 0.0
    if method == "Chi-square":
        denom = (n11 + n01) * (n11 + n10) * (n00 + n01) * (n00 + n10)
        return (N * (n11 * n00 - n10 * n01) ** 2) / (denom + 1e-9)
    return float(n11)


def build_cooccurrence_network(
    token_sets: Iterable[List[str]],
    min_edge_weight: int = 2,
    score_method: str = "LLR (기본)",
    min_n11: int = 2,
    top_edge_pct: float = 10.0,
    tightness: int = 5,
    hide_isolates: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    counter: Counter[Tuple[str, str]] = Counter()
    token_doc_freq: Counter[str] = Counter()
    for tokens in token_sets:
        unique_tokens = sorted(set(tokens))
        for t in unique_tokens:
            token_doc_freq[t] += 1
        for a, b in combinations(unique_tokens, 2):
            counter[(a, b)] += 1
    edges_scored = []
    N = len(token_sets)
    for (a, b), n11 in counter.items():
        if n11 < max(min_edge_weight, min_n11):
            continue
        n1_ = token_doc_freq[a]
        n_1 = token_doc_freq[b]
        score = _score_pair(score_method, n11, n1_, n_1, N)
        edges_scored.append((a, b, n11, score))
    if not edges_scored:
        return pd.DataFrame(), pd.DataFrame()
    # 점수 기반 정렬 후 상위 퍼센트 필터
    edges_scored.sort(key=lambda x: x[3], reverse=True)
    if 0 < top_edge_pct < 100:
        keep_n = max(1, int(len(edges_scored) * (top_edge_pct / 100)))
        edges_scored = edges_scored[:keep_n]
    edges = [(a, b, n11, score) for a, b, n11, score in edges_scored]
    G = nx.Graph()
    for a, b, n11, score in edges:
        G.add_edge(a, b, weight=n11, score=score)
    partition = community_louvain.best_partition(G) if G.number_of_nodes() else {}
    if hide_isolates:
        isolate_nodes = [n for n in G.nodes if G.degree(n) <= 1]
        G.remove_nodes_from(isolate_nodes)
    nodes_df = pd.DataFrame(
        {
            "id": list(G.nodes()),
            "degree": [G.degree(n) for n in G.nodes()],
            "community": [partition.get(n, 0) for n in G.nodes()],
        }
    )
    edges_df = pd.DataFrame(
        {
            "source": [e[0] for e in G.edges()],
            "target": [e[1] for e in G.edges()],
            "weight": [G.edges[e].get("weight", 1) for e in G.edges()],
            "score": [G.edges[e].get("score", 0.0) for e in G.edges()],
        }
    )
    return nodes_df, edges_df


def render_pyvis_html(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    output_path: str | Path,
    avoid_overlap: bool = False,
    hide_isolates: bool = False,
    tightness: int = 5,
) -> Path:
    net = Network(height="640px", width="100%", notebook=False, cdn_resources="remote")
    physics_kwargs = {"spring_length": max(50, 200 - tightness * 10), "spring_strength": 0.01 + tightness * 0.002}
    net.barnes_hut(**physics_kwargs)
    for _, row in nodes_df.iterrows():
        net.add_node(row["id"], title=row["id"], group=row.get("community", 0))
    for _, row in edges_df.iterrows():
        net.add_edge(row["source"], row["target"], value=row.get("weight", 1))
    if avoid_overlap:
        net.toggle_physics(True)
    if hide_isolates:
        net.filter_edges(lambda e: True)
    output_path = Path(output_path)
    net.show(str(output_path))
    return output_path
