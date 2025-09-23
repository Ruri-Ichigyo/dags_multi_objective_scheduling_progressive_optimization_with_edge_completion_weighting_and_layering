#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q3 深度学习编译器性能优化问题 - 优化版本

功能特点:
1. 支持多种优化算法 (拓扑排序, 贪心, 遗传算法变种)
2. 结果保存到 Q3/data 目录
3. Plotly 可视化算法对比
4. 修复了 JSON 数据结构处理问题
"""

import numpy as np
import pandas as pd
import networkx as nx
import json
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set, Optional, Union
from collections import defaultdict, deque
from dataclasses import dataclass
import heapq
import copy
import warnings
warnings.filterwarnings('ignore')

# 可选导入，如果没有安装则跳过可视化功能
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️  matplotlib未安装，部分图表功能将不可用")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("⚠️  plotly未安装，交互式图表功能将不可用")

# 基础配置
ROOT = Path.cwd()
JSON_DIR = ROOT / "Json版本"
CACHE_CAPACITIES = {
    "L1": 4096, "UB": 1024, "L0A": 256, "L0B": 256, "L0C": 512
}

# 硬件单元执行时间模型
HARDWARE_TIMING = {
    "CUBE": {"base_cycles": 10, "throughput": 1},
    "VECTOR": {"base_cycles": 3, "throughput": 2},
    "MTE1": {"base_cycles": 5, "throughput": 1},
    "MTE2": {"base_cycles": 5, "throughput": 1},
    "MTE3": {"base_cycles": 5, "throughput": 1},
    "FIXP": {"base_cycles": 2, "throughput": 4},
    "MEMORY": {"base_cycles": 1, "throughput": 8}
}

def load_graph_fixed(json_path):
    """修复的图加载函数 - 正确处理JSON数据结构"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    graph = nx.DiGraph()
    nodes_map = {}

    # 获取节点数据 - 支持大小写变体
    nodes_data = data.get('Nodes', data.get('nodes', []))
    edges_data = data.get('Edges', data.get('edges', []))

    print(f"🔍 加载JSON: 节点数={len(nodes_data)}, 边数={len(edges_data)}")

    # 构建节点映射
    for node in nodes_data:
        # 获取节点ID - 支持Id或id
        node_id = node.get('Id', node.get('id'))
        if node_id is None:
            continue

        # 标准化节点数据
        normalized_node = {
            'Op': node.get('Op', node.get('op', '')),
            'BufId': node.get('BufId', node.get('bufId')),
            'Size': node.get('Size', node.get('size', 0)),
            'Type': node.get('Type', node.get('type', '')),
            'Pipe': node.get('Pipe', node.get('pipe', 'MEMORY')),
            'Cycles': node.get('Cycles', node.get('cycles', 1)),
            'Bufs': node.get('Bufs', node.get('bufs', []))
        }

        graph.add_node(node_id, **normalized_node)
        nodes_map[node_id] = normalized_node

    # 构建边
    if edges_data:
        for edge in edges_data:
            if isinstance(edge, list) and len(edge) >= 2:
                # 边是列表形式 [source, target]
                source, target = edge[0], edge[1]
                if source is not None and target is not None:
                    graph.add_edge(source, target)
            elif isinstance(edge, dict):
                # 边是字典形式
                source = edge.get('source', edge.get('Source'))
                target = edge.get('target', edge.get('Target'))
                if source is not None and target is not None:
                    graph.add_edge(source, target)
    else:
        # 根据依赖关系推断边
        for node_id, node in nodes_map.items():
            if node.get('Bufs'):
                for buf_id in node['Bufs']:
                    # 找到分配这个buf_id的节点
                    for prev_id, prev_node in nodes_map.items():
                        if (prev_node.get('Op') == 'ALLOC' and
                            prev_node.get('BufId') == buf_id and
                            prev_id < node_id):
                            graph.add_edge(prev_id, node_id)

    print(f"🔍 图构建完成: {graph.number_of_nodes()} 节点, {graph.number_of_edges()} 边")
    return graph, nodes_map

@dataclass
class OptimizationResult:
    """优化结果数据类"""
    algorithm_name: str
    schedule: List[int]
    execution_time: float
    spill_cost: int
    cache_allocations: Dict
    fitness_score: float
    pipeline_efficiency: float
    memory_peak: int

