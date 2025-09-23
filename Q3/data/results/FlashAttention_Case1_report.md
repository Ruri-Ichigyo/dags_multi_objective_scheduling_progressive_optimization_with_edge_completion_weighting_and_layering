# FlashAttention_Case1 算法对比报告\n\n测试算法数量: 5\n图规模: 6952 节点, 11184 边\n\n## 各指标最佳算法\n- fitness: greedy\n- execution_time: topological\n- spill_cost: greedy\n- memory_peak: greedy\n\n## 算法性能对比\n      algorithm  execution_time  spill_cost  memory_peak  fitness_score  pipeline_efficiency  schedule_length
    topological        327680.0      485664       248976       0.009895                  1.0             6952
         greedy        327680.0      349848       158404       0.012941                  1.0             6952
ga_conservative        327680.0      471536       239478       0.008360                  1.0             6952
    ga_balanced        327680.0      473856       238686       0.010092                  1.0             6952
  ga_aggressive        327680.0      474580       239858       0.011839                  1.0             6952