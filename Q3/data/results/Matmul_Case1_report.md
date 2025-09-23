# Matmul_Case1 算法对比报告\n\n测试算法数量: 5\n图规模: 30976 节点, 55040 边\n\n## 各指标最佳算法\n- fitness: ga_aggressive\n- execution_time: topological\n- spill_cost: greedy\n- memory_peak: greedy\n\n## 算法性能对比\n      algorithm  execution_time  spill_cost  memory_peak  fitness_score  pipeline_efficiency  schedule_length
    topological       5242880.0     2349056      1179648       0.001810                  1.0            30976
         greedy       5242880.0     2027776       875904       0.002077                  1.0            30976
ga_conservative       5242880.0     2291200      1146240       0.001437                  1.0            30976
    ga_balanced       5242880.0     2277120      1132160       0.001863                  1.0            30976
  ga_aggressive       5242880.0     2278144      1120512       0.002281                  1.0            30976