class PipelineSimulator:
    """流水线模拟器"""

    def __init__(self, hardware_timing: Dict = None):
        self.hardware_timing = hardware_timing or HARDWARE_TIMING
        self.hardware_units = list(self.hardware_timing.keys())
        self._simulation_cache = {}

    def simulate_execution(self, order: List[int], nodes_map: Dict[int, Dict[str, Any]]) -> Tuple[float, Dict]:
        """模拟执行过程，计算真实执行时间"""
        cache_key = hash(tuple(order))
        if cache_key in self._simulation_cache:
            return self._simulation_cache[cache_key]

        unit_time = {unit: 0.0 for unit in self.hardware_units}
        node_end_times = {}

        for node_id in order:
            node = nodes_map.get(node_id, {})
            if not isinstance(node, dict):
                continue

            op = node.get("Op", "")
            pipe = node.get("Pipe", "MEMORY")
            cycles = max(1, node.get("Cycles", 1) or 1)

            # 确定执行单元
            if pipe in self.hardware_timing:
                unit = pipe
            elif op in {"ALLOC", "FREE", "COPY_IN", "COPY_OUT"}:
                unit = "MEMORY"
            else:
                unit = "CUBE"

            # 计算执行时间
            timing = self.hardware_timing[unit]
            exec_time = max(1, cycles * timing["base_cycles"] / timing["throughput"])

            unit_time[unit] += exec_time
            node_end_times[node_id] = unit_time[unit]

        # 计算总执行时间和并行效率
        total_time = max(unit_time.values())
        sequential_time = sum(node_end_times.values())
        parallel_efficiency = min(1.0, sequential_time / (total_time * len(self.hardware_units)) if total_time > 0 else 0)

        execution_info = {
            "total_time": total_time,
            "unit_times": unit_time,
            "parallel_efficiency": parallel_efficiency,
            "sequential_time": sequential_time
        }

        result = (total_time, execution_info)
        self._simulation_cache[cache_key] = result
        return result

class MultiObjectiveEvaluator:
    """多目标评价器"""

    def __init__(self, alpha: float = 0.6, beta: float = 0.4, spill_penalty: float = 1.0):
        self.alpha = alpha
        self.beta = beta
        self.spill_penalty = spill_penalty
        self.pipeline_simulator = PipelineSimulator()
        self._evaluation_cache = {}

    def evaluate(self, order: List[int], nodes_map: Dict[int, Dict[str, Any]],
                 graph: nx.DiGraph = None, algorithm_name: str = "unknown") -> OptimizationResult:
        """综合评价调度序列"""
        cache_key = hash(tuple(order))
        if cache_key in self._evaluation_cache:
            cached_result = self._evaluation_cache[cache_key]
            cached_result.algorithm_name = algorithm_name  # 更新算法名称
            return cached_result

        # 执行时间评估
        execution_time, exec_info = self.pipeline_simulator.simulate_execution(order, nodes_map)

        # SPILL代价估算
        spill_cost = self._fast_spill_estimation(order, nodes_map)

        # 内存峰值估算
        memory_peak = self._fast_memory_peak(order, nodes_map)

        # 适应度计算
        time_score = 1.0 / (1.0 + execution_time * 0.001)
        spill_score = 1.0 / (1.0 + spill_cost * self.spill_penalty * 0.0001)

        fitness = self.alpha * time_score + self.beta * spill_score

        result = OptimizationResult(
            algorithm_name=algorithm_name,
            schedule=order,
            execution_time=execution_time,
            spill_cost=spill_cost,
            cache_allocations={},
            fitness_score=fitness,
            pipeline_efficiency=exec_info["parallel_efficiency"],
            memory_peak=memory_peak
        )

        self._evaluation_cache[cache_key] = result
        return result

    def _fast_spill_estimation(self, order: List[int], nodes_map: Dict[int, Dict[str, Any]]) -> int:
        """快速SPILL代价估算"""
        total_cost = 0
        cache_usage = [0] * len(CACHE_CAPACITIES)
        cache_types = list(CACHE_CAPACITIES.keys())
        cache_limits = list(CACHE_CAPACITIES.values())

        for node_id in order:
            node = nodes_map.get(node_id, {})
            if not isinstance(node, dict):
                continue

            op = node.get("Op", "")

            if op == "ALLOC":
                cache_type = node.get("Type", "")
                size = node.get("Size", 0) or 0

                if cache_type in cache_types:
                    idx = cache_types.index(cache_type)
                    cache_usage[idx] += size

                    if cache_usage[idx] > cache_limits[idx]:
                        overflow = cache_usage[idx] - cache_limits[idx]
                        total_cost += overflow * 2
                        cache_usage[idx] = cache_limits[idx]

            elif op == "FREE":
                cache_type = node.get("Type", "")
                size = node.get("Size", 0) or 0

                if cache_type in cache_types:
                    idx = cache_types.index(cache_type)
                    cache_usage[idx] = max(0, cache_usage[idx] - size)

        return total_cost

    def _fast_memory_peak(self, order: List[int], nodes_map: Dict[int, Dict[str, Any]]) -> int:
        """快速内存峰值估算"""
        current_memory = 0
        peak_memory = 0

        for node_id in order:
            node = nodes_map.get(node_id, {})
            if not isinstance(node, dict):
                continue

            op = node.get("Op", "")
            size = node.get("Size", 0) or 0

            if op == "ALLOC":
                current_memory += size
                peak_memory = max(peak_memory, current_memory)
            elif op == "FREE":
                current_memory = max(0, current_memory - size)

        return peak_memory

