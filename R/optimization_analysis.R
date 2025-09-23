library(jsonlite)
library(ggplot2)
library(dplyr)
library(tidyr)
library(gridExtra)
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

# 1. 执行时间对比图
p1 <- ggplot(algorithm_data, aes(x = task_name, y = execution_time, fill = best_algorithm)) +
  geom_bar(stat = "identity", alpha = 0.8) +
  geom_text(aes(label = scales::comma(execution_time)), vjust = -0.5, size = 3) +
  labs(title = "算法执行时间对比",
       subtitle = "不同任务的最佳算法执行时间",
       x = "任务名称",
       y = "执行时间 (微秒)",
       fill = "最佳算法") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        plot.title = element_text(size = 14, face = "bold"),
        legend.position = "bottom") +
  scale_fill_viridis_d() +
  scale_y_continuous(labels = scales::comma)

# 2. 内存峰值对比图
p2 <- ggplot(algorithm_data, aes(x = task_name, y = memory_peak, fill = best_algorithm)) +
  geom_bar(stat = "identity", alpha = 0.8) +
  geom_text(aes(label = scales::comma(memory_peak)), vjust = -0.5, size = 3) +
  labs(title = "内存峰值使用对比",
       subtitle = "不同任务的内存峰值使用情况",
       x = "任务名称",
       y = "内存峰值 (KB)",
       fill = "最佳算法") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        plot.title = element_text(size = 14, face = "bold"),
        legend.position = "bottom") +
  scale_fill_viridis_d() +
  scale_y_continuous(labels = scales::comma)

# 3. Spill Cost对比图
p3 <- ggplot(algorithm_data, aes(x = task_name, y = spill_cost, fill = best_algorithm)) +
  geom_bar(stat = "identity", alpha = 0.8) +
  geom_text(aes(label = scales::comma(spill_cost)), vjust = -0.5, size = 3) +
  labs(title = "Spill Cost 对比",
       subtitle = "不同任务的Spill Cost",
       x = "任务名称",
       y = "Spill Cost",
       fill = "最佳算法") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        plot.title = element_text(size = 14, face = "bold"),
        legend.position = "bottom") +
  scale_fill_viridis_d() +
  scale_y_continuous(labels = scales::comma)

# 4. Fitness Score对比图
p4 <- ggplot(algorithm_data, aes(x = task_name, y = fitness_score, fill = best_algorithm)) +
  geom_bar(stat = "identity", alpha = 0.8) +
  geom_text(aes(label = sprintf("%.4f", fitness_score)), vjust = -0.5, size = 3) +
  labs(title = "适应度得分对比",
       subtitle = "不同任务的适应度得分 (越高越好)",
       x = "任务名称",
       y = "适应度得分",
       fill = "最佳算法") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        plot.title = element_text(size = 14, face = "bold"),
        legend.position = "bottom") +
  scale_fill_viridis_d()

# 5. 综合性能雷达图数据准备
algorithm_data_norm <- algorithm_data %>%
  mutate(
    exec_time_norm = 1 - (execution_time - min(execution_time)) / (max(execution_time) - min(execution_time)),
    memory_norm = 1 - (memory_peak - min(memory_peak)) / (max(memory_peak) - min(memory_peak)),
    spill_norm = 1 - (spill_cost - min(spill_cost)) / (max(spill_cost) - min(spill_cost)),
    fitness_norm = fitness_score / max(fitness_score)
  )

# 转换为长格式用于雷达图
radar_data <- algorithm_data_norm %>%
  select(task_name, best_algorithm, exec_time_norm, memory_norm, spill_norm, fitness_norm) %>%
  pivot_longer(cols = c(exec_time_norm, memory_norm, spill_norm, fitness_norm),
               names_to = "metric", values_to = "value") %>%
  mutate(metric = case_when(
    metric == "exec_time_norm" ~ "执行时间(标准化)",
    metric == "memory_norm" ~ "内存使用(标准化)",
    metric == "spill_norm" ~ "Spill成本(标准化)",
    metric == "fitness_norm" ~ "适应度得分(标准化)"
  ))

# 6. 综合性能对比图
p5 <- ggplot(radar_data, aes(x = metric, y = value, fill = task_name)) +
  geom_bar(stat = "identity", position = "dodge", alpha = 0.8) +
  labs(title = "综合性能对比 (标准化指标)",
       subtitle = "所有指标标准化后的性能对比",
       x = "性能指标",
       y = "标准化得分 (0-1)",
       fill = "任务") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        plot.title = element_text(size = 14, face = "bold"),
        legend.position = "bottom") +
  scale_fill_viridis_d()

# 7. 算法类型分布图
algo_count <- algorithm_data %>%
  count(best_algorithm) %>%
  mutate(percentage = n / sum(n) * 100)

p6 <- ggplot(algo_count, aes(x = "", y = n, fill = best_algorithm)) +
  geom_bar(stat = "identity", width = 1) +
  coord_polar("y", start = 0) +
  geom_text(aes(label = paste0(best_algorithm, "\n", n, "个任务\n(",
                              round(percentage, 1), "%)")),
            position = position_stack(vjust = 0.5)) +
  labs(title = "最佳算法分布",
       subtitle = "不同算法作为最佳算法的次数分布",
       fill = "算法类型") +
  theme_void() +
  theme(plot.title = element_text(size = 14, face = "bold"),
        legend.position = "right") +
  scale_fill_viridis_d()

# 保存图表
ggsave(file.path(base_path, "R", "execution_time_comparison.png"), p1,
       width = 12, height = 8, dpi = 300)
ggsave(file.path(base_path, "R", "memory_peak_comparison.png"), p2,
       width = 12, height = 8, dpi = 300)
ggsave(file.path(base_path, "R", "spill_cost_comparison.png"), p3,
       width = 12, height = 8, dpi = 300)
ggsave(file.path(base_path, "R", "fitness_score_comparison.png"), p4,
       width = 12, height = 8, dpi = 300)
ggsave(file.path(base_path, "R", "comprehensive_performance.png"), p5,
       width = 12, height = 8, dpi = 300)
ggsave(file.path(base_path, "R", "algorithm_distribution.png"), p6,
       width = 10, height = 8, dpi = 300)

# 创建组合图
combined_plot <- grid.arrange(p1, p2, p3, p4, ncol = 2, nrow = 2)
ggsave(file.path(base_path, "R", "combined_performance_analysis.png"), combined_plot,
       width = 20, height = 16, dpi = 300)

# 输出数据摘要
cat("=== 优化算法性能分析摘要 ===\n")
print(algorithm_data)

cat("\n=== 最佳算法统计 ===\n")
print(algo_count)

cat("\n=== 性能指标统计 ===\n")
summary_stats <- algorithm_data %>%
  summarise(
    avg_exec_time = mean(execution_time),
    avg_memory = mean(memory_peak),
    avg_spill_cost = mean(spill_cost),
    avg_fitness = mean(fitness_score)
  )
print(summary_stats)

cat("\n图表已保存到 R 目录下:\n")
cat("- execution_time_comparison.png: 执行时间对比\n")
cat("- memory_peak_comparison.png: 内存峰值对比\n")
cat("- spill_cost_comparison.png: Spill成本对比\n")
cat("- fitness_score_comparison.png: 适应度得分对比\n")
cat("- comprehensive_performance.png: 综合性能对比\n")
cat("- algorithm_distribution.png: 算法分布饼图\n")
cat("- combined_performance_analysis.png: 综合分析图\n")