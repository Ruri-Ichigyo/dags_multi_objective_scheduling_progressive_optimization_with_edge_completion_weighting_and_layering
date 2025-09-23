# %% [markdown]
# # Problem 2 结果可视化分析
# 
# 基于Problem2的缓存分配结果，进行深入的可视化分析和性能评估。

# %% [markdown]
# ## 导入依赖和配置

# %%
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import ipywidgets as widgets
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json
from collections import defaultdict
import Q1.code.Q_1 as q1
from Q1.code.Q_1_view import parse_schedule_txt

# 目录配置
ROOT = Path.cwd()
JSON_DIR = ROOT / "Json版本"
PROBLEM1_DIR = ROOT / "Attachment" / "Problem1"
PROBLEM2_DIR = ROOT / "Attachment" / "Problem2"

# 确保目录存在
assert PROBLEM2_DIR.exists(), f"Problem2结果目录不存在: {PROBLEM2_DIR}"

# 缓存容量配置（用于可视化）
CACHE_CAPACITIES = {
    "L1": 4096,
    "UB": 1024, 
    "L0A": 256,
    "L0B": 256,
    "L0C": 512
}

# 颜色配置
CACHE_COLORS = {
    "L1": "#FF6B6B",
    "UB": "#4ECDC4", 
    "L0A": "#45B7D1",
    "L0B": "#96CEB4",
    "L0C": "#FFEAA7"
}

print("✅ 依赖库导入完成")
print(f"📁 Problem2结果目录: {PROBLEM2_DIR}")

# %% [markdown]
# ## 数据加载和解析函数

# %%
def load_problem2_results(task_name: str) -> Dict[str, Any]:
    """加载单个任务的Problem2结果"""
    result = {
        "task_name": task_name,
        "schedule": [],
        "memory_allocations": {},
        "spill_operations": [],
        "summary": {}
    }
    
    try:
        # 1. 加载调度序列
        schedule_file = PROBLEM2_DIR / f"{task_name}_schedule.txt"
        if schedule_file.exists():
            with open(schedule_file, "r") as f:
                result["schedule"] = [int(line.strip()) for line in f if line.strip().isdigit()]
        
        # 2. 加载内存分配
        memory_file = PROBLEM2_DIR / f"{task_name}_memory.txt"
        if memory_file.exists():
            with open(memory_file, "r") as f:
                for line in f:
                    if ":" in line:
                        buf_id, offset = line.strip().split(":")
                        result["memory_allocations"][int(buf_id)] = int(offset)
        
        # 3. 加载SPILL操作
        spill_file = PROBLEM2_DIR / f"{task_name}_spill.txt"
        if spill_file.exists():
            with open(spill_file, "r") as f:
                for line in f:
                    if ":" in line:
                        buf_id, new_offset = line.strip().split(":")
                        result["spill_operations"].append({
                            "buf_id": int(buf_id),
                            "new_offset": int(new_offset)
                        })
        
        # 4. 加载汇总统计（如果存在）
        summary_file = PROBLEM2_DIR / f"{task_name}_summary.txt"
        if summary_file.exists():
            with open(summary_file, "r") as f:
                content = f.read()
                # 简单解析关键指标
                for line in content.split('\n'):
                    if "调度序列长度:" in line:
                        result["summary"]["schedule_length"] = int(line.split(":")[1].strip())
                    elif "缓冲区分配数:" in line:
                        result["summary"]["buffer_count"] = int(line.split(":")[1].strip())
                    elif "SPILL操作数:" in line:
                        result["summary"]["spill_count"] = int(line.split(":")[1].strip())
                    elif "总额外数据搬运量:" in line:
                        result["summary"]["total_spill_cost"] = int(line.split(":")[1].strip())
        
        print(f"✅ 加载 {task_name}: 调度{len(result['schedule'])}节点, "
              f"分配{len(result['memory_allocations'])}缓冲区, "
              f"SPILL{len(result['spill_operations'])}次")
        
    except Exception as e:
        print(f"⚠️ 加载 {task_name} 时出错: {e}")
    
    return result

