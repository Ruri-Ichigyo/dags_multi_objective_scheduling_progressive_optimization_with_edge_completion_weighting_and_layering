library(jsonlite)
library(ggplot2)
library(dplyr)
library(tidyr)
library(plotly)
library(viridis)
library(scales)
library(gridExtra)
library(grid)

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

# 1. 简化流程图替代冲积图
flow_data <- algorithm_data %>%
  count(task_type, best_algorithm) %>%
  arrange(desc(n))

p1 <- ggplot(flow_data, aes(x = task_type, y = n, fill = best_algorithm)) +
  geom_bar(stat = "identity", position = "dodge", alpha = 0.8) +
  geom_text(aes(label = n), position = position_dodge(width = 0.9),
            vjust = -0.3, fontface = "bold") +
  labs(title = "任务类型与算法选择流程图",
       subtitle = "展示不同任务类型选择各算法的频次分布",
       x = "任务类型",
       y = "选择次数",
       fill = "最佳算法") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "bottom"
  ) +
  scale_fill_viridis_d() +
  scale_y_continuous(expand = expansion(mult = c(0, 0.1)))

# 2. 简化饼图替代华夫饼图
algo_count <- algorithm_data %>%
  count(best_algorithm, sort = TRUE) %>%
  mutate(percentage = round(n / sum(n) * 100, 1))

p2 <- ggplot(algo_count, aes(x = "", y = n, fill = best_algorithm)) +
  geom_bar(stat = "identity", width = 1) +
  coord_polar("y", start = 0) +
  geom_text(aes(label = paste0(best_algorithm, "\n", n, "个任务\n(", percentage, "%)")),
            position = position_stack(vjust = 0.5), size = 3, fontface = "bold") +
  labs(title = "算法选择分布饼图",
       subtitle = "展示各算法作为最佳选择的频次分布",
       fill = "算法类型") +
  theme_void() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    legend.position = "bottom"
  ) +
  scale_fill_viridis_d()

# 3. 高级坡度图 - Case0 vs Case1 性能对比
slope_data <- algorithm_data %>%
  select(task_type, case, fitness_score, execution_time, memory_peak) %>%
  pivot_longer(cols = c(fitness_score, execution_time, memory_peak),
               names_to = "metric", values_to = "value") %>%
  group_by(task_type, case, metric) %>%
  summarise(avg_value = mean(value), .groups = 'drop') %>%
  pivot_wider(names_from = case, values_from = avg_value) %>%
  mutate(
    change = Case1 - Case0,
    change_pct = (Case1 - Case0) / Case0 * 100,
    metric_label = case_when(
      metric == "fitness_score" ~ "适应度得分",
      metric == "execution_time" ~ "执行时间",
      metric == "memory_peak" ~ "内存峰值"
    )
  ) %>%
  pivot_longer(cols = c(Case0, Case1), names_to = "case", values_to = "value")

p3 <- ggplot(slope_data, aes(x = case, y = value, group = interaction(task_type, metric_label))) +
  geom_line(aes(color = task_type), size = 1.2, alpha = 0.8) +
  geom_point(aes(color = task_type, shape = metric_label), size = 4) +
  facet_wrap(~metric_label, scales = "free_y", ncol = 1) +
  labs(title = "Case0 vs Case1 性能变化坡度图",
       subtitle = "展示不同任务类型在两种案例下的性能变化趋势",
       x = "案例类型",
       y = "指标值",
       color = "任务类型",
       shape = "性能指标") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    strip.text = element_text(size = 12, face = "bold"),
    legend.position = "bottom"
  ) +
  scale_color_viridis_d() +
  scale_y_continuous(labels = scales::comma)

