# 函数接口文档

## 图加载与分析模块

### load_graph
```python
def load_graph(json_path: Path) -> Tuple[nx.DiGraph, Dict[int, Dict[str, Any]]]
```

从 JSON 文件读取节点和边信息，构建有向图。

**参数:**
- `json_path (Path)`: JSON 文件路径

**返回:**
- `Tuple[nx.DiGraph, Dict[int, Dict[str, Any]]]`: 
  - `G`: NetworkX 有向图对象
  - `nodes_map`: 节点ID到属性字典的映射

**功能:**
- 解析 JSON 文件中的 Nodes 和 Edges 字段
- 根据节点类型（操作节点/缓存节点）设置颜色和属性
- 构建包含完整节点属性的有向图

---

### topo_order
```python
def topo_order(G: nx.DiGraph) -> List[int]
```

计算有向无环图的拓扑排序。

**参数:**
- `G (nx.DiGraph)`: 输入的有向图

**返回:**
- `List[int]`: 拓扑排序的节点序列

**异常:**
- `ValueError`: 当图中存在环时抛出

---

### summarize
```python
def summarize(G: nx.DiGraph) -> pd.DataFrame
```

生成图节点的摘要表格。

**参数:**
- `G (nx.DiGraph)`: 输入的有向图

**返回:**
- `pd.DataFrame`: 包含节点ID、操作、类型、管道、周期等信息的数据框

## 可视化模块

### visualize_subgraph
```python
def visualize_subgraph(G: nx.DiGraph, first_n: int = 80, layout: str = "dot") -> go.Figure
```

可视化拓扑序前N个节点的诱导子图。

**参数:**
- `G (nx.DiGraph)`: 输入的有向图
- `first_n (int, 可选)`: 显示的节点数量，默认80
- `layout (str, 可选)`: 布局算法，可选 'spring'、'kamada'、'dot'，默认 'dot'

**返回:**
- `go.Figure`: Plotly 图形对象

**功能:**
- 支持多种布局算法
- 节点按类型着色，显示详细悬停信息
- 自动处理布局算法的回退机制

## 内存管理与调度模块

### compute_mem_delta
```python
def compute_mem_delta(node_attr: dict) -> int
```

计算节点对L1/UB内存的影响量。

**参数:**
- `node_attr (dict)`: 节点属性字典

**返回:**
- `int`: 内存变化量（ALLOC为正，FREE为负，其他为0）

---

### is_l0_alloc / is_l0_free
```python
def is_l0_alloc(node_attr: dict) -> bool
def is_l0_free(node_attr: dict) -> bool
```

判断节点是否为L0缓存的分配/释放操作。

**参数:**
- `node_attr (dict)`: 节点属性字典

**返回:**
- `bool`: 判断结果

---

### minimal_residency_schedule
```python
def minimal_residency_schedule(G: nx.DiGraph, nodes_map: Dict[int, Dict[str, Any]]) -> List[int]
```

基于启发式的最小内存驻留调度算法。

**参数:**
- `G (nx.DiGraph)`: 输入的有向图
- `nodes_map (Dict[int, Dict[str, Any]])`: 节点属性映射

**返回:**
- `List[int]`: 调度序列（节点ID列表）

**算法特点:**
- 优先选择能降低当前内存驻留的节点
- 满足L0缓存同时驻留≤1的硬约束
- 使用多级启发式策略进行节点选择

**复杂度:**
- 时间复杂度: O((N+M) + N log R)，其中N为节点数，M为边数，R为就绪集合平均大小
- 空间复杂度: O(N + M)

---

### peak_memory_for_order
```python
def peak_memory_for_order(order: List[int], nodes_map: Dict[int, Dict[str, Any]]) -> int
```

计算给定调度序列的峰值内存占用。

**参数:**
- `order (List[int])`: 节点调度序列
- `nodes_map (Dict[int, Dict[str, Any]])`: 节点属性映射

**返回:**
- `int`: 峰值内存占用量

## 缓存分配与SPILL模块

### CacheManager
```python
class CacheManager:
    def __init__(self, cache_type: str, capacity: int)
    def allocate(self, buf_id: int, size: int, step: int) -> Optional[int]
    def free(self, buf_id: int) -> bool
    def select_victim_lru_opt(self, required_size: int, current_step: int) -> Optional[int]
```

高级缓存管理器，支持精确地址分配和优化的SPILL策略。

**核心特性:**
- 基于地址偏移的精确内存分配
- 最佳适应（Best-Fit）分配策略
- 自动合并相邻空闲块减少碎片
- LRU+OPT混合SPILL策略

---

### advanced_cache_simulation
```python
def advanced_cache_simulation(
    order: List[int],
    nodes_map: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]
```

执行高级缓存分配模拟。

**参数:**
- `order (List[int])`: 调度序列
- `nodes_map (Dict[int, Dict[str, Any]])`: 节点属性映射

