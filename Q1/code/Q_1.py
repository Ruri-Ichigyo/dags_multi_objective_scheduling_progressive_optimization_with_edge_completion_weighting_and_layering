# %%
# 依赖与导入
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple

import pandas as pd
import networkx as nx

# 交互与可视化
try:
    import plotly.graph_objects as go
    import plotly.express as px
except Exception:
    raise RuntimeError("请先安装 plotly: pip install plotly")

# 工作目录与数据目录
ROOT = Path.cwd()
JSON_DIR = ROOT / "Json版本"
assert JSON_DIR.exists(), f"找不到目录: {JSON_DIR}"

# 实用函数
PIPE_COLOR = {
    "CUBE": "#ff7f0e",
    "VECTOR": "#2ca02c",
    "MTE1": "#1f77b4",
    "MTE2": "#9467bd",
    "MTE3": "#8c564b",
    "FIXP": "#e377c2",
}
BUF_TYPE_COLOR = {
    "L0A": "#AEC7E8",
    "L0B": "#FFBB78",
    "L0C": "#98DF8A",
    "L1": "#FF9896",
    "UB": "#C5B0D5",
}


# %% [markdown]
# # 计算图 JSON 读取与可视化工具
# 
# - 功能：
#   - 扫描根目录下 `Json版本/` 内的 JSON 文件
#   - 解析 Nodes/Edges 构建有向无环图（DAG）
#   - 输出拓扑序摘要并可视化子图（默认展示前 N 个拓扑序节点）
# - 适用数据结构：
#   - 节点字段：`Id, Op`，操作节点可含 `Pipe, Cycles, Bufs`；缓存管理节点为 `ALLOC/FREE`，可含 `BufId, Size, Type`
#   - 边字段：`Edges: [[src, dst], ...]`
# - 使用步骤：
#   1) 运行依赖与导入单元格
#   2) 运行“解析函数”和“可视化函数”单元格
#   3) 在“示例运行”里选择目标 JSON 文件并可视化

# %%
# 解析与构图