# 4. 简化排名图替代凹凸图
ranking_data <- algorithm_data %>%
  group_by(best_algorithm) %>%
  summarise(
    avg_fitness = mean(fitness_score),
    avg_exec_time = mean(execution_time),
    avg_memory = mean(memory_peak),
    count = n(),
    .groups = 'drop'
  ) %>%
  arrange(desc(avg_fitness)) %>%
  mutate(
    rank_fitness = row_number(),
    rank_exec = rank(avg_exec_time),
    rank_memory = rank(avg_memory)
  ) %>%
  select(best_algorithm, rank_fitness, rank_exec, rank_memory) %>%
  pivot_longer(cols = starts_with("rank"), names_to = "metric", values_to = "rank") %>%
  mutate(metric = case_when(
    metric == "rank_fitness" ~ "适应度排名",
    metric == "rank_exec" ~ "执行时间排名",
    metric == "rank_memory" ~ "内存使用排名"
  ))

p4 <- ggplot(ranking_data, aes(x = metric, y = rank, color = best_algorithm, group = best_algorithm)) +
  geom_line(size = 1.5, alpha = 0.8) +
  geom_point(size = 4, alpha = 0.9) +
  labs(title = "算法多维排名对比图",
       subtitle = "展示算法在不同性能维度上的排名变化",
       x = "排名维度",
       y = "排名 (1为最佳)",
       color = "算法类型") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "bottom"
  ) +
  scale_color_viridis_d() +
  scale_y_reverse()

# 5. 高级组合仪表盘
# 创建四个小图表组合
mini_p1 <- algorithm_data %>%
  ggplot(aes(x = best_algorithm, fill = best_algorithm)) +
  geom_bar() +
  coord_polar() +
  theme_void() +
  theme(legend.position = "none") +
  scale_fill_viridis_d() +
  labs(title = "算法分布")

mini_p2 <- algorithm_data %>%
  ggplot(aes(x = task_type, y = fitness_score, fill = task_type)) +
  geom_boxplot() +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        legend.position = "none") +
  scale_fill_viridis_d() +
  labs(title = "任务类型适应度", x = "", y = "")

mini_p3 <- algorithm_data %>%
  ggplot(aes(x = execution_time, y = memory_peak, color = fitness_score)) +
  geom_point(size = 3, alpha = 0.8) +
  theme_minimal() +
  theme(legend.position = "none") +
  scale_color_viridis_c() +
  scale_x_log10() +
  labs(title = "执行时间 vs 内存", x = "", y = "")

mini_p4 <- algorithm_data %>%
  group_by(task_type) %>%
  summarise(count = n(), .groups = 'drop') %>%
  ggplot(aes(x = "", y = count, fill = task_type)) +
  geom_bar(stat = "identity") +
  coord_polar("y") +
  theme_void() +
  theme(legend.position = "none") +
  scale_fill_viridis_d() +
  labs(title = "任务类型分布")

# 组合仪表盘使用grid.arrange
p5 <- grid.arrange(mini_p1, mini_p2, mini_p3, mini_p4, ncol = 2, nrow = 2,
                   top = textGrob("算法优化综合仪表盘\n多维度性能指标概览",
                                 gp = gpar(fontsize = 16, fontface = "bold")))

# 保存图表
ggsave("t3/flow_diagram.png", p1, width = 14, height = 8, dpi = 300)
ggsave("t3/pie_chart.png", p2, width = 12, height = 6, dpi = 300)
ggsave("t3/slope_chart.png", p3, width = 10, height = 12, dpi = 300)
ggsave("t3/ranking_chart.png", p4, width = 12, height = 8, dpi = 300)
ggsave("t3/dashboard.png", p5, width = 16, height = 12, dpi = 300)

# 输出信息
cat("=== T3: 高级分布与流程分析图表已生成 ===\n")
cat("- flow_diagram.png: 任务类型与算法选择流程图\n")
cat("- pie_chart.png: 算法选择分布饼图\n")
cat("- slope_chart.png: Case0 vs Case1 性能变化坡度图\n")
cat("- ranking_chart.png: 算法多维排名对比图\n")
cat("- dashboard.png: 算法优化综合仪表盘\n")