def get_all_tasks() -> List[str]:
    """获取所有可用的任务名称"""
    tasks = []
    for schedule_file in PROBLEM2_DIR.glob("*_schedule.txt"):
        task_name = schedule_file.stem.replace("_schedule", "")
        tasks.append(task_name)
    return sorted(tasks)

def load_original_graph_data(task_name: str) -> Tuple[Any, Dict[int, Dict[str, Any]]]:
    """加载原始图数据"""
    try:
        json_file = JSON_DIR / f"{task_name}.json"
        if json_file.exists():
            return q1.load_graph(json_file)
        else:
            print(f"⚠️ 未找到JSON文件: {json_file}")
            return None, {}
    except Exception as e:
        print(f"⚠️ 加载图数据失败: {e}")
        return None, {}

# 测试数据加载
tasks = get_all_tasks()
print(f"📊 发现 {len(tasks)} 个任务: {tasks}")

# %% [markdown]
# ## 缓存利用率可视化

# %%
def visualize_cache_utilization(task_name: str) -> go.Figure:
    """可视化缓存利用率随时间的变化"""
    
    # 加载数据
    G, nodes_map = load_original_graph_data(task_name)
    if not nodes_map:
        return go.Figure().add_annotation(text="无法加载图数据", x=0.5, y=0.5)
    
    result = load_problem2_results(task_name)
    if not result["schedule"]:
        return go.Figure().add_annotation(text="无调度数据", x=0.5, y=0.5)
    
    # 模拟缓存使用情况
    cache_usage = {cache: [] for cache in CACHE_CAPACITIES.keys()}
    time_steps = []
    
    current_usage = {cache: 0 for cache in CACHE_CAPACITIES.keys()}
    
    for step, node_id in enumerate(result["schedule"]):
        if node_id not in nodes_map:
            continue
            
        node = nodes_map[node_id]
        op = node.get("Op", "") or node.get("op", "")
        cache_type = node.get("Type", "") or node.get("type", "")
        size = node.get("Size", 0) or node.get("size", 0)
        
        if cache_type in CACHE_CAPACITIES:
            if op == "ALLOC":
                current_usage[cache_type] += size
            elif op == "FREE":
                current_usage[cache_type] = max(0, current_usage[cache_type] - size)
        
        # 记录当前状态
        time_steps.append(step)
        for cache in CACHE_CAPACITIES.keys():
            utilization = current_usage[cache] / CACHE_CAPACITIES[cache] * 100
            cache_usage[cache].append(utilization)
    
    # 创建图表
    fig = go.Figure()
    
    for cache_type in CACHE_CAPACITIES.keys():
        if cache_usage[cache_type]:  # 只显示有数据的缓存
            fig.add_trace(go.Scatter(
                x=time_steps,
                y=cache_usage[cache_type],
                mode='lines',
                name=f'{cache_type} ({CACHE_CAPACITIES[cache_type]})',
                line=dict(color=CACHE_COLORS[cache_type], width=2),
                hovertemplate=f'<b>{cache_type}</b><br>' +
                             'Step: %{x}<br>' +
                             'Utilization: %{y:.1f}%<br>' +
                             '<extra></extra>'
            ))
    
    fig.update_layout(
        title=f'缓存利用率变化 - {task_name}',
        xaxis_title='调度步骤',
        yaxis_title='利用率 (%)',
        yaxis=dict(range=[0, 105]),
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_cache_summary_chart(tasks: List[str]) -> go.Figure:
    """创建所有任务的缓存使用汇总图表"""
    
    summary_data = []
    
    for task in tasks:
        result = load_problem2_results(task)
        if result["summary"]:
            summary_data.append({
                "Task": task,
                "BufferCount": result["summary"].get("buffer_count", 0),
                "SpillCount": result["summary"].get("spill_count", 0),
                "SpillCost": result["summary"].get("total_spill_cost", 0),
                "ScheduleLength": result["summary"].get("schedule_length", 0)
            })
    
    if not summary_data:
        return go.Figure().add_annotation(text="无汇总数据", x=0.5, y=0.5)
    
    df = pd.DataFrame(summary_data)
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('缓冲区分配数', 'SPILL操作次数', '总数据搬运量', '调度序列长度'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 缓冲区分配数
    fig.add_trace(
        go.Bar(x=df["Task"], y=df["BufferCount"], name="缓冲区数", 
               marker_color="#3498db"),
        row=1, col=1
    )
    
    # SPILL操作次数
    fig.add_trace(
        go.Bar(x=df["Task"], y=df["SpillCount"], name="SPILL次数",
               marker_color="#e74c3c"),
        row=1, col=2
    )
    
    # 总数据搬运量
    fig.add_trace(
        go.Bar(x=df["Task"], y=df["SpillCost"], name="搬运量",
               marker_color="#f39c12"),
        row=2, col=1
    )
    
    # 调度序列长度
    fig.add_trace(
        go.Bar(x=df["Task"], y=df["ScheduleLength"], name="序列长度",
               marker_color="#9b59b6"),
        row=2, col=2
    )
    
    fig.update_layout(
        title_text="Problem2 结果汇总对比",
        showlegend=False,
        height=600
    )
    
    # 旋转x轴标签
    fig.update_xaxes(tickangle=45)
    
    return fig

# %% [markdown]
# ## 内存分配可视化

# %%
def create_memory_allocation_chart(task_name: str) -> go.Figure:
    """创建内存分配的甘特图"""
    
    # 加载数据
    G, nodes_map = load_original_graph_data(task_name)
    result = load_problem2_results(task_name)
    
    if not nodes_map or not result["schedule"]:
        return go.Figure().add_annotation(text="数据不完整", x=0.5, y=0.5)
    
    # 分析每个缓冲区的生命周期
    buffer_lifecycle = {}  # buf_id -> {"alloc_step": int, "free_step": int, "cache_type": str, "size": int, "offset": int}
    
    for step, node_id in enumerate(result["schedule"]):
        if node_id not in nodes_map:
            continue
            
        node = nodes_map[node_id]
        op = node.get("Op", "") or node.get("op", "")
        buf_id = node.get("BufId", 0) or node.get("buf_id", 0)
        cache_type = node.get("Type", "") or node.get("type", "")
        size = node.get("Size", 0) or node.get("size", 0)
        
        if op == "ALLOC" and cache_type in CACHE_CAPACITIES:
            buffer_lifecycle[buf_id] = {
                "alloc_step": step,
                "free_step": None,
                "cache_type": cache_type,
                "size": size,
                "offset": result["memory_allocations"].get(buf_id, 0)
            }
        elif op == "FREE" and buf_id in buffer_lifecycle:
            buffer_lifecycle[buf_id]["free_step"] = step
    
    # 创建甘特图数据
    gantt_data = []
    
    for buf_id, info in buffer_lifecycle.items():
        if info["free_step"] is not None:
            gantt_data.append({
                "Buffer": f"Buf_{buf_id}",
                "Start": info["alloc_step"],
                "Finish": info["free_step"],
                "Cache": info["cache_type"],
                "Size": info["size"],
                "Offset": info["offset"],
                "Duration": info["free_step"] - info["alloc_step"]
            })
    
    if not gantt_data:
        return go.Figure().add_annotation(text="无缓冲区生命周期数据", x=0.5, y=0.5)
    
    df_gantt = pd.DataFrame(gantt_data)
    
    # 按缓存类型分组
    fig = go.Figure()
    
    y_pos = 0
    cache_y_positions = {}
    
    for cache_type in CACHE_CAPACITIES.keys():
        cache_buffers = df_gantt[df_gantt["Cache"] == cache_type]
        if len(cache_buffers) > 0:
            cache_y_positions[cache_type] = y_pos
            
            for _, row in cache_buffers.iterrows():
                fig.add_trace(go.Scatter(
                    x=[row["Start"], row["Finish"], row["Finish"], row["Start"], row["Start"]],
                    y=[y_pos, y_pos, y_pos+0.8, y_pos+0.8, y_pos],
                    fill="toself",
                    fillcolor=CACHE_COLORS[cache_type],
                    line=dict(color=CACHE_COLORS[cache_type]),
                    name=f'{cache_type}',
                    text=f'Buf_{row["Buffer"].split("_")[1]}<br>Size: {row["Size"]}<br>Offset: {row["Offset"]}',
                    hovertemplate='<b>%{text}</b><br>' +
                                 'Start: %{x[0]}<br>' +
                                 'End: %{x[1]}<br>' +
                                 'Duration: ' + str(row["Duration"]) + '<br>' +
                                 '<extra></extra>',
                    showlegend=False if cache_type in [t.name for t in fig.data] else True
                ))
                y_pos += 1
            
            y_pos += 0.5  # 缓存类型之间的间隔
    
    fig.update_layout(
        title=f'缓冲区内存分配时间线 - {task_name}',
        xaxis_title='调度步骤',
        yaxis_title='缓冲区',
        yaxis=dict(showticklabels=False),
        hovermode='closest',
        height=max(400, len(gantt_data) * 20 + 100)
    )
    
    return fig

def create_spill_analysis_chart(task_name: str) -> go.Figure:
    """创建SPILL操作分析图表"""
    
    result = load_problem2_results(task_name)
    
    if not result["spill_operations"]:
        return go.Figure().add_annotation(text="无SPILL操作", x=0.5, y=0.5)
    
    # 分析SPILL模式
    spill_pattern = defaultdict(int)
    spill_offsets = []
    
    for i, spill in enumerate(result["spill_operations"]):
        spill_pattern[spill["buf_id"]] += 1
        spill_offsets.append(spill["new_offset"])
    
    # 创建双子图
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('SPILL频次分布', 'SPILL偏移地址分布'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # SPILL频次
    buf_ids = list(spill_pattern.keys())
    frequencies = list(spill_pattern.values())
    
    fig.add_trace(
        go.Bar(
            x=[f"Buf_{bid}" for bid in buf_ids],
            y=frequencies,
            name="SPILL频次",
            marker_color="#e74c3c"
        ),
        row=1, col=1
    )
    
    # SPILL偏移地址分布
    fig.add_trace(
        go.Histogram(
            x=spill_offsets,
            nbinsx=20,
            name="偏移地址",
            marker_color="#3498db"
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title_text=f"SPILL操作分析 - {task_name}",
        showlegend=False,
        height=400
    )
    
    fig.update_xaxes(title_text="缓冲区ID", row=1, col=1)
    fig.update_xaxes(title_text="新偏移地址", row=1, col=2)
    fig.update_yaxes(title_text="SPILL次数", row=1, col=1)
    fig.update_yaxes(title_text="频次", row=1, col=2)
    
    return fig

# %% [markdown]
# ## 性能对比分析

# %%
def create_performance_comparison() -> go.Figure:
    """创建性能对比分析图表"""
    
    tasks = get_all_tasks()
    if not tasks:
        return go.Figure().add_annotation(text="无任务数据", x=0.5, y=0.5)
    
    # 收集性能数据
    perf_data = []
    
    for task in tasks:
        result = load_problem2_results(task)
        G, nodes_map = load_original_graph_data(task)
        
        if result["summary"] and nodes_map:
            # 计算性能指标
            total_nodes = len(nodes_map)
            schedule_length = result["summary"].get("schedule_length", 0)
            spill_cost = result["summary"].get("total_spill_cost", 0)
            spill_count = result["summary"].get("spill_count", 0)
            buffer_count = result["summary"].get("buffer_count", 0)
            
            # 计算效率指标
            spill_efficiency = spill_cost / max(spill_count, 1)  # 平均每次SPILL的代价
            memory_efficiency = buffer_count / max(schedule_length, 1) * 100  # 内存分配密度
            
            perf_data.append({
                "Task": task,
                "TotalNodes": total_nodes,
                "ScheduleLength": schedule_length,
                "SpillCost": spill_cost,
                "SpillCount": spill_count,
                "BufferCount": buffer_count,
                "SpillEfficiency": spill_efficiency,
                "MemoryEfficiency": memory_efficiency,
                "Category": task.split('_')[0]  # 提取任务类别
            })
    
    if not perf_data:
        return go.Figure().add_annotation(text="无性能数据", x=0.5, y=0.5)
    
    df = pd.DataFrame(perf_data)
    
    # 创建散点图矩阵
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('SPILL代价 vs SPILL次数', '内存效率 vs 调度长度', 
                       'SPILL效率对比', '综合性能雷达图'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"type": "polar"}]]
    )
    
    # 1. SPILL代价 vs SPILL次数
    for category in df["Category"].unique():
        cat_data = df[df["Category"] == category]
        fig.add_trace(
            go.Scatter(
                x=cat_data["SpillCount"],
                y=cat_data["SpillCost"],
                mode='markers+text',
                text=cat_data["Task"],
                textposition="top center",
                name=category,
                marker=dict(size=10)
            ),
            row=1, col=1
        )
    
    # 2. 内存效率 vs 调度长度
    fig.add_trace(
        go.Scatter(
            x=df["ScheduleLength"],
            y=df["MemoryEfficiency"],
            mode='markers+text',
            text=df["Task"],
            textposition="top center",
            name="内存效率",
            marker=dict(color=df["SpillCost"], colorscale="Viridis", size=10)
        ),
        row=1, col=2
    )
    
    # 3. SPILL效率对比
    fig.add_trace(
        go.Bar(
            x=df["Task"],
            y=df["SpillEfficiency"],
            name="SPILL效率",
            marker_color=df["SpillEfficiency"],
            marker_colorscale="RdYlBu_r"
        ),
        row=2, col=1
    )
    
    # 4. 雷达图（综合性能）
    if len(df) > 0:
        # 标准化指标（0-100）
        metrics = ["SpillCost", "SpillCount", "MemoryEfficiency", "SpillEfficiency"]
        
        for i, (_, row) in enumerate(df.iterrows()):
            if i < 3:  # 只显示前3个任务避免图表过于拥挤
                normalized_values = []
                for metric in metrics:
                    if metric in ["MemoryEfficiency", "SpillEfficiency"]:
                        # 这些是效率指标，值越大越好
                        val = min(100, row[metric])
                    else:
                        # 这些是代价指标，需要反转
                        max_val = df[metric].max()
                        val = (1 - row[metric] / max_val) * 100 if max_val > 0 else 100
                    normalized_values.append(val)
                
                fig.add_trace(
                    go.Scatterpolar(
                        r=normalized_values + [normalized_values[0]],  # 闭合图形
                        theta=metrics + [metrics[0]],
                        fill='toself',
                        name=row["Task"],
                        opacity=0.6
                    ),
                    row=2, col=2
                )
    
    fig.update_layout(
        title_text="Problem2 性能综合分析",
        height=800,
        showlegend=True
    )
    
    # 更新坐标轴标签
    fig.update_xaxes(title_text="SPILL次数", row=1, col=1)
    fig.update_yaxes(title_text="SPILL总代价", row=1, col=1)
    fig.update_xaxes(title_text="调度序列长度", row=1, col=2)
    fig.update_yaxes(title_text="内存效率 (%)", row=1, col=2)
    fig.update_xaxes(title_text="任务", tickangle=45, row=2, col=1)
    fig.update_yaxes(title_text="平均SPILL代价", row=2, col=1)
    
    return fig

# %% [markdown]
# ## 交互式可视化界面

# %%
# 创建交互式控件
task_dropdown = widgets.Dropdown(
    options=get_all_tasks(),
    description='选择任务:',
    style={'description_width': 'initial'}
)

chart_type_dropdown = widgets.Dropdown(
    options=[
        ('缓存利用率', 'utilization'),
        ('内存分配时间线', 'allocation'),
        ('SPILL操作分析', 'spill'),
        ('性能对比分析', 'performance'),
        ('结果汇总', 'summary')
    ],
    value='utilization',
    description='图表类型:',
    style={'description_width': 'initial'}
)

refresh_button = widgets.Button(
    description='刷新数据',
    button_style='info',
    icon='refresh'
)

output_area = widgets.Output()

def on_refresh_click(b):
    """刷新数据"""
    with output_area:
        output_area.clear_output()
        print("🔄 刷新任务列表...")
        
        # 更新任务列表
        new_tasks = get_all_tasks()
        task_dropdown.options = new_tasks
        
        print(f"✅ 发现 {len(new_tasks)} 个任务")
        display_chart()

def display_chart():
    """显示选定的图表"""
    with output_area:
        output_area.clear_output(wait=True)
        
        try:
            chart_type = chart_type_dropdown.value
            task_name = task_dropdown.value
            
            if chart_type == 'utilization':
                fig = visualize_cache_utilization(task_name)
                fig.show()
                
            elif chart_type == 'allocation':
                fig = create_memory_allocation_chart(task_name)
                fig.show()
                
            elif chart_type == 'spill':
                fig = create_spill_analysis_chart(task_name)
                fig.show()
                
            elif chart_type == 'performance':
                fig = create_performance_comparison()
                fig.show()
                
            elif chart_type == 'summary':
                fig = create_cache_summary_chart(get_all_tasks())
                fig.show()
                
        except Exception as e:
            print(f"❌ 生成图表时出错: {e}")
            import traceback
            traceback.print_exc()

# 绑定事件处理器
refresh_button.on_click(on_refresh_click)

def on_selection_change(change):
    """当选择改变时更新图表"""
    display_chart()

task_dropdown.observe(on_selection_change, names='value')
chart_type_dropdown.observe(on_selection_change, names='value')

# 显示控件
control_panel = widgets.HBox([
    task_dropdown,
    chart_type_dropdown,
    refresh_button
])

display(control_panel)
display(output_area)

# 初始显示
display_chart()

# %% [markdown]
# ## 使用说明
# 
# ### 功能特性：
# 
# 1. **缓存利用率可视化**：
#    - 实时显示各种缓存（L1, UB, L0A, L0B, L0C）的利用率变化
#    - 帮助识别缓存瓶颈和优化机会
# 
# 2. **内存分配时间线**：
#    - 甘特图显示每个缓冲区的生命周期
#    - 直观展示内存分配模式和重叠情况
# 
# 3. **SPILL操作分析**：
#    - 分析SPILL操作的频次和模式
#    - 识别频繁被换出的缓冲区
# 
# 4. **性能综合对比**：
#    - 多维度性能指标对比
#    - 雷达图展示综合性能表现
# 
# 5. **结果汇总统计**：
#    - 所有任务的关键指标对比
#    - 便于识别最优和最差案例
# 
# ### 使用方法：
# 
# 1. **选择任务**：从下拉菜单选择要分析的具体任务
# 2. **选择图表类型**：根据分析需求选择不同的可视化类型
# 3. **刷新数据**：点击刷新按钮重新加载最新的结果文件
# 4. **交互分析**：利用Plotly的交互功能进行深入分析
# 
# ### 分析要点：
# 
# - **缓存利用率**：关注峰值利用率和波动模式
# - **SPILL代价**：识别高代价操作的原因
# - **内存碎片**：观察分配模式中的碎片情况
# - **算法效果**：对比不同任务的优化效果
# 
# 此工具为Problem2的结果分析提供了全面的可视化支持，有助于理解缓存分配算法的性能表现和优化空间。


