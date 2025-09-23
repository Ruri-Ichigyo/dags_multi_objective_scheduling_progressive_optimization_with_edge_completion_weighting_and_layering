# Conv_Case0 算法对比报告\n\n测试算法数量: 5\n图规模: 2580 节点, 3869 边\n\n## 各指标最佳算法\n- fitness: ga_aggressive\n- execution_time: topological\n- spill_cost: greedy\n- memory_peak: greedy\n\n## 算法性能对比\n      algorithm  execution_time  spill_cost  memory_peak  fitness_score  pipeline_efficiency  schedule_length
    topological       3486770.0      292910       150807       0.013377                  1.0             2580
         greedy       3486770.0      218948       113722       0.017643                  1.0             2580
ga_conservative       3486770.0      241778       124434       0.012116                  1.0             2580
    ga_balanced       3486770.0      233124       119581       0.016625                  1.0             2580
  ga_aggressive       3486770.0      219762       113931       0.021905                  1.0             2580