**返回:**
- `Dict[str, Any]`: 包含分配结果、SPILL操作和统计信息

**输出格式:**
```python
{
    "total_spill_cost": int,              # 总额外数据搬运量
    "spill_count": int,                   # SPILL操作次数
    "spill_operations": List[Dict],       # 详细SPILL操作列表
    "buffer_allocations": Dict,           # 缓冲区分配映射
    "cache_stats": Dict,                  # 各缓存统计信息
    "processing_time": float              # 处理时间
}
```

## 文件导出模块

### task_name_from_path
```python
def task_name_from_path(p: Path) -> str
```

从文件路径提取任务名称。

**参数:**
- `p (Path)`: 文件路径

**返回:**
- `str`: 任务名称（文件名去除扩展名）

---

### generate_problem1_schedule
```python
def generate_problem1_schedule(json_path: Path, out_root: Path = Path("Attachment")) -> Path
```

为Problem1生成调度结果文件。

**参数:**
- `json_path (Path)`: 输入JSON文件路径
- `out_root (Path, 可选)`: 输出根目录，默认为 "Attachment"

**返回:**
- `Path`: 生成的调度文件路径

**功能:**
- 运行最小驻留调度算法
- 将结果导出为 `<任务名>_schedule.txt` 格式
- 自动创建输出目录结构

---

### export_problem2_results
```python
def export_problem2_results(
    task_name: str,
    original_order: List[int],
    simulation_result: Dict[str, Any],
    out_dir: Path
)
```

按照标准格式导出Problem2结果文件。

**参数:**
- `task_name (str)`: 任务名称
- `original_order (List[int])`: 原始调度序列
- `simulation_result (Dict[str, Any])`: 缓存模拟结果
- `out_dir (Path)`: 输出目录

**生成文件:**
- `<任务名>_schedule.txt`: 调度顺序结果（节点ID列表）
- `<任务名>_memory.txt`: 缓存分配结果（BufId:Offset格式）
- `<任务名>_spill.txt`: SPILL操作列表（BufId:NewOffset格式）

**文件格式示例:**
```
# <任务名>_schedule.txt
0
2
4
1
...

# <任务名>_memory.txt  
0:0
1:5
2:30
3:10
...

# <任务名>_spill.txt
5:400
9:20
1:40
...
```

## 常量定义

```python
# 管道类型颜色映射
PIPE_COLOR = {
    "CUBE": "#ff7f0e",
    "VECTOR": "#2ca02c", 
    "MTE1": "#1f77b4",
    "MTE2": "#9467bd",
    "MTE3": "#8c564b",
    "FIXP": "#e377c2",
}

# 缓冲区类型颜色映射
BUF_TYPE_COLOR = {
    "L0A": "#AEC7E8",
    "L0B": "#FFBB78", 
    "L0C": "#98DF8A",
    "L1": "#FF9896",
    "UB": "#C5B0D5",
}

# 缓存类型分类
L0_TYPES = {"L0A", "L0B", "L0C"}  # L0缓存类型
SOFT_TYPES = {"L1", "UB"}         # 软约束内存类型

# 缓存容量配置
CACHE_CAPACITIES = {
    "L1": 4096,
    "UB": 1024, 
    "L0A": 256,
    "L0B": 256,
    "L0C": 512
}
```

## 使用示例

```python
# 基本用法
json_path = Path("Json版本/example.json")
G, nodes_map = load_graph(json_path)

# 生成调度序列
schedule = minimal_residency_schedule(G, nodes_map)

# 计算峰值内存
peak = peak_memory_for_order(schedule, nodes_map)

# 可视化
fig = visualize_subgraph(G, first_n=50, layout='dot')
fig.show()

# 导出Problem1结果
output_path = generate_problem1_schedule(json_path)

# Problem2缓存分配和导出
result = advanced_cache_simulation(schedule, nodes_map)
export_problem2_results("example", schedule, result, Path("Attachment/Problem2"))
```

# Q_1_ans_view.ipynb 接口文档

## 概述

这是一个用于分析和可视化调度序列中 L1/UB 内存变化的 Jupyter Notebook 工具。主要功能是从生成的 schedule.txt 文件中读取调度序列，计算内存占用变化，并提供交互式可视化。

## 核心函数接口

### load_graph
```python
def load_graph(json_path: Path) -> Tuple[nx.DiGraph, Dict[int, Dict[str, Any]]]
```

从 JSON 文件加载计算图结构。

**参数:**
- `json_path (Path)`: JSON 文件路径

**返回:**
- `Tuple[nx.DiGraph, Dict[int, Dict[str, Any]]]`:
  - `G`: NetworkX 有向图对象
  - `nodes_map`: 节点 ID 到属性字典的映射

**功能:**
- 解析 JSON 中的 Nodes 和 Edges 字段
- 构建 NetworkX 有向图
- 兼容不同的边表示格式（列表或字典）

