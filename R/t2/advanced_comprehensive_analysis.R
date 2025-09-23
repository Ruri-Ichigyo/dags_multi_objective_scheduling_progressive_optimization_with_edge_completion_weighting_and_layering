library(jsonlite)
library(ggplot2)
library(dplyr)
library(tidyr)
library(plotly)
library(viridis)
library(scales)

# 设置工作目录和数据路径
base_path <- "/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code"
data_path <- file.path(base_path, "Attachment", "Problem3")

# 读取JSON数据文件
json_files <- list.files(data_path, pattern = "*_algorithm_summary.json", full.names = TRUE)

# 初始化数据框
algorithm_data <- data.frame()

# 读取所有JSON文件
for (file in json_files) {
  data <- fromJSON(file)

  # 提取数据
  row <- data.frame(
    task_name = data$task_name,
    best_algorithm = data$best_algorithm,
    execution_time = data$best_performance$execution_time,
    spill_cost = data$best_performance$spill_cost,
    fitness_score = data$best_performance$fitness_score,
    memory_peak = data$best_performance$memory_peak,
    stringsAsFactors = FALSE
  )

  algorithm_data <- rbind(algorithm_data, row)
}

# 数据预处理
algorithm_data$task_type <- gsub("_Case[0-9]", "", algorithm_data$task_name)
algorithm_data$case <- gsub(".*_Case", "Case", algorithm_data$task_name)

# 1. 简化雷达图 - 综合性能评估
# 数据标准化
algorithm_data_norm <- algorithm_data %>%
  mutate(
    exec_time_score = 100 * (1 - (execution_time - min(execution_time)) / (max(execution_time) - min(execution_time))),
    memory_score = 100 * (1 - (memory_peak - min(memory_peak)) / (max(memory_peak) - min(memory_peak))),
    spill_score = 100 * (1 - (spill_cost - min(spill_cost)) / (max(spill_cost) - min(spill_cost))),
    fitness_score_norm = 100 * fitness_score / max(fitness_score)
  )

# 创建简化的雷达图风格图表
radar_summary <- algorithm_data_norm %>%
  group_by(best_algorithm) %>%
  summarise(
    执行效率 = mean(exec_time_score),
    内存效率 = mean(memory_score),
    Spill优化 = mean(spill_score),
    适应度得分 = mean(fitness_score_norm),
    .groups = 'drop'
  ) %>%
  pivot_longer(cols = -best_algorithm, names_to = "metric", values_to = "score")

p1 <- ggplot(radar_summary, aes(x = metric, y = score, color = best_algorithm, group = best_algorithm)) +
  geom_line(size = 1.5, alpha = 0.8) +
  geom_point(size = 3, alpha = 0.9) +
  coord_polar() +
  labs(title = "算法综合性能雷达风格图",
       subtitle = "展示不同算法在各维度的综合表现",
       color = "算法类型") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    axis.text.x = element_text(size = 10, face = "bold"),
    legend.position = "bottom"
  ) +
  scale_color_viridis_d() +
  scale_y_continuous(limits = c(0, 100))

# 2. 河流图替代桑基图
river_data <- algorithm_data %>%
  count(task_type, best_algorithm) %>%
  group_by(task_type) %>%
  mutate(percentage = n / sum(n) * 100) %>%
  ungroup()

p2 <- ggplot(river_data, aes(x = task_type, y = percentage, fill = best_algorithm)) +
  geom_bar(stat = "identity", position = "stack", alpha = 0.8) +
  geom_text(aes(label = ifelse(percentage > 10, paste0(best_algorithm, "\n", round(percentage, 1), "%"), "")),
            position = position_stack(vjust = 0.5), size = 3, fontface = "bold", color = "white") +
  labs(title = "任务类型与算法选择分布",
       subtitle = "展示不同任务类型中各算法的使用比例",
       x = "任务类型",
       y = "百分比",
       fill = "最佳算法") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "bottom"
  ) +
  scale_fill_viridis_d() +
  scale_y_continuous(labels = function(x) paste0(x, "%"))

# 3. 简化层次结构图替代树形图
hierarchy_data <- algorithm_data %>%
  group_by(task_type, best_algorithm) %>%
  summarise(
    avg_fitness = mean(fitness_score),
    count = n(),
    total_performance = avg_fitness * count,
    .groups = 'drop'
  )