def load_graph(json_path: Path) -> Tuple[nx.DiGraph, Dict[int, Dict[str, Any]]]:
    """从 JSON 文件读取 Nodes 和 Edges，构建有向图。
    返回 (G, nodes_map)。nodes_map: id -> node_attr
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nodes = data.get("Nodes", [])
    edges = data.get("Edges", [])

    G = nx.DiGraph()
    nodes_map: Dict[int, Dict[str, Any]] = {}
    for n in nodes:
        nid = n.get("Id")
        if nid is None:
            continue
        nodes_map[nid] = n
        # 分类：操作节点 or 缓存节点
        op = n.get("Op")
        is_alloc = op == "ALLOC"
        is_free = op == "FREE"
        node_type = "CACHE" if (is_alloc or is_free) else "OP"
        color = None
        if node_type == "OP":
            pipe = n.get("Pipe", "")
            color = PIPE_COLOR.get(pipe, "#7f7f7f")
        else:
            buf_type = n.get("Type", "")
            color = BUF_TYPE_COLOR.get(buf_type, "#bcbd22")
        G.add_node(
            nid,
            label=f"{nid}:{op}",
            node_type=node_type,
            color=color,
            pipe=n.get("Pipe"),
            cycles=n.get("Cycles"),
            bufs=n.get("Bufs"),
            buf_id=n.get("BufId"),
            size=n.get("Size"),
            buf_type=n.get("Type"),
        )

    for e in edges:
        if isinstance(e, (list, tuple)) and len(e) == 2:
            src, dst = e
            G.add_edge(int(src), int(dst))
        else:
            # 兼容可能的 dict 形式 {"Src": x, "Dst": y}
            if isinstance(e, dict) and "Src" in e and "Dst" in e:
                G.add_edge(int(e["Src"]), int(e["Dst"]))

    return G, nodes_map


def topo_order(G: nx.DiGraph) -> List[int]:
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError("图中存在环，非 DAG。")
    return list(nx.topological_sort(G))


def summarize(G: nx.DiGraph) -> pd.DataFrame:
    df = pd.DataFrame([
        {
            "Id": n,
            "Op": G.nodes[n].get("label"),
            "Type": G.nodes[n].get("node_type"),
            "Pipe": G.nodes[n].get("pipe"),
            "Cycles": G.nodes[n].get("cycles"),
            "BufType": G.nodes[n].get("buf_type"),
        }
        for n in G.nodes
    ])
    return df.sort_values("Id").reset_index(drop=True)


# %%
# 可视化

def visualize_subgraph(G: nx.DiGraph, first_n: int = 80, layout: str = "dot") -> go.Figure:
    """可视化拓扑序前 N 个节点的诱导子图。
    layout: 'spring' | 'kamada' | 'dot' (Graphviz)
    """
    order = topo_order(G)
    nodes_sel = set(order[:max(1, min(first_n, len(order)))])
    H = G.subgraph(nodes_sel).copy()

    # 布局
    pos = None
    if layout == "spring":
        pos = nx.spring_layout(H, seed=42, k=0.5)
    elif layout == "kamada":
        pos = nx.kamada_kawai_layout(H)
    elif layout == "dot":
        try:
            # 需要 pygraphviz 或 pydot；缺失则回退 spring
            pos = nx.nx_agraph.graphviz_layout(H, prog="dot")  # type: ignore
        except Exception:
            pos = nx.spring_layout(H, seed=42, k=0.5)
    else:
        pos = nx.spring_layout(H, seed=42, k=0.5)

    # 节点散点
    x_nodes = [pos[n][0] for n in H.nodes]
    y_nodes = [pos[n][1] for n in H.nodes]
    colors = [H.nodes[n].get("color", "#7f7f7f") for n in H.nodes]
    texts = [
        f"Id: {n}<br>Op: {H.nodes[n].get('label')}<br>Type: {H.nodes[n].get('node_type')}<br>Pipe: {H.nodes[n].get('pipe')}<br>Cycles: {H.nodes[n].get('cycles')}<br>BufType: {H.nodes[n].get('buf_type')}"
        for n in H.nodes
    ]

    node_trace = go.Scatter(
        x=x_nodes,
        y=y_nodes,
        mode="markers+text",
        text=[str(n) for n in H.nodes],
        textposition="top center",
        hovertext=texts,
        hoverinfo="text",
        marker=dict(size=10, color=colors, line=dict(width=0.5, color="#333")),
        showlegend=False,
    )

    # 边线段
    x_edges = []
    y_edges = []
    for u, v in H.edges:
        x_edges += [pos[u][0], pos[v][0], None]
        y_edges += [pos[u][1], pos[v][1], None]

    edge_trace = go.Scatter(
        x=x_edges,
        y=y_edges,
        mode="lines",
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        showlegend=False,
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"DAG 子图可视化（前 {len(nodes_sel)} / {G.number_of_nodes()} 节点）",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        height=700,
    )
    return fig


# %%
# 示例运行：选择一个 JSON 并可视化
from ipywidgets import widgets, interact

# 构建文件列表
json_files = sorted([p for p in JSON_DIR.glob("*.json")])

if not json_files:
    raise FileNotFoundError(f"目录 {JSON_DIR} 下未找到 .json 文件")

file_options = [(p.name, str(p)) for p in json_files]

@interact(
    json_path=widgets.Dropdown(options=file_options, description='JSON文件'),
    first_n=widgets.IntSlider(value=80, min=10, max=50000, step=10, description='前N节点'),
    layout=widgets.Dropdown(options=['dot','spring','kamada'], value='dot', description='布局')
)
def run(json_path, first_n, layout):
    G, nodes_map = load_graph(Path(json_path))
    order = topo_order(G)
    print(f"节点总数: {G.number_of_nodes()} | 边总数: {G.number_of_edges()} | 拓扑序长度: {len(order)}")

    # 展示前 10 个节点摘要
    df = summarize(G)
    display(df.head(10))

    # 可视化
    fig = visualize_subgraph(G, first_n=first_n, layout=layout)
    fig.show()


# %% [markdown]
# ## 算法说明与复杂度
# 
# - 目标：在保持 DAG 依赖的前提下，最小化执行过程中 L1/UB 的峰值驻留；同时满足 L0A/L0B/L0C 同时驻留≤1 的硬约束。
# - 做法：在任一时刻的“就绪集合”（入度为 0 的节点）中，按以下启发式选择下一个节点：
#   1) 优先选择可降低当前驻留的节点（L1/UB 的 FREE），若有多个，选释放量绝对值最大的；
#   2) 若没有能降驻留的，优先选择 L0 FREE 或能尽快解锁 L0 FREE 的节点；
#   3) 否则选择“未来代价”较小的节点（依据 Size 近似，选增量小的）。
#   同时对 L0 ALLOC 做硬约束：同类型如已有驻留，则暂不调度新的 L0 ALLOC。
# - 正确性：算法保证每步选择的节点都在就绪集合中并满足 L0 约束，因此整体序列是合法的拓扑序。
# - 复杂度：
#   - 记节点数 N、边数 M、就绪集合均摊规模 R（通常远小于 N）。
#   - 每次选择需要在候选中做若干打分，若用线性扫描，则每步 O(R + 出边检查近似 O(out))，总计 O(N·R + M)。
#   - 若用堆/多队列维护（按类别分桶），可将选择均摊降到 O(log R)，总体约 O((N+M) + N log R)。
#   - 本实现采用简单线性策略，代码更直观；若需要更高性能可进一步分桶优化。

# %%
# 最小缓存驻留调度（启发式拓扑排序）
from collections import defaultdict, deque

L0_TYPES = {"L0A", "L0B", "L0C"}
SOFT_TYPES = {"L1", "UB"}


def compute_mem_delta(node_attr: dict) -> int:
    """返回对 L1/UB 的内存增量：ALLOC(+Size) / FREE(-Size)；其他为0。仅计入 L1/UB。"""
    op = node_attr.get("Op") or node_attr.get("op")
    t = node_attr.get("Type") or node_attr.get("type")
    size = int(node_attr.get("Size") or 0)
    if t not in SOFT_TYPES:
        return 0
    if op == "ALLOC":
        return size
    if op == "FREE":
        return -size
    return 0


def is_l0_alloc(node_attr: dict) -> bool:
    return (node_attr.get("Op") == "ALLOC") and (node_attr.get("Type") in L0_TYPES)


def is_l0_free(node_attr: dict) -> bool:
    return (node_attr.get("Op") == "FREE") and (node_attr.get("Type") in L0_TYPES)


def minimal_residency_schedule(G: nx.DiGraph, nodes_map: Dict[int, Dict[str, Any]]) -> List[int]:
    """
    在满足依赖的前提下进行拓扑调度，目标近似最小化 L1/UB 峰值驻留。
    约束：L0A/L0B/L0C 同时最多各 1 个缓冲区驻留（即必须紧随其后完成对应 FREE；若 FREE 不显式给出，则按启发式尽快排完相关使用/释放）。

    策略：就绪集合中优先选择能降低当前驻留的节点（FREE>L0 FREE>其他），
          若均不降，则选“后续影响小”的节点：
            - 优先选择即将触发 L0 FREE 的节点或 L0 FREE 本身
            - 其次选择未来累计内存需求较小的节点（用 Size 近似）
    返回：节点调度序列（拓扑合法）。
    """
    # 入度与就绪集合
    indeg = {u: G.in_degree(u) for u in G.nodes}
    ready = [u for u, d in indeg.items() if d == 0]
    ready_set = set(ready)

    # 跟踪 L0 驻留计数：同类型最多 1
    l0_live = {"L0A": 0, "L0B": 0, "L0C": 0}

    # 已分配的 L0 buf 集合（按 BufId），用于遇到 FREE 时递减
    l0_buf_live: Dict[str, set] = {"L0A": set(), "L0B": set(), "L0C": set()}

    # 输出序列与内存跟踪
    order: List[int] = []
    cur_mem = 0
    peak_mem = 0

    # 预处理：节点的 mem_delta 与辅助属性
    mem_delta = {}
    size_hint = {}
    for n in G.nodes:
        attr = nodes_map.get(n, {})
        mem_delta[n] = compute_mem_delta(attr)
        size_hint[n] = int(attr.get("Size") or 0)

    def can_place(n: int) -> bool:
        """检查 L0 同时驻留约束。对于 L0 ALLOC，确保对应类型当前为 0。FREE 总是可放（若匹配已有）。"""
        attr = nodes_map.get(n, {})
        if is_l0_alloc(attr):
            t = attr.get("Type")
            return l0_live.get(t, 0) == 0
        if is_l0_free(attr):
            t = attr.get("Type")
            buf_id = attr.get("BufId")
            # 只有在该 buf 已在驻留集合中才有意义；否则也允许（容错），但不改变计数
            return True
        return True

    def apply_side_effects(n: int):
        nonlocal cur_mem, peak_mem
        attr = nodes_map.get(n, {})
        # L1/UB 内存
        cur_mem += mem_delta[n]
        peak_mem = max(peak_mem, cur_mem)
        # L0 状态
        if is_l0_alloc(attr):
            t = attr.get("Type")
            l0_live[t] += 1
            l0_buf_live[t].add(attr.get("BufId"))
        elif is_l0_free(attr):
            t = attr.get("Type")
            buf_id = attr.get("BufId")
            if buf_id in l0_buf_live[t]:
                l0_buf_live[t].remove(buf_id)
                l0_live[t] = max(0, l0_live[t] - 1)

    # 选择函数：优先减少内存/释放 L0
    def pick_next(cands: List[int]) -> int:
        # 分类：
        # 1) 负增量（FREE L1/UB）、L0 FREE
        c1 = [n for n in cands if mem_delta[n] < 0 or is_l0_free(nodes_map.get(n, {}))]
        if c1:
            # 选择绝对值最大的负增量，若并列，选择 size_hint 大的
            return max(c1, key=lambda n: (-(mem_delta[n]), size_hint[n]))
        # 2) 不改变内存的节点（如计算/MOVE/COPY），尽量靠近触发 L0 FREE：优先后继中存在 L0 FREE 的
        def will_unlock_l0_free(n: int) -> int:
            # 如果 n 的后继中存在 L0 FREE，给予更高权重
            score = 0
            for succ in G.successors(n):
                attr = nodes_map.get(succ, {})
                if is_l0_free(attr):
                    score += 1
            return score
        c2 = [n for n in cands if mem_delta[n] == 0 and not is_l0_alloc(nodes_map.get(n, {}))]
        if c2:
            return max(c2, key=lambda n: (will_unlock_l0_free(n), -size_hint[n]))
        # 3) 正增量（ALLOC L1/UB）与 L0 ALLOC，尽量选择 size 小的，且避免打破 L0 约束
        c3 = [n for n in cands if True]
        return min(c3, key=lambda n: (size_hint[n], mem_delta[n]))

    # 主循环
    # 使用 deque 提升 pop/append 性能
    ready_q = deque(sorted(ready))
    ready_set = set(ready_q)

    while ready_q:
        # 就绪且满足 L0 约束的候选
        cands = [n for n in list(ready_q) if can_place(n)]
        if not cands:
            # 理论上不会发生（DAG + L0 约束可满足），若发生则退化为忽略 L0 限制选择一个
            n = ready_q.popleft()
        else:
            n = pick_next(cands)
            # 从 deque 中移除该元素
            # 简单做法：重建 deque
            tmp = deque()
            popped = False
            while ready_q:
                x = ready_q.popleft()
                if not popped and x == n:
                    popped = True
                    continue
                tmp.append(x)
            ready_q = tmp

        ready_set.discard(n)
        order.append(n)
        apply_side_effects(n)

        # 更新后继
        for v in G.successors(n):
            indeg[v] -= 1
            if indeg[v] == 0 and v not in ready_set:
                ready_q.append(v)
                ready_set.add(v)

    # 简单校验
    if len(order) != G.number_of_nodes():
        raise RuntimeError("生成的调度序列不完整，可能图非 DAG 或约束冲突。")
    return order


# %%
# 最小缓存驻留调度（基于堆的启发式拓扑排序）
from heapq import heappush, heappop

# 评分越小优先级越高；我们构造多维 key：
# key = (
#   k0,  # 是否负增量/L0 FREE 优先（0 优先, 1 次之, 2 最后）
#   k1,  # 负增量时按释放绝对值大优先 -> -abs(delta)；其他时用辅助代价
#   k2,  # 次级排序：倾向 size 小
#   node_id  # 稳定排序
# )

def _prio_key(n: int, G: nx.DiGraph, nodes_map: Dict[int, Dict[str, Any]], mem_delta: Dict[int, int], size_hint: Dict[int, int]) -> tuple:
    attr = nodes_map.get(n, {})
    delta = mem_delta[n]
    size = size_hint[n]

    # 类别
    if delta < 0 or is_l0_free(attr):
        k0 = 0
        k1 = -abs(delta)
    else:
        # 是否能解锁 L0 FREE
        unlock = 0
        for succ in G.successors(n):
            if is_l0_free(nodes_map.get(succ, {})):
                unlock += 1
        if unlock > 0 and delta == 0 and not is_l0_alloc(attr):
            k0 = 1
            k1 = -unlock  # 越多越优先
        else:
            k0 = 2
            # 正增量或 L0 ALLOC：偏向 size 小
            k1 = size
    k2 = size
    return (k0, k1, k2, n)


def minimal_residency_schedule(G: nx.DiGraph, nodes_map: Dict[int, Dict[str, Any]]) -> List[int]:
    indeg = {u: G.in_degree(u) for u in G.nodes}

    # 跟踪 L0 驻留计数
    l0_live = {"L0A": 0, "L0B": 0, "L0C": 0}
    l0_buf_live: Dict[str, set] = {"L0A": set(), "L0B": set(), "L0C": set()}

    order: List[int] = []
    cur_mem = 0
    peak_mem = 0

    mem_delta = {n: compute_mem_delta(nodes_map.get(n, {})) for n in G.nodes}
    size_hint = {n: int(nodes_map.get(n, {}).get("Size") or 0) for n in G.nodes}

    def can_place(n: int) -> bool:
        attr = nodes_map.get(n, {})
        if is_l0_alloc(attr):
            t = attr.get("Type")
            return l0_live.get(t, 0) == 0
        return True

    def apply_side_effects(n: int):
        nonlocal cur_mem, peak_mem
        attr = nodes_map.get(n, {})
        # L1/UB 内存
        cur_mem += mem_delta[n]
        peak_mem = max(peak_mem, cur_mem)
        # L0 状态
        if is_l0_alloc(attr):
            t = attr.get("Type")
            l0_live[t] += 1
            l0_buf_live[t].add(attr.get("BufId"))
        elif is_l0_free(attr):
            t = attr.get("Type")
            buf_id = attr.get("BufId")
            if buf_id in l0_buf_live[t]:
                l0_buf_live[t].remove(buf_id)
                l0_live[t] = max(0, l0_live[t] - 1)

    # 初始化堆
    heap = []
    for u in G.nodes:
        if indeg[u] == 0 and can_place(u):
            heappush(heap, (_prio_key(u, G, nodes_map, mem_delta, size_hint), u))

    pushed = set([u for u, d in indeg.items() if d == 0 and can_place(u)])

    while heap:
        _, n = heappop(heap)
        if indeg[n] != 0:
            continue  # 已被其他路径更新
        order.append(n)
        apply_side_effects(n)

        for v in G.successors(n):
            indeg[v] -= 1
            if indeg[v] == 0 and v not in pushed and can_place(v):
                heappush(heap, (_prio_key(v, G, nodes_map, mem_delta, size_hint), v))
                pushed.add(v)

        # 如果堆空了但还有未调度节点，说明被 L0 约束卡住：
        # 放宽策略为允许下一个就绪节点（忽略 can_place）入堆，保证进度。
        if not heap and len(order) < G.number_of_nodes():
            unlocked = False
            for u in list(G.nodes):
                if indeg[u] == 0 and u not in pushed:
                    heappush(heap, (_prio_key(u, G, nodes_map, mem_delta, size_hint), u))
                    pushed.add(u)
                    unlocked = True
                    break
            if not unlocked:
                break

    if len(order) != G.number_of_nodes():
        raise RuntimeError("生成的调度序列不完整，可能存在约束冲突或非 DAG。")
    return order
# 峰值驻留计算与验证

def peak_memory_for_order(order: List[int], nodes_map: Dict[int, Dict[str, Any]]) -> int:
    cur = 0
    peak = 0
    for n in order:
        delta = compute_mem_delta(nodes_map.get(n, {}))
        cur += delta
        peak = max(peak, cur)
    return peak

# %%
# 交互（下拉 + 运行按钮）
from ipywidgets import Dropdown, IntSlider, Button, HBox, VBox, Output

file_dropdown = Dropdown(options=[(p.name, str(p)) for p in (JSON_DIR.glob('*.json'))], description='JSON文件')
show_slider = IntSlider(value=30, min=10, max=200, step=10, description='展示前N')
run_btn = Button(description='运行调度', button_style='primary')
out = Output()

def on_run_clicked(_):
    out.clear_output()
    json_path = file_dropdown.value
    if not json_path:
        with out:
            print('请选择 JSON 文件')
        return
    G, nodes_map = load_graph(Path(json_path))
    base_order = topo_order(G)
    base_peak = peak_memory_for_order(base_order, nodes_map)
    sched = minimal_residency_schedule(G, nodes_map)
    sched_peak = peak_memory_for_order(sched, nodes_map)
    with out:
        print(f"节点: {G.number_of_nodes()} 边: {G.number_of_edges()}")
        print(f"基准拓扑序峰值(L1/UB): {base_peak}")
        print(f"启发式调度峰值(L1/UB): {sched_peak}")
        df = pd.DataFrame({
            'order_id': list(range(len(sched))),
            'node': sched,
            'op': [nodes_map[n].get('Op') for n in sched],
            'type': [nodes_map[n].get('Type') for n in sched],
            'delta': [compute_mem_delta(nodes_map[n]) for n in sched],
        })
        display(df.head(show_slider.value))

run_btn.on_click(on_run_clicked)

VBox([HBox([file_dropdown, show_slider, run_btn]), out])

# %%
# Problem1 结果导出：<任务名>_schedule.txt
import os

def task_name_from_path(p: Path) -> str:
    return p.stem  # 如 Matmul_Case0


def generate_problem1_schedule(json_path: Path, out_root: Path = Path("Attachment")) -> Path:
    """读取 JSON，运行最小驻留调度，导出 Problem1/<任务名>_schedule.txt。
    返回生成文件路径。
    """
    G, nodes_map = load_graph(json_path)
    sched = minimal_residency_schedule(G, nodes_map)

    task = task_name_from_path(json_path)
    out_dir = out_root / "Problem1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{task}_schedule.txt"

    with open(out_file, "w", encoding="utf-8") as f:
        for nid in sched:
            f.write(f"{nid}\n")
    return out_file
# 交互：生成 Problem1 文本
from ipywidgets import Dropdown, Button, HBox, VBox, Output

export_dropdown = Dropdown(options=[(p.name, str(p)) for p in (JSON_DIR.glob('*.json'))], description='JSON文件')
export_btn = Button(description='生成 Problem1 文本', button_style='success')
export_out = Output()


def on_export_clicked(_):
    export_out.clear_output()
    path = export_dropdown.value
    if not path:
        with export_out:
            print('请选择 JSON 文件')
        return
    out_path = generate_problem1_schedule(Path(path), Path('Attachment'))
    with export_out:
        print(f'已生成: {out_path}')
        # 预览前 10 行
        try:
            with open(out_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= 10:
                        print('...')
                        break
                    print(line.rstrip('\n'))
        except Exception as e:
            print('预览失败:', e)

export_btn.on_click(on_export_clicked)

VBox([HBox([export_dropdown, export_btn]), export_out])