class GeneticAlgorithmOptimizer:
    """遗传算法优化器"""

    def __init__(self, graph: nx.DiGraph, nodes_map: Dict[int, Dict[str, Any]],
                 population_size: int = 20, generations: int = 30,
                 mutation_rate: float = 0.15, crossover_rate: float = 0.8,
                 elite_ratio: float = 0.2, alpha: float = 0.6, beta: float = 0.4,
                 algorithm_name: str = "genetic"):
        """优化版构造函数"""
        self.graph = graph
        self.nodes_map = nodes_map
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_ratio = elite_ratio
        self.algorithm_name = algorithm_name

        # 初始化评价器
        self.evaluator = MultiObjectiveEvaluator(alpha=alpha, beta=beta)

        # 预计算拓扑信息
        self.nodes = list(graph.nodes())
        self.node_count = len(self.nodes)
        self._precompute_dependencies()

        # 生成初始种群基础
        self.topo_orders = self._generate_initial_topo_orders()

        # 统计信息
        self.best_fitness_history = []
        self.avg_fitness_history = []

    def _precompute_dependencies(self):
        """预计算依赖关系以加速验证"""
        self.ancestors = {}
        self.descendants = {}

        for node in self.nodes:
            self.ancestors[node] = set(nx.ancestors(self.graph, node))
            self.descendants[node] = set(nx.descendants(self.graph, node))

    def _generate_initial_topo_orders(self, num_orders: int = 3) -> List[List[int]]:
        """生成高质量的初始拓扑排序"""
        orders = []

        # 基准拓扑序
        base_order = list(nx.topological_sort(self.graph))
        orders.append(base_order)

        # 生成随机变种
        for _ in range(num_orders - 1):
            order = self._fast_random_topo_sort()
            orders.append(order)

        return orders

    def _fast_random_topo_sort(self) -> List[int]:
        """快速随机拓扑排序"""
        in_degree = [self.graph.in_degree(node) for node in self.nodes]
        available = [i for i, degree in enumerate(in_degree) if degree == 0]
        result = []
        node_to_idx = {node: i for i, node in enumerate(self.nodes)}

        while available:
            idx = available.pop(random.randint(0, len(available) - 1))
            node = self.nodes[idx]
            result.append(node)

            for successor in self.graph.successors(node):
                succ_idx = node_to_idx[successor]
                in_degree[succ_idx] -= 1
                if in_degree[succ_idx] == 0:
                    available.append(succ_idx)

        return result

    def _initialize_population(self) -> List[List[int]]:
        """快速初始化种群"""
        population = []

        for order in self.topo_orders:
            population.append(order.copy())

        while len(population) < self.population_size:
            if len(self.topo_orders) > 0:
                parent = random.choice(self.topo_orders)
                child = self._fast_mutate(parent.copy())
                population.append(child)
            else:
                population.append(self._fast_random_topo_sort())

        return population[:self.population_size]

    def _fast_crossover(self, parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
        """优化的交叉操作"""
        n = len(parent1)

        start = random.randint(0, n//3)
        end = random.randint(start + max(1, n//6), min(n, start + n//2))

        def create_child(p1, p2):
            child = [-1] * n
            child[start:end] = p1[start:end]
            copied = set(child[start:end])

            j = 0
            for i in range(n):
                if child[i] == -1:
                    while j < len(p2) and p2[j] in copied:
                        j += 1
                    if j < len(p2):
                        child[i] = p2[j]
                        j += 1
            return child

        child1 = create_child(parent1, parent2)
        child2 = create_child(parent2, parent1)

        return child1, child2

    def _fast_mutate(self, individual: List[int]) -> List[int]:
        """快速变异操作"""
        n = len(individual)
        mutated = individual.copy()

        max_attempts = min(3, max(1, n//20))
        attempts = 0

        while attempts < max_attempts and random.random() < self.mutation_rate:
            if n >= 2:
                i, j = random.sample(range(n), 2)
                if i > j:
                    i, j = j, i

                node_i, node_j = mutated[i], mutated[j]

                if (node_j not in self.ancestors[node_i] and
                    node_i not in self.ancestors[node_j]):
                    mutated[i], mutated[j] = mutated[j], mutated[i]

            attempts += 1

        return mutated

    def optimize(self, verbose: bool = False) -> OptimizationResult:
        """优化的遗传算法主循环"""
        if verbose:
            print(f"开始{self.algorithm_name}优化: 种群={self.population_size}, 代数={self.generations}")

        population = self._initialize_population()
        best_overall = None
        stagnation_count = 0
        max_stagnation = 8

        for generation in range(self.generations):
            results = []
            fitness_scores = []

            for individual in population:
                result = self.evaluator.evaluate(individual, self.nodes_map, self.graph, self.algorithm_name)
                results.append(result)
                fitness_scores.append(result.fitness_score)

            best_fitness = max(fitness_scores)
            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            self.best_fitness_history.append(best_fitness)
            self.avg_fitness_history.append(avg_fitness)

            best_idx = fitness_scores.index(best_fitness)
            if best_overall is None or best_fitness > best_overall.fitness_score:
                best_overall = results[best_idx]
                stagnation_count = 0
            else:
                stagnation_count += 1

            if stagnation_count >= max_stagnation:
                if verbose:
                    print(f"第{generation}代早停")
                break

            if verbose and generation % 10 == 0:
                print(f"代数 {generation}: 最佳={best_fitness:.4f}, 平均={avg_fitness:.4f}")

            # 生成下一代
            new_population = []

            # 精英保留
            elite_count = max(1, int(self.population_size * self.elite_ratio))
            elite_indices = sorted(range(len(fitness_scores)),
                                 key=lambda x: fitness_scores[x], reverse=True)[:elite_count]
            for idx in elite_indices:
                new_population.append(population[idx])

            # 繁殖
            while len(new_population) < self.population_size:
                if random.random() < self.crossover_rate and len(population) >= 2:
                    total_fitness = sum(fitness_scores)
                    if total_fitness > 0:
                        weights = [f/total_fitness for f in fitness_scores]
                        parent1 = random.choices(population, weights=weights)[0]
                        parent2 = random.choices(population, weights=weights)[0]
                    else:
                        parent1, parent2 = random.sample(population, 2)

                    child1, child2 = self._fast_crossover(parent1, parent2)
                    child1 = self._fast_mutate(child1)
                    child2 = self._fast_mutate(child2)

                    new_population.extend([child1, child2])
                else:
                    parent = random.choice(population)
                    child = self._fast_mutate(parent.copy())
                    new_population.append(child)

            population = new_population[:self.population_size]

        if verbose:
            print(f"{self.algorithm_name}优化完成! 适应度: {best_overall.fitness_score:.4f}")

        return best_overall

def greedy_heuristic_scheduling(graph: nx.DiGraph, algorithm_name: str = "greedy") -> List[int]:
    """贪心启发式调度算法"""
    scheduled = []
    remaining = set(graph.nodes())
    in_degree = dict(graph.in_degree())

    while remaining:
        ready_nodes = [node for node in remaining if in_degree[node] == 0]

        if not ready_nodes:
            ready_nodes = [min(remaining, key=lambda x: in_degree[x])]

        def priority(node_id):
            return (node_id % 100, node_id)

        next_node = min(ready_nodes, key=priority)

        scheduled.append(next_node)
        remaining.remove(next_node)

        for successor in graph.successors(next_node):
            in_degree[successor] -= 1

    return scheduled

class Q3OptimizedSuite:
    """Q3优化套件 - 支持多算法和数据保存"""

    def __init__(self, json_path: Path):
        """初始化优化套件"""
        self.json_path = json_path
        self.task_name = json_path.stem
        self.graph, self.nodes_map = load_graph_fixed(json_path)
        self.results = {}

        # 创建Q3/data目录结构
        self.q3_data_dir = Path("Q3/data")
        self.algorithms_dir = self.q3_data_dir / "algorithms"
        self.results_dir = self.q3_data_dir / "results"
        self.vis_dir = self.q3_data_dir / "visualizations"

        for dir_path in [self.algorithms_dir, self.results_dir, self.vis_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        print(f"🔧 初始化 {self.task_name} 优化套件")
        print(f"   图规模: {self.graph.number_of_nodes()} 节点, {self.graph.number_of_edges()} 边")

    def run_comprehensive_optimization(self, ga_generations: int = 20, ga_population: int = 10, verbose: bool = True):
        """运行综合优化分析"""
        print(f"\\n🚀 开始 {self.task_name} 多算法优化...")

        evaluator = MultiObjectiveEvaluator()

        # 1. 基础拓扑排序
        if verbose:
            print("1️⃣ 基础拓扑排序...")
        topo_schedule = list(nx.topological_sort(self.graph))
        topo_result = evaluator.evaluate(topo_schedule, self.nodes_map, self.graph, "topological")
        self.results["topological"] = topo_result

        # 2. 贪心启发式
        if verbose:
            print("2️⃣ 贪心启发式...")
        greedy_schedule = greedy_heuristic_scheduling(self.graph)
        greedy_result = evaluator.evaluate(greedy_schedule, self.nodes_map, self.graph, "greedy")
        self.results["greedy"] = greedy_result

        # 3. 遗传算法 - 保守
        if verbose:
            print("3️⃣ 遗传算法(保守)...")
        ga_conservative = GeneticAlgorithmOptimizer(
            self.graph, self.nodes_map,
            population_size=max(5, ga_population//2),
            generations=max(8, ga_generations//2),
            alpha=0.7, beta=0.3,
            algorithm_name="ga_conservative"
        )
        ga_conservative_result = ga_conservative.optimize(verbose=False)
        self.results["ga_conservative"] = ga_conservative_result

        # 4. 遗传算法 - 平衡
        if verbose:
            print("4️⃣ 遗传算法(平衡)...")
        ga_balanced = GeneticAlgorithmOptimizer(
            self.graph, self.nodes_map,
            population_size=ga_population,
            generations=ga_generations,
            alpha=0.6, beta=0.4,
            algorithm_name="ga_balanced"
        )
        ga_balanced_result = ga_balanced.optimize(verbose=False)
        self.results["ga_balanced"] = ga_balanced_result

        # 5. 遗传算法 - 激进
        if verbose:
            print("5️⃣ 遗传算法(激进)...")
        ga_aggressive = GeneticAlgorithmOptimizer(
            self.graph, self.nodes_map,
            population_size=min(30, ga_population*2),
            generations=min(50, ga_generations*2),
            alpha=0.5, beta=0.5,
            mutation_rate=0.2,
            algorithm_name="ga_aggressive"
        )
        ga_aggressive_result = ga_aggressive.optimize(verbose=False)
        self.results["ga_aggressive"] = ga_aggressive_result

        # 保存数据和生成可视化
        self._save_algorithms_data()
        self._generate_comparison_report()
        self._create_plotly_visualizations()

        if verbose:
            print(f"✅ {self.task_name} 优化完成")

        return self.results

    def _save_algorithms_data(self):
        """保存所有算法结果到Q3/data目录"""
        # 保存算法性能数据
        algorithms_data = {}
        for result in self.results.values():
            algorithms_data[result.algorithm_name] = {
                "execution_time": float(result.execution_time),
                "spill_cost": int(result.spill_cost),
                "memory_peak": int(result.memory_peak),
                "fitness_score": float(result.fitness_score),
                "pipeline_efficiency": float(result.pipeline_efficiency),
                "schedule_length": len(result.schedule)
            }

        algorithms_file = self.algorithms_dir / f"{self.task_name}_algorithms.json"
        with open(algorithms_file, 'w', encoding='utf-8') as f:
            json.dump(algorithms_data, f, indent=2, ensure_ascii=False)

        # 保存每个算法的详细调度结果
        for result in self.results.values():
            schedule_file = self.algorithms_dir / f"{self.task_name}_{result.algorithm_name}_schedule.txt"
            with open(schedule_file, 'w') as f:
                for node_id in result.schedule:
                    f.write(f"{node_id}\\n")

        print(f"💾 算法数据已保存: {self.algorithms_dir}")

    def _generate_comparison_report(self):
        """生成算法对比报告"""
        # 创建对比DataFrame
        comparison_data = []
        for result in self.results.values():
            comparison_data.append({
                "algorithm": result.algorithm_name,
                "execution_time": result.execution_time,
                "spill_cost": result.spill_cost,
                "memory_peak": result.memory_peak,
                "fitness_score": result.fitness_score,
                "pipeline_efficiency": result.pipeline_efficiency,
                "schedule_length": len(result.schedule)
            })

        comparison_df = pd.DataFrame(comparison_data)

        # 找出各指标最佳算法
        best_algorithms = {}
        best_algorithms["fitness"] = comparison_df.loc[comparison_df['fitness_score'].idxmax(), 'algorithm']
        best_algorithms["execution_time"] = comparison_df.loc[comparison_df['execution_time'].idxmin(), 'algorithm']
        best_algorithms["spill_cost"] = comparison_df.loc[comparison_df['spill_cost'].idxmin(), 'algorithm']
        best_algorithms["memory_peak"] = comparison_df.loc[comparison_df['memory_peak'].idxmin(), 'algorithm']

        # 保存对比结果
        comparison_file = self.results_dir / f"{self.task_name}_comparison.csv"
        comparison_df.to_csv(comparison_file, index=False, encoding='utf-8')

        # 生成报告
        summary = f"# {self.task_name} 算法对比报告\\n\\n"
        summary += f"测试算法数量: {len(comparison_data)}\\n"
        summary += f"图规模: {self.graph.number_of_nodes()} 节点, {self.graph.number_of_edges()} 边\\n\\n"

        summary += "## 各指标最佳算法\\n"
        for metric, best_alg in best_algorithms.items():
            summary += f"- {metric}: {best_alg}\\n"

        summary += "\\n## 算法性能对比\\n"
        summary += comparison_df.to_string(index=False)

        report_file = self.results_dir / f"{self.task_name}_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(summary)

        self.comparison_report = {
            "best_algorithms": best_algorithms,
            "comparison_df": comparison_df,
            "summary": summary
        }

        print(f"📋 对比报告已保存: {self.results_dir}")

    def _create_plotly_visualizations(self):
        """创建Plotly可视化图表"""
        if not HAS_PLOTLY:
            print("⚠️  Plotly未安装，跳过可视化")
            return

        # 1. 性能对比柱状图
        self._create_performance_bars()

        # 2. 多维度雷达图
        self._create_radar_chart()

        # 3. 算法排名图
        self._create_ranking_chart()

        print(f"📈 可视化图表已保存: {self.vis_dir}")

    def _create_performance_bars(self):
        """创建性能对比柱状图"""
        comparison_df = self.comparison_report["comparison_df"]

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("执行时间", "溢出成本", "内存峰值", "适应度分数"),
        )

        colors = px.colors.qualitative.Set1

        fig.add_bar(x=comparison_df['algorithm'], y=comparison_df['execution_time'],
                   name='执行时间', marker_color=colors[0], row=1, col=1, showlegend=False)

        fig.add_bar(x=comparison_df['algorithm'], y=comparison_df['spill_cost'],
                   name='溢出成本', marker_color=colors[1], row=1, col=2, showlegend=False)

        fig.add_bar(x=comparison_df['algorithm'], y=comparison_df['memory_peak'],
                   name='内存峰值', marker_color=colors[2], row=2, col=1, showlegend=False)

        fig.add_bar(x=comparison_df['algorithm'], y=comparison_df['fitness_score'],
                   name='适应度', marker_color=colors[3], row=2, col=2, showlegend=False)

        fig.update_layout(
            height=800,
            title_text=f"{self.task_name} 算法性能对比",
            title_x=0.5
        )

        fig.update_xaxes(tickangle=45)

        chart_file = self.vis_dir / f"{self.task_name}_performance_comparison.html"
        fig.write_html(chart_file)

    def _create_radar_chart(self):
        """创建多维度雷达图"""
        comparison_df = self.comparison_report["comparison_df"]

        # 归一化数据
        normalized_df = comparison_df.copy()

        # 对于越小越好的指标，使用倒数归一化
        for col in ['execution_time', 'spill_cost', 'memory_peak']:
            if normalized_df[col].max() > normalized_df[col].min():
                max_val = normalized_df[col].max()
                min_val = normalized_df[col].min()
                normalized_df[f'{col}_norm'] = (1 - (normalized_df[col] - min_val) / (max_val - min_val)) * 100
            else:
                normalized_df[f'{col}_norm'] = 100

        # 对于越大越好的指标，直接归一化
        for col in ['fitness_score', 'pipeline_efficiency']:
            if normalized_df[col].max() > normalized_df[col].min():
                max_val = normalized_df[col].max()
                min_val = normalized_df[col].min()
                normalized_df[f'{col}_norm'] = ((normalized_df[col] - min_val) / (max_val - min_val)) * 100
            else:
                normalized_df[f'{col}_norm'] = 100

        fig = go.Figure()

        categories = ['执行时间', '溢出控制', '内存效率', '适应度', '流水线效率']
        colors = px.colors.qualitative.Set1

        for i, (_, row) in enumerate(normalized_df.iterrows()):
            values = [
                row['execution_time_norm'],
                row['spill_cost_norm'],
                row['memory_peak_norm'],
                row['fitness_score_norm'],
                row['pipeline_efficiency_norm']
            ]
            values += values[:1]  # 闭合雷达图

            fig.add_scatterpolar(
                r=values,
                theta=categories + categories[:1],
                fill='toself',
                name=row['algorithm'],
                line=dict(color=colors[i % len(colors)]),
                fillcolor=colors[i % len(colors)],
                opacity=0.4
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=f"{self.task_name} 算法多维度性能雷达图",
            title_x=0.5,
            height=600
        )

        radar_file = self.vis_dir / f"{self.task_name}_radar_chart.html"
        fig.write_html(radar_file)

    def _create_ranking_chart(self):
        """创建算法排名图"""
        comparison_df = self.comparison_report["comparison_df"]

        # 按适应度排序
        sorted_df = comparison_df.sort_values('fitness_score', ascending=False)

        fig = go.Figure()

        fig.add_bar(
            x=sorted_df['algorithm'],
            y=sorted_df['fitness_score'],
            marker_color=px.colors.qualitative.Set1[:len(sorted_df)],
            text=sorted_df['fitness_score'].round(4),
            textposition='auto'
        )

        fig.update_layout(
            title=f"{self.task_name} 算法适应度排名",
            title_x=0.5,
            xaxis_title="算法",
            yaxis_title="适应度分数",
            height=500
        )

        ranking_file = self.vis_dir / f"{self.task_name}_ranking.html"
        fig.write_html(ranking_file)

    def export_best_results(self, output_dir: Path = Path("Attachment/Problem3")):
        """导出最优结果到标准格式"""
        output_dir.mkdir(parents=True, exist_ok=True)

        if not hasattr(self, 'comparison_report'):
            print("❌ 无优化结果可导出")
            return

        # 选择最佳算法
        best_algorithm_name = self.comparison_report["best_algorithms"]["fitness"]
        best_result = self.results[best_algorithm_name]

        print(f"📤 导出最佳算法 {best_algorithm_name} 的结果...")

        # 1. 调度序列文件
        schedule_file = output_dir / f"{self.task_name}_schedule.txt"
        with open(schedule_file, "w") as f:
            for node_id in best_result.schedule:
                f.write(f"{node_id}\\n")

        # 2. 缓存分配文件
        memory_file = output_dir / f"{self.task_name}_memory.txt"
        with open(memory_file, "w") as f:
            current_offset = 0
            for node_id in best_result.schedule:
                node = self.nodes_map.get(node_id, {})
                if node.get("Op") == "ALLOC" and node.get("BufId") is not None:
                    buf_id = node["BufId"]
                    f.write(f"{buf_id}:{current_offset}\\n")
                    size = node.get("Size", 10)
                    current_offset += size

        # 3. SPILL操作文件
        spill_file = output_dir / f"{self.task_name}_spill.txt"
        with open(spill_file, "w") as f:
            if best_result.spill_cost > 0:
                # 简化SPILL处理
                spill_count = min(3, best_result.spill_cost // 1000)
                offset = 400
                for node_id in best_result.schedule[:spill_count]:
                    node = self.nodes_map.get(node_id, {})
                    if node.get("Op") == "ALLOC" and node.get("BufId") is not None:
                        buf_id = node["BufId"]
                        f.write(f"{buf_id}:{offset}\\n")
                        offset += 20

        # 4. 导出算法摘要
        summary_file = output_dir / f"{self.task_name}_algorithm_summary.json"
        summary_data = {
            "task_name": self.task_name,
            "best_algorithm": best_algorithm_name,
            "total_algorithms": len(self.results),
            "best_performance": {
                "execution_time": best_result.execution_time,
                "spill_cost": best_result.spill_cost,
                "fitness_score": best_result.fitness_score,
                "memory_peak": best_result.memory_peak
            }
        }

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        print(f"✅ 最优结果已导出到: {output_dir}")

def batch_optimize_all_cases(ga_generations: int = 15, ga_population: int = 8, verbose: bool = True):
    """批量优化所有测试案例"""
    json_files = list(JSON_DIR.glob("*.json"))
    if not json_files:
        print("❌ 未找到JSON测试文件")
        return {}

    print(f"🚀 开始批量优化 {len(json_files)} 个测试案例...")

    all_results = {}
    success_count = 0

    # 确保输出目录存在
    problem3_dir = Path("Attachment/Problem3")
    problem3_dir.mkdir(parents=True, exist_ok=True)

    # 收集全局对比数据
    global_comparison_data = []

    for i, json_file in enumerate(json_files, 1):
        task_name = json_file.stem
        print(f"\\n[{i}/{len(json_files)}] 正在优化: {task_name}")

        try:
            suite = Q3OptimizedSuite(json_file)
            results = suite.run_comprehensive_optimization(
                ga_generations=ga_generations,
                ga_population=ga_population,
                verbose=False
            )

            # 导出最优结果
            suite.export_best_results(problem3_dir)

            # 收集对比数据
            if hasattr(suite, 'comparison_report'):
                comparison_df = suite.comparison_report["comparison_df"]
                comparison_df['task_name'] = task_name
                global_comparison_data.append(comparison_df)

            all_results[task_name] = results
            success_count += 1

            print(f"✅ {task_name} 优化完成")

        except Exception as e:
            print(f"❌ {task_name} 优化失败: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            continue

    # 生成全局对比
    if global_comparison_data and HAS_PLOTLY:
        _create_global_comparison(global_comparison_data)

    # 生成总结报告
    summary_file = problem3_dir / "batch_optimization_summary_enhanced.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("# Problem 3 批量优化总结报告\\n\\n")
        f.write(f"测试案例数: {len(json_files)}\\n")
        f.write(f"成功案例数: {success_count}\\n")
        f.write(f"成功率: {success_count/len(json_files)*100:.1f}%\\n\\n")

        f.write("## 各案例最优算法摘要\\n\\n")
        for task_name, results in all_results.items():
            if results:
                best_result = max(results.values(), key=lambda r: r.fitness_score)
                f.write(f"### {task_name}\\n")
                f.write(f"- 最佳算法: {best_result.algorithm_name}\\n")
                f.write(f"- 执行时间: {best_result.execution_time:.2f}\\n")
                f.write(f"- 适应度: {best_result.fitness_score:.4f}\\n")
                f.write(f"- 溢出成本: {best_result.spill_cost}\\n\\n")

    print(f"\\n🎉 批量优化完成!")
    print(f"📊 成功优化: {success_count}/{len(json_files)} 个案例")
    print(f"📁 结果保存:")
    print(f"   - 标准格式: {problem3_dir}")
    print(f"   - 详细数据: Q3/data/")

    return all_results

def _create_global_comparison(global_comparison_data):
    """创建全局算法对比"""
    all_data = pd.concat(global_comparison_data, ignore_index=True)

    # 创建全局可视化目录
    global_vis_dir = Path("Q3/data/visualizations/global")
    global_vis_dir.mkdir(parents=True, exist_ok=True)

    # 1. 全局性能对比
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("全局执行时间对比", "全局溢出成本对比", "全局内存峰值对比", "全局适应度对比")
    )

    tasks = all_data['task_name'].unique()
    colors = px.colors.qualitative.Set1

    for i, task in enumerate(tasks):
        task_data = all_data[all_data['task_name'] == task]
        task_color = colors[i % len(colors)]

        fig.add_bar(x=task_data['algorithm'], y=task_data['execution_time'],
                   name=f'{task}', marker_color=task_color, row=1, col=1,
                   legendgroup=task)

        fig.add_bar(x=task_data['algorithm'], y=task_data['spill_cost'],
                   name=f'{task}', marker_color=task_color, row=1, col=2,
                   showlegend=False, legendgroup=task)

        fig.add_bar(x=task_data['algorithm'], y=task_data['memory_peak'],
                   name=f'{task}', marker_color=task_color, row=2, col=1,
                   showlegend=False, legendgroup=task)

        fig.add_bar(x=task_data['algorithm'], y=task_data['fitness_score'],
                   name=f'{task}', marker_color=task_color, row=2, col=2,
                   showlegend=False, legendgroup=task)

    fig.update_layout(
        height=1000,
        title_text="全局算法性能对比总览",
        title_x=0.5,
        barmode='group'
    )

    fig.update_xaxes(tickangle=45)

    global_chart_file = global_vis_dir / "global_performance_comparison.html"
    fig.write_html(global_chart_file)

    # 2. 算法效果统计
    algorithm_summary = all_data.groupby('algorithm').agg({
        'execution_time': ['mean', 'std'],
        'spill_cost': ['mean', 'std'],
        'memory_peak': ['mean', 'std'],
        'fitness_score': ['mean', 'std']
    }).round(4)

    summary_file = global_vis_dir / "global_algorithm_summary.csv"
    algorithm_summary.to_csv(summary_file, encoding='utf-8')

    print(f"🌐 全局对比已生成: {global_vis_dir}")

# 便捷函数
def optimize_single_case(json_path: Path, ga_generations: int = 20, ga_population: int = 10):
    """优化单个测试案例"""
    suite = Q3OptimizedSuite(json_path)
    results = suite.run_comprehensive_optimization(ga_generations, ga_population, verbose=True)
    suite.export_best_results()
    return results

def optimize_and_visualize_all():
    """生产环境：优化所有案例并生成完整的可视化对比"""
    print("🚀 Q3 深度学习编译器性能优化 - 生产版本")
    print("=" * 60)

    try:
        # 使用生产参数进行批量优化
        all_results = batch_optimize_all_cases(
            ga_generations=15,   # 适中的代数，平衡速度和质量
            ga_population=10,     # 适中的种群大小
            verbose=True
        )

        print(f"\n🎉 批量优化完成！成功优化 {len(all_results)} 个案例")

        # 显示优化结果摘要
        if all_results:
            print("\n📊 优化结果摘要:")
            for task_name, results in all_results.items():
                if results:
                    best_result = max(results.values(), key=lambda r: r.fitness_score)
                    print(f"  {task_name:20} | 最佳算法: {best_result.algorithm_name:15} | 适应度: {best_result.fitness_score:.4f}")

        # 检查生成的文件
        print(f"\n📁 生成的文件:")

        # Q3/data 文件
        q3_data_dir = Path("Q3/data")
        if q3_data_dir.exists():
            alg_files = list((q3_data_dir / "algorithms").glob("*"))
            result_files = list((q3_data_dir / "results").glob("*"))
            vis_files = list((q3_data_dir / "visualizations").glob("*"))

            print(f"  📊 Q3/data/algorithms: {len(alg_files)} 文件")
            print(f"  📋 Q3/data/results: {len(result_files)} 文件")
            print(f"  📈 Q3/data/visualizations: {len(vis_files)} 文件")

        # Attachment/Problem3 文件
        problem3_dir = Path("Attachment/Problem3")
        if problem3_dir.exists():
            std_files = list(problem3_dir.glob("*.txt"))
            json_files = list(problem3_dir.glob("*.json"))
            print(f"  📄 Attachment/Problem3 标准格式: {len(std_files)} 个txt文件, {len(json_files)} 个json文件")

        print("\n✅ Q3 优化流程完成!")
        print("\n🔍 查看结果:")
        print("  - Q3/data/visualizations/*.html - Plotly交互式图表")
        print("  - Q3/data/results/*.csv - 算法对比数据")
        print("  - Q3/data/algorithms/*.json - 详细算法性能")
        print("  - Attachment/Problem3/*_schedule.txt - 标准调度文件")

        return all_results

    except Exception as e:
        print(f"❌ 批量优化过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Q3 优化模块初始化完成")
    print(f"依赖状态: matplotlib={HAS_MATPLOTLIB}, plotly={HAS_PLOTLY}")

    print("\n" + "="*60)
    print("🎯 Q3 深度学习编译器性能优化系统")
    print("="*60)
    print("📋 功能:")
    print("  1. 多算法性能优化 (拓扑排序, 贪心, 遗传算法变种)")
    print("  2. 结果保存到 Q3/data (algorithms, results, visualizations)")
    print("  3. Plotly交互式可视化对比")
    print("  4. 标准格式导出到 Attachment/Problem3")
    print("\n💡 使用提示:")
    print("  - 快速测试: python quick_test_q3.py")
    print("  - 单案例优化: optimize_single_case(Path('Json版本/案例名.json'))")
    print("  - 完整批量优化: optimize_and_visualize_all()")
    print("\n⚠️  注意：完整批量优化可能需要较长时间，建议小批量测试后再运行")
    print("="*60)