p3 <- ggplot(hierarchy_data, aes(x = task_type, y = total_performance, fill = best_algorithm)) +
  geom_bar(stat = "identity", position = "stack", alpha = 0.8) +
  geom_text(aes(label = ifelse(total_performance > max(total_performance) * 0.1,
                              paste0(best_algorithm, "\n", round(avg_fitness, 3)), "")),
            position = position_stack(vjust = 0.5), size = 3, fontface = "bold", color = "white") +
  labs(title = "算法性能层次结构图",
       subtitle = "面积大小反映综合性能权重 (适应度 × 任务数)",
       x = "任务类型",
       y = "综合性能得分",
       fill = "最佳算法") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "bottom"
  ) +
  scale_fill_viridis_d(option = "plasma") +
  scale_y_continuous(expand = expansion(mult = c(0, 0.1)))

# 4. 高级平行坐标图
parallel_data <- algorithm_data %>%
  select(task_name, execution_time, memory_peak, spill_cost, fitness_score) %>%
  mutate(
    exec_norm = (execution_time - min(execution_time)) / (max(execution_time) - min(execution_time)),
    memory_norm = (memory_peak - min(memory_peak)) / (max(memory_peak) - min(memory_peak)),
    spill_norm = (spill_cost - min(spill_cost)) / (max(spill_cost) - min(spill_cost)),
    fitness_norm = fitness_score / max(fitness_score)
  ) %>%
  select(task_name, exec_norm, memory_norm, spill_norm, fitness_norm) %>%
  pivot_longer(cols = -task_name, names_to = "metric", values_to = "value") %>%
  mutate(metric = case_when(
    metric == "exec_norm" ~ "执行时间",
    metric == "memory_norm" ~ "内存使用",
    metric == "spill_norm" ~ "Spill成本",
    metric == "fitness_norm" ~ "适应度得分"
  ))

p4 <- ggplot(parallel_data, aes(x = metric, y = value, group = task_name, color = task_name)) +
  geom_line(alpha = 0.7, size = 1.2) +
  geom_point(size = 3, alpha = 0.8) +
  labs(title = "算法性能平行坐标图",
       subtitle = "展示各任务在不同性能维度上的表现模式",
       x = "性能维度",
       y = "标准化值 (0-1)",
       color = "任务名称") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "bottom",
    legend.text = element_text(size = 8)
  ) +
  scale_color_viridis_d() +
  scale_y_continuous(labels = percent)

# 5. 高级漏斗图 - 性能等级分布
performance_bins <- algorithm_data %>%
  mutate(
    performance_level = case_when(
      fitness_score >= quantile(fitness_score, 0.8) ~ "优秀 (Top 20%)",
      fitness_score >= quantile(fitness_score, 0.6) ~ "良好 (60-80%)",
      fitness_score >= quantile(fitness_score, 0.4) ~ "中等 (40-60%)",
      fitness_score >= quantile(fitness_score, 0.2) ~ "一般 (20-40%)",
      TRUE ~ "待优化 (Bottom 20%)"
    )
  ) %>%
  count(performance_level) %>%
  mutate(
    percentage = n / sum(n) * 100,
    performance_level = factor(performance_level,
                              levels = c("优秀 (Top 20%)", "良好 (60-80%)",
                                       "中等 (40-60%)", "一般 (20-40%)", "待优化 (Bottom 20%)")),
    y_pos = cumsum(percentage) - percentage/2
  )

p5 <- ggplot(performance_bins, aes(x = 1, y = percentage, fill = performance_level)) +
  geom_bar(stat = "identity", width = 0.8) +
  geom_text(aes(x = 1.4, y = y_pos, label = paste0(performance_level, "\n",
                                                    n, "个任务 (", round(percentage, 1), "%)")),
            size = 3, fontface = "bold") +
  coord_flip() +
  labs(title = "算法性能等级分布漏斗图",
       subtitle = "基于适应度得分的性能等级划分",
       fill = "性能等级") +
  theme_void() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    legend.position = "right"
  ) +
  scale_fill_viridis_d(option = "plasma", direction = -1) +
  xlim(0.5, 2)

# 保存图表
ggsave("t2/radar_style_chart.png", p1, width = 12, height = 10, dpi = 300)
ggsave("t2/river_chart.png", p2, width = 12, height = 8, dpi = 300)
ggsave("t2/hierarchy_chart.png", p3, width = 14, height = 10, dpi = 300)
ggsave("t2/parallel_coordinates.png", p4, width = 14, height = 8, dpi = 300)
ggsave("t2/funnel_chart.png", p5, width = 12, height = 6, dpi = 300)

# 输出信息
cat("=== T2: 高级综合分析图表已生成 ===\n")
cat("- radar_style_chart.png: 算法综合性能雷达风格图\n")
cat("- river_chart.png: 任务类型与算法选择分布河流图\n")
cat("- hierarchy_chart.png: 算法性能层次结构图\n")
cat("- parallel_coordinates.png: 算法性能平行坐标图\n")
cat("- funnel_chart.png: 算法性能等级分布漏斗图\n")