#!/usr/bin/env python3
"""
JSON数据描述性统计分析
"""
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict, Counter

ROOT = Path.cwd()
JSON_DIR = ROOT / "Json版本"

def load_json_data(json_path: Path) -> Dict[str, Any]:
    """加载JSON文件数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_graph_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    """分析图结构特征"""
    nodes = data.get("Nodes", [])
    edges = data.get("Edges", [])

    # 基本统计
    num_nodes = len(nodes)
    num_edges = len(edges)

    # 节点度数分析
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)

    for edge in edges:
        if isinstance(edge, (list, tuple)) and len(edge) == 2:
            src, dst = edge
            out_degree[int(src)] += 1
            in_degree[int(dst)] += 1
        elif isinstance(edge, dict) and "Src" in edge and "Dst" in edge:
            src, dst = edge["Src"], edge["Dst"]
            out_degree[int(src)] += 1
            in_degree[int(dst)] += 1

    # 计算度数统计
    all_node_ids = {int(n.get("Id")) for n in nodes if n.get("Id") is not None}
    in_degrees = [in_degree.get(nid, 0) for nid in all_node_ids]
    out_degrees = [out_degree.get(nid, 0) for nid in all_node_ids]
    total_degrees = [in_degree.get(nid, 0) + out_degree.get(nid, 0) for nid in all_node_ids]

    return {
        'num_nodes': num_nodes,
        'num_edges': num_edges,
        'density': num_edges / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0,
        'avg_degree': np.mean(total_degrees) if total_degrees else 0,
        'max_in_degree': max(in_degrees) if in_degrees else 0,
        'max_out_degree': max(out_degrees) if out_degrees else 0,
        'in_degree_dist': in_degrees,
        'out_degree_dist': out_degrees,
        'total_degree_dist': total_degrees
    }

def analyze_node_operations(data: Dict[str, Any]) -> Dict[str, Any]:
    """分析节点操作类型分布"""
    nodes = data.get("Nodes", [])

    # 操作类型统计
    op_counts = Counter()
    pipe_counts = Counter()
    type_counts = Counter()

    # 内存相关统计
    memory_stats = {
        'L1': {'alloc_count': 0, 'free_count': 0, 'total_size': 0, 'sizes': []},
        'UB': {'alloc_count': 0, 'free_count': 0, 'total_size': 0, 'sizes': []},
        'L0A': {'alloc_count': 0, 'free_count': 0, 'total_size': 0, 'sizes': []},
        'L0B': {'alloc_count': 0, 'free_count': 0, 'total_size': 0, 'sizes': []},
        'L0C': {'alloc_count': 0, 'free_count': 0, 'total_size': 0, 'sizes': []}
    }

    cycles_list = []

    for node in nodes:
        op = node.get("Op", "Unknown")
        pipe = node.get("Pipe", "None")
        node_type = node.get("Type", "None")
        size = node.get("Size", 0)
        cycles = node.get("Cycles", 0)

        op_counts[op] += 1
        if pipe != "None":
            pipe_counts[pipe] += 1
        if node_type != "None":
            type_counts[node_type] += 1

        # 内存统计
        if node_type in memory_stats:
            if op == "ALLOC":
                memory_stats[node_type]['alloc_count'] += 1
                if size > 0:
                    memory_stats[node_type]['total_size'] += size
                    memory_stats[node_type]['sizes'].append(size)
            elif op == "FREE":
                memory_stats[node_type]['free_count'] += 1

        if cycles > 0:
            cycles_list.append(cycles)

    return {
        'op_counts': dict(op_counts),
        'pipe_counts': dict(pipe_counts),
        'type_counts': dict(type_counts),
        'memory_stats': memory_stats,
        'cycles_stats': {
            'count': len(cycles_list),
            'total': sum(cycles_list),
            'mean': np.mean(cycles_list) if cycles_list else 0,
            'std': np.std(cycles_list) if cycles_list else 0,
            'min': min(cycles_list) if cycles_list else 0,
            'max': max(cycles_list) if cycles_list else 0,
            'distribution': cycles_list
        }
    }

def create_comprehensive_analysis():
    """创建综合分析报告"""
    json_files = sorted([f for f in JSON_DIR.glob("*.json")])

    if not json_files:
        print(f"未在 {JSON_DIR} 找到JSON文件")
        return

    all_stats = {}
    summary_data = []

    print("=" * 80)
    print("JSON数据描述性统计分析")
    print("=" * 80)

    for json_file in json_files:
        print(f"\n分析文件: {json_file.name}")

        try:
            data = load_json_data(json_file)
            graph_stats = analyze_graph_structure(data)
            node_stats = analyze_node_operations(data)

            case_name = json_file.stem
            all_stats[case_name] = {
                'graph': graph_stats,
                'nodes': node_stats
            }

            # 汇总信息
            summary_data.append({
                '案例名称': case_name,
                '节点数': graph_stats['num_nodes'],
                '边数': graph_stats['num_edges'],
                '图密度': f"{graph_stats['density']:.6f}",
                '平均度数': f"{graph_stats['avg_degree']:.2f}",
                '最大入度': graph_stats['max_in_degree'],
                '最大出度': graph_stats['max_out_degree'],
                '操作类型数': len(node_stats['op_counts']),
                '管道类型数': len(node_stats['pipe_counts']),
                '缓存类型数': len(node_stats['type_counts']),
                '总周期数': node_stats['cycles_stats']['total'],
                '平均周期': f"{node_stats['cycles_stats']['mean']:.2f}"
            })

            # 详细输出
            print(f"  节点数: {graph_stats['num_nodes']:,}")
            print(f"  边数: {graph_stats['num_edges']:,}")
            print(f"  图密度: {graph_stats['density']:.6f}")
            print(f"  平均度数: {graph_stats['avg_degree']:.2f}")
            print(f"  最大入度: {graph_stats['max_in_degree']}")
            print(f"  最大出度: {graph_stats['max_out_degree']}")

            print(f"  操作类型分布:")
            for op, count in sorted(node_stats['op_counts'].items(), key=lambda x: x[1], reverse=True):
                print(f"    {op}: {count:,}")

            print(f"  内存类型分布:")
            for mem_type, count in sorted(node_stats['type_counts'].items(), key=lambda x: x[1], reverse=True):
                if count > 0:
                    print(f"    {mem_type}: {count:,}")

            if node_stats['cycles_stats']['count'] > 0:
                print(f"  周期统计:")
                print(f"    总周期: {node_stats['cycles_stats']['total']:,}")
                print(f"    平均周期: {node_stats['cycles_stats']['mean']:.2f}")
                print(f"    周期范围: {node_stats['cycles_stats']['min']} - {node_stats['cycles_stats']['max']}")

        except Exception as e:
            print(f"  错误: {e}")

    # 创建汇总表格
    print(f"\n{'='*80}")
    print("汇总统计表")
    print(f"{'='*80}")

    df_summary = pd.DataFrame(summary_data)
    print(df_summary.to_string(index=False))

    # 保存汇总结果
    df_summary.to_csv(ROOT / "json_descriptive_statistics.csv", index=False, encoding='utf-8-sig')
    print(f"\n汇总统计已保存至: json_descriptive_statistics.csv")

    return all_stats, df_summary

def create_visualizations(all_stats: Dict[str, Any], df_summary: pd.DataFrame):
    """创建可视化图表"""

    cases = list(all_stats.keys())
    
    # 图1: 图规模对比 - 综合面板
    fig1 = make_subplots(
        rows=2, cols=2,
        subplot_titles=['Graph Size Comparison', 'Graph Density Comparison', 
                       'Degree Distribution', 'Cycles Statistics'],
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": True}]]
    )
    
    # 节点数和边数对比
    nodes = [all_stats[case]['graph']['num_nodes'] for case in cases]
    edges = [all_stats[case]['graph']['num_edges'] for case in cases]
    
    fig1.add_trace(
        go.Bar(name='Nodes', x=cases, y=nodes, marker_color='lightblue', opacity=0.8),
        row=1, col=1
    )
    fig1.add_trace(
        go.Bar(name='Edges', x=cases, y=edges, marker_color='lightcoral', opacity=0.8),
        row=1, col=1
    )
    
    # 图密度对比
    densities = [all_stats[case]['graph']['density'] for case in cases]
    fig1.add_trace(
        go.Bar(name='Density', x=cases, y=densities, marker_color='orange', opacity=0.8,
               text=[f'{d:.2e}' for d in densities], textposition='outside'),
        row=1, col=2
    )
    
    # 度数分布箱线图
    for i, case in enumerate(cases):
        degree_data = all_stats[case]['graph']['total_degree_dist']
        fig1.add_trace(
            go.Box(y=degree_data, name=case, showlegend=False),
            row=2, col=1
        )
    
    # 周期统计对比
    cycle_totals = [all_stats[case]['nodes']['cycles_stats']['total'] for case in cases]
    cycle_means = [all_stats[case]['nodes']['cycles_stats']['mean'] for case in cases]
    
    fig1.add_trace(
        go.Bar(name='Total Cycles', x=cases, y=cycle_totals, marker_color='skyblue', opacity=0.8),
        row=2, col=2
    )
    fig1.add_trace(
        go.Scatter(name='Mean Cycles', x=cases, y=cycle_means, mode='markers+lines',
                  marker=dict(color='red', size=8), line=dict(color='red')),
        row=2, col=2, secondary_y=True
    )
    
    # 更新布局
    fig1.update_layout(
        title_text="JSON Data Descriptive Statistics Overview",
        title_x=0.5,
        height=800,
        showlegend=True
    )
    
    # 更新子图轴标签
    fig1.update_xaxes(title_text="Cases", row=1, col=1)
    fig1.update_yaxes(title_text="Count", row=1, col=1)
    fig1.update_xaxes(title_text="Cases", row=1, col=2)
    fig1.update_yaxes(title_text="Density", row=1, col=2)
    fig1.update_xaxes(title_text="Cases", row=2, col=1)
    fig1.update_yaxes(title_text="Degree", row=2, col=1)
    fig1.update_xaxes(title_text="Cases", row=2, col=2)
    fig1.update_yaxes(title_text="Total Cycles", row=2, col=2)
    fig1.update_yaxes(title_text="Mean Cycles", row=2, col=2, secondary_y=True)
    
    fig1.write_html(ROOT / 'json_descriptive_statistics_overview.html')
    
    # 图2: 操作类型分布 - 饼图网格
    fig2 = make_subplots(
        rows=2, cols=3,
        specs=[[{"type": "domain"}, {"type": "domain"}, {"type": "domain"}],
               [{"type": "domain"}, {"type": "domain"}, {"type": "domain"}]],
        subplot_titles=[case for case in cases]
    )
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FCEA2B', '#FF9FF3', '#54A0FF']
    
    for i, case in enumerate(cases):
        row = i // 3 + 1
        col = i % 3 + 1
        
        op_counts = all_stats[case]['nodes']['op_counts']
        
        if op_counts:
            ops = list(op_counts.keys())
            counts = list(op_counts.values())
            
            fig2.add_trace(
                go.Pie(labels=ops, values=counts, name=case,
                      marker_colors=colors[:len(ops)],
                      textinfo='label+percent',
                      textfont_size=10),
                row=row, col=col
            )
        else:
            # 空数据的情况
            fig2.add_trace(
                go.Pie(labels=['No Data'], values=[1], name=case,
                      marker_colors=['lightgray'],
                      textinfo='text',
                      text=['No Operation Data']),
                row=row, col=col
            )
    
    fig2.update_layout(
        title_text="Operation Type Distribution by Case",
        title_x=0.5,
        height=800,
        showlegend=False
    )
    
    fig2.write_html(ROOT / 'json_operation_distribution.html')
    
    # 图3: 内存类型分布热力图
    memory_types = ['L1', 'UB', 'L0A', 'L0B', 'L0C']
    memory_matrix = []
    
    for case in cases:
        case_memory = []
        for mem_type in memory_types:
            alloc_count = all_stats[case]['nodes']['memory_stats'][mem_type]['alloc_count']
            free_count = all_stats[case]['nodes']['memory_stats'][mem_type]['free_count']
            case_memory.append(alloc_count + free_count)
        memory_matrix.append(case_memory)
    
    fig3 = go.Figure(data=go.Heatmap(
        z=memory_matrix,
        x=memory_types,
        y=cases,
        colorscale='Viridis',
        text=memory_matrix,
        texttemplate="%{text}",
        textfont={"size": 10},
        colorbar=dict(title="Operation Count")
    ))
    
    fig3.update_layout(
        title='Memory Type Operations Heatmap',
        title_x=0.5,
        xaxis_title='Memory Types',
        yaxis_title='Cases',
        height=600
    )
    
    fig3.write_html(ROOT / 'json_memory_heatmap.html')
    
    # 图4: 交互式数据表
    fig4 = go.Figure(data=[go.Table(
        header=dict(values=list(df_summary.columns),
                   fill_color='paleturquoise',
                   align='left',
                   font_size=12),
        cells=dict(values=[df_summary[col] for col in df_summary.columns],
                  fill_color='lavender',
                  align='left',
                  font_size=11))
    ])
    
    fig4.update_layout(
        title='Summary Statistics Table',
        title_x=0.5,
        height=600
    )
    
    fig4.write_html(ROOT / 'json_summary_table.html')
    
    print("交互式可视化图表已生成:")
    print("- json_descriptive_statistics_overview.html")
    print("- json_operation_distribution.html")
    print("- json_memory_heatmap.html")
    print("- json_summary_table.html")
    
    # 显示图表（如果在Jupyter环境中）
    try:
        fig1.show()
        fig2.show()
        fig3.show()
        fig4.show()
    except:
        print("注意: 图表已保存为HTML文件，请在浏览器中打开查看")

if __name__ == "__main__":
    # 执行分析
    all_stats, df_summary = create_comprehensive_analysis()

    if all_stats:
        # 创建可视化
        create_visualizations(all_stats, df_summary)

        # 额外统计分析
        print(f"\n{'='*80}")
        print("额外统计分析")
        print(f"{'='*80}")

        # 计算总体统计
        total_nodes = sum(stats['graph']['num_nodes'] for stats in all_stats.values())
        total_edges = sum(stats['graph']['num_edges'] for stats in all_stats.values())
        avg_density = np.mean([stats['graph']['density'] for stats in all_stats.values()])

        print(f"全部案例汇总:")
        print(f"  总节点数: {total_nodes:,}")
        print(f"  总边数: {total_edges:,}")
        print(f"  平均图密度: {avg_density:.6f}")

        # 规模分类
        small_cases = [name for name, stats in all_stats.items() if stats['graph']['num_nodes'] < 5000]
        medium_cases = [name for name, stats in all_stats.items() if 5000 <= stats['graph']['num_nodes'] < 20000]
        large_cases = [name for name, stats in all_stats.items() if stats['graph']['num_nodes'] >= 20000]

        print(f"\n按规模分类:")
        print(f"  小规模案例 (<5K节点): {small_cases}")
        print(f"  中等规模案例 (5K-20K节点): {medium_cases}")
        print(f"  大规模案例 (≥20K节点): {large_cases}")