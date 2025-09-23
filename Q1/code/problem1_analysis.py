#!/usr/bin/env python3
"""
Problem 1 结果分析与优化效果评估
"""
import json
import pandas as pd
import networkx as nx
from pathlib import Path
from typing import Dict, Any, List, Tuple
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

ROOT = Path.cwd()
JSON_DIR = ROOT / "Json版本"
SCHED_DIR = ROOT / "Attachment" / "Problem1"

# 缓冲区类型定义
L0_TYPES = {"L0A", "L0B", "L0C"}
SOFT_TYPES = {"L1", "UB"}


def load_graph(json_path: Path) -> Tuple[nx.DiGraph, Dict[int, Dict[str, Any]]]:
    """从JSON文件加载图结构数据"""
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
    """解析调度文件，提取节点执行顺序"""
    order: List[int] = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                order.append(int(line))
            except ValueError:
                pass
    return order


def compute_mem_delta(node_attr: dict) -> int:
    """计算节点对L1/UB的内存增量"""
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


def compute_layer_deltas(node_attr: Dict[str, Any]) -> Tuple[int, int]:
    """返回 (delta_L1, delta_UB)"""
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


def analyze_memory_usage(order: List[int], nodes_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """分析内存使用情况"""
    cur_l1 = cur_ub = 0
    peak_l1 = peak_ub = 0
    l1_history = []
    ub_history = []

    # L0缓冲区约束检查
    l0_violations = 0
    l0_live = {"L0A": 0, "L0B": 0, "L0C": 0}

    for step, nid in enumerate(order):
        attr = nodes_map.get(nid, {})

        # 计算L1/UB内存变化
        d_l1, d_ub = compute_layer_deltas(attr)
        cur_l1 += d_l1
        cur_ub += d_ub
        peak_l1 = max(peak_l1, cur_l1)
        peak_ub = max(peak_ub, cur_ub)

        l1_history.append(cur_l1)
        ub_history.append(cur_ub)

        # 检查L0约束
        op = attr.get("Op")
        buf_type = attr.get("Type")
        if op == "ALLOC" and buf_type in L0_TYPES:
            if l0_live[buf_type] > 0:
                l0_violations += 1
            l0_live[buf_type] += 1
        elif op == "FREE" and buf_type in L0_TYPES:
            l0_live[buf_type] = max(0, l0_live[buf_type] - 1)

    return {
        'peak_l1': peak_l1,
        'peak_ub': peak_ub,
        'peak_total': peak_l1 + peak_ub,
        'l1_history': l1_history,
        'ub_history': ub_history,
        'l0_violations': l0_violations,
        'final_l1': cur_l1,
        'final_ub': cur_ub
    }


def baseline_topological_order(G: nx.DiGraph) -> List[int]:
    """基准拓扑排序"""
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError("图中存在环，非DAG。")
    return list(nx.topological_sort(G))


def analyze_case(case_name: str) -> Dict[str, Any]:
    """分析单个测试案例"""
    json_file = JSON_DIR / f"{case_name}.json"
    sched_file = SCHED_DIR / f"{case_name}_schedule.txt"

    if not json_file.exists() or not sched_file.exists():
        return None

    # 加载数据
    G, nodes_map = load_graph(json_file)
    optimized_order = parse_schedule_txt(sched_file)
    baseline_order = baseline_topological_order(G)

    # 分析优化前后的内存使用
    baseline_stats = analyze_memory_usage(baseline_order, nodes_map)
    optimized_stats = analyze_memory_usage(optimized_order, nodes_map)

    # 计算改进幅度
    l1_improvement = baseline_stats['peak_l1'] - optimized_stats['peak_l1']
    ub_improvement = baseline_stats['peak_ub'] - optimized_stats['peak_ub']
    total_improvement = baseline_stats['peak_total'] - optimized_stats['peak_total']

    l1_improvement_pct = (l1_improvement / baseline_stats['peak_l1'] * 100) if baseline_stats['peak_l1'] > 0 else 0
    ub_improvement_pct = (ub_improvement / baseline_stats['peak_ub'] * 100) if baseline_stats['peak_ub'] > 0 else 0
    total_improvement_pct = (total_improvement / baseline_stats['peak_total'] * 100) if baseline_stats['peak_total'] > 0 else 0

    return {
        'case_name': case_name,
        'nodes': G.number_of_nodes(),
        'edges': G.number_of_edges(),
        'baseline': baseline_stats,
        'optimized': optimized_stats,
        'improvements': {
            'l1_abs': l1_improvement,
            'ub_abs': ub_improvement,
            'total_abs': total_improvement,
            'l1_pct': l1_improvement_pct,
            'ub_pct': ub_improvement_pct,
            'total_pct': total_improvement_pct
        }
    }


def generate_summary_report():
    """生成汇总分析报告"""
    cases = ['Conv_Case0', 'Conv_Case1', 'FlashAttention_Case0', 'FlashAttention_Case1', 'Matmul_Case0', 'Matmul_Case1']

    results = []
    valid_cases = []

    print("=" * 80)
    print("Problem 1 结果分析与优化效果评估")
    print("=" * 80)

    for case in cases:
        analysis = analyze_case(case)
        if analysis:
            results.append(analysis)
            valid_cases.append(case)

            print(f"\n案例: {case}")
            print(f"  图规模: {analysis['nodes']} 节点, {analysis['edges']} 边")
            print(f"  基准峰值内存 - L1: {analysis['baseline']['peak_l1']:,}, UB: {analysis['baseline']['peak_ub']:,}, 总计: {analysis['baseline']['peak_total']:,}")
            print(f"  优化峰值内存 - L1: {analysis['optimized']['peak_l1']:,}, UB: {analysis['optimized']['peak_ub']:,}, 总计: {analysis['optimized']['peak_total']:,}")
            print(f"  内存减少量 - L1: {analysis['improvements']['l1_abs']:,} ({analysis['improvements']['l1_pct']:.1f}%)")
            print(f"  内存减少量 - UB: {analysis['improvements']['ub_abs']:,} ({analysis['improvements']['ub_pct']:.1f}%)")
            print(f"  总内存减少: {analysis['improvements']['total_abs']:,} ({analysis['improvements']['total_pct']:.1f}%)")
            print(f"  L0约束违规: {analysis['optimized']['l0_violations']} 次")

    if results:
        # 生成汇总表格
        print("\n" + "=" * 80)
        print("汇总表格")
        print("=" * 80)

        df_data = []
        for r in results:
            df_data.append({
                '案例': r['case_name'],
                '节点数': r['nodes'],
                '边数': r['edges'],
                '基准L1峰值': r['baseline']['peak_l1'],
                '优化L1峰值': r['optimized']['peak_l1'],
                'L1减少量': r['improvements']['l1_abs'],
                'L1减少%': f"{r['improvements']['l1_pct']:.1f}%",
                '基准UB峰值': r['baseline']['peak_ub'],
                '优化UB峰值': r['optimized']['peak_ub'],
                'UB减少量': r['improvements']['ub_abs'],
                'UB减少%': f"{r['improvements']['ub_pct']:.1f}%",
                '总内存减少%': f"{r['improvements']['total_pct']:.1f}%",
                'L0违规次数': r['optimized']['l0_violations']
            })

        df = pd.DataFrame(df_data)
        print(df.to_string(index=False))

        # 计算总体统计
        total_l1_baseline = sum(r['baseline']['peak_l1'] for r in results)
        total_l1_optimized = sum(r['optimized']['peak_l1'] for r in results)
        total_ub_baseline = sum(r['baseline']['peak_ub'] for r in results)
        total_ub_optimized = sum(r['optimized']['peak_ub'] for r in results)

        avg_l1_improvement = sum(r['improvements']['l1_pct'] for r in results) / len(results)
        avg_ub_improvement = sum(r['improvements']['ub_pct'] for r in results) / len(results)
        avg_total_improvement = sum(r['improvements']['total_pct'] for r in results) / len(results)

        print(f"\n总体优化效果:")
        print(f"  平均L1内存减少: {avg_l1_improvement:.1f}%")
        print(f"  平均UB内存减少: {avg_ub_improvement:.1f}%")
        print(f"  平均总内存减少: {avg_total_improvement:.1f}%")

        # 保存结果到CSV
        output_file = ROOT / "problem1_analysis_results.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n详细结果已保存至: {output_file}")

        return results
    else:
        print("未找到有效的分析案例")
        return []


if __name__ == "__main__":
    results = generate_summary_report()