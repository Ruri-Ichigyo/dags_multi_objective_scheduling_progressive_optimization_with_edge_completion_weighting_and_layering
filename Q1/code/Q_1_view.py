# %%
# 依赖与最小工具函数（基于 schedule.txt 的 L1/UB 序列分析）
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple

import pandas as pd
import networkx as nx

try:
    import plotly.graph_objects as go
except Exception:
    raise RuntimeError("请先安装 plotly: pip install plotly")

ROOT = Path.cwd()
JSON_DIR = ROOT / 'Json版本'
SCHED_DIR = ROOT / 'Attachment' / 'Problem1'
SCHED_DIR.mkdir(parents=True, exist_ok=True)


def load_graph(json_path: Path) -> Tuple[nx.DiGraph, Dict[int, Dict[str, Any]]]:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nodes = data.get('Nodes', [])
    edges = data.get('Edges', [])
    G = nx.DiGraph()
    nodes_map: Dict[int, Dict[str, Any]] = {}
    for n in nodes:
        nid = n.get('Id')
        if nid is None:
            continue
        nodes_map[int(nid)] = n
        G.add_node(int(nid))
    for e in edges:
        if isinstance(e, (list, tuple)) and len(e) == 2:
            G.add_edge(int(e[0]), int(e[1]))
        elif isinstance(e, dict) and 'Src' in e and 'Dst' in e:
            G.add_edge(int(e['Src']), int(e['Dst']))
    return G, nodes_map


def parse_schedule_txt(path: Path) -> List[int]:
    order: List[int] = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                order.append(int(line))
            except ValueError:
                # 忽略非整数行
                pass
    return order


def guess_json_for_schedule(sched_file: Path) -> Path:
    stem = sched_file.stem  # e.g., Matmul_Case0_schedule / Matmul_Case0_GA_schedule
    base = stem
    if base.endswith('_schedule'):
        base = base[: -len('_schedule')]
    for tag in ('_GA', '_HEUR', '_BASE'):
        if base.endswith(tag):
            base = base[: -len(tag)]
            break
    candidate = JSON_DIR / f"{base}.json"
    return candidate


def compute_layer_deltas(node_attr: Dict[str, Any]) -> Tuple[int, int]:
    """返回 (delta_L1, delta_UB) 仅根据 ALLOC/FREE + Type(L1/UB)。"""
    op = node_attr.get('Op') or node_attr.get('op')
    t = node_attr.get('Type') or node_attr.get('type')
    size = int(node_attr.get('Size') or 0)
    d_l1 = d_ub = 0
    if op == 'ALLOC':
        if t == 'L1':
            d_l1 += size
        elif t == 'UB':
            d_ub += size
    elif op == 'FREE':
        if t == 'L1':
            d_l1 -= size
        elif t == 'UB':
            d_ub -= size
    return d_l1, d_ub


# %%
# 交互：从 schedule.txt 复现并可视化 L1/UB 变化
import ipywidgets as widgets
from IPython.display import display, clear_output

# 收集可用的 schedule 文本（去重）
sched_files = sorted({p for p in SCHED_DIR.glob('*_schedule.txt')}, key=lambda p: p.name)
if not sched_files:
    print(f'提示：未在 {SCHED_DIR} 找到 *_schedule.txt，可先在主 Notebook 生成。')

sched_dd = widgets.Dropdown(options=[(p.name, str(p)) for p in sched_files], description='schedule')
run_btn = widgets.Button(description='计算与绘制', button_style='primary')
out = widgets.Output()


def make_series(order: List[int], nodes_map: Dict[int, Dict[str, Any]]):
    t = list(range(len(order)))
    l1 = []
    ub = []
    cur_l1 = cur_ub = 0
    peak_l1 = peak_ub = 0
    for n in order:
        d_l1, d_ub = compute_layer_deltas(nodes_map.get(n, {}))
        cur_l1 += d_l1
        cur_ub += d_ub
        peak_l1 = max(peak_l1, cur_l1)
        peak_ub = max(peak_ub, cur_ub)
        l1.append(cur_l1)
        ub.append(cur_ub)
    return t, l1, ub, peak_l1, peak_ub


@run_btn.on_click
def _on_run(_):
    with out:
        clear_output()
        if not sched_dd.value:
            print('请选择一个 schedule 文件')
            return
        sched_path = Path(sched_dd.value)
        order = parse_schedule_txt(sched_path)
        json_path = guess_json_for_schedule(sched_path)
        if not json_path.exists():
            print('未找到对应 JSON：', json_path)
            return
        _, nodes_map = load_graph(json_path)
        t, l1, ub, peak_l1, peak_ub = make_series(order, nodes_map)
        print(f'JSON: {json_path.name} | 序列长度: {len(order)}')
        print(f'峰值 L1: {peak_l1} | 峰值 UB: {peak_ub}')

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=l1, mode='lines', name='L1'))
        fig.add_trace(go.Scatter(x=t, y=ub, mode='lines', name='UB'))
        fig.update_layout(title='L1 / UB 变化曲线', xaxis_title='调度步', yaxis_title='累计占用', height=500)
        fig.show()

ui = widgets.VBox([sched_dd, run_btn, out])
display(ui)


# %%


# %%