---

### parse_schedule_txt
```python
def parse_schedule_txt(path: Path) -> List[int]
```

解析调度文件，提取节点执行序列。

**参数:**
- `path (Path)`: schedule.txt 文件路径

**返回:**
- `List[int]`: 节点 ID 的执行顺序列表

**功能:**
- 逐行读取文件，提取整数节点 ID
- 自动忽略空行和非整数行
- 容错处理，跳过格式错误的行

---

### guess_json_for_schedule
```python
def guess_json_for_schedule(sched_file: Path) -> Path
```

根据调度文件名推测对应的 JSON 文件路径。

**参数:**
- `sched_file (Path)`: 调度文件路径

**返回:**
- `Path`: 推测的 JSON 文件路径

**推测规则:**
```
Matmul_Case0_schedule.txt -> Matmul_Case0.json
Matmul_Case0_GA_schedule.txt -> Matmul_Case0.json
Matmul_Case0_HEUR_schedule.txt -> Matmul_Case0.json
```

**处理逻辑:**
1. 移除 `_schedule` 后缀
2. 移除算法标识后缀（`_GA`, `_HEUR`, `_BASE`）
3. 在 JSON_DIR 目录中查找对应 JSON 文件

---

### compute_layer_deltas
```python
def compute_layer_deltas(node_attr: Dict[str, Any]) -> Tuple[int, int]
```

计算单个节点对 L1 和 UB 内存的影响。

**参数:**
- `node_attr (Dict[str, Any])`: 节点属性字典

**返回:**
- `Tuple[int, int]`: (L1内存变化量, UB内存变化量)

**计算逻辑:**
- `ALLOC` + `L1`: L1 内存增加 Size
- `ALLOC` + `UB`: UB 内存增加 Size  
- `FREE` + `L1`: L1 内存减少 Size
- `FREE` + `UB`: UB 内存减少 Size
- 其他情况: 无内存变化 (0, 0)

---

### make_series
```python
def make_series(order: List[int], nodes_map: Dict[int, Dict[str, Any]]) -> Tuple[List[int], List[int], List[int], int, int]
```

根据调度序列计算内存占用时间序列。

**参数:**
- `order (List[int])`: 节点执行序列
- `nodes_map (Dict[int, Dict[str, Any]])`: 节点属性映射

**返回:**
- `Tuple[List[int], List[int], List[int], int, int]`:
  - `t`: 时间步列表 [0, 1, 2, ...]
  - `l1`: L1 内存占用序列
  - `ub`: UB 内存占用序列  
  - `peak_l1`: L1 峰值内存
  - `peak_ub`: UB 峰值内存

**功能:**
- 逐步模拟调度执行过程
- 累计计算内存占用变化
- 记录峰值内存占用

## 交互式界面

### 组件定义
```python
sched_dd = widgets.Dropdown(options=[(p.name, str(p)) for p in sched_files], description='schedule')
run_btn = widgets.Button(description='计算与绘制', button_style='primary')
out = widgets.Output()
```

### 主要交互函数
```python
@run_btn.on_click
def _on_run(_):
    # 处理用户点击事件
    # 1. 读取选择的 schedule 文件
    # 2. 解析调度序列
    # 3. 加载对应的 JSON 图数据
    # 4. 计算内存变化序列
    # 5. 生成 Plotly 可视化图表
```

## 目录结构和常量

```python
ROOT = Path.cwd()                           # 当前工作目录
JSON_DIR = ROOT / 'Json版本'                # JSON 文件目录
SCHED_DIR = ROOT / 'Attachment' / 'Problem1' # 调度文件目录
```

## 可视化输出

### 图表特性
- 使用 Plotly 生成交互式折线图
- 同时显示 L1 和 UB 内存占用曲线
- X 轴：调度步骤（时间）
- Y 轴：累计内存占用
- 支持缩放、平移等交互操作

### 输出信息
```
JSON: <文件名> | 序列长度: <节点数>
峰值 L1: <峰值内存> | 峰值 UB: <峰值内存>
```

## 使用流程

1. **准备数据**: 确保 Json版本 目录下有 JSON 文件，Problem1 目录下有对应的 schedule.txt 文件

2. **运行 Notebook**: 执行前两个单元格加载依赖和定义函数

3. **选择文件**: 在下拉菜单中选择要分析的 schedule 文件

4. **生成可视化**: 点击"计算与绘制"按钮，查看内存变化曲线和峰值统计

## 错误处理

- **文件不存在**: 自动提示未找到 schedule 文件或对应 JSON 文件
- **格式错误**: 自动跳过 schedule.txt 中的非整数行
- **图形显示**: 需要正确安装 plotly 和 nbformat 依赖

## 依赖要求

```
pandas
networkx
plotly
ipywidgets
nbformat>=4.2.0
```
