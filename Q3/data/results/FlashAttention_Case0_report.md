# FlashAttention_Case0 算法对比报告\n\n测试算法数量: 5\n图规模: 1716 节点, 2712 边\n\n## 各指标最佳算法\n- fitness: greedy\n- execution_time: topological\n- spill_cost: greedy\n- memory_peak: greedy\n\n## 算法性能对比\n      algorithm  execution_time  spill_cost  memory_peak  fitness_score  pipeline_efficiency  schedule_length
    topological         81920.0      116240        64264       0.038922                  1.0             1716
         greedy         81920.0       71472        34678       0.056333                  1.0             1716
ga_conservative         81920.0      112656        60546       0.032901                  1.0             1716
    ga_balanced         81920.0      112048        60252       0.040010                  1.0             1716
  ga_aggressive         81920.0      108304        59142       0.048294                  1.0             1716