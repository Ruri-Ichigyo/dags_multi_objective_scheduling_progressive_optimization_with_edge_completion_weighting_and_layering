library(jsonlite)
library(ggplot2)
library(dplyr)
library(tidyr)
library(plotly)
library(ggridges)
library(viridis)
library(scales)
library(corrplot)
library(GGally)

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

# 1. 高级小提琴图 - 执行时间分布
p1 <- ggplot(algorithm_data, aes(x = task_type, y = execution_time, fill = task_type)) +
  geom_violin(alpha = 0.7, trim = FALSE) +
  geom_boxplot(width = 0.1, alpha = 0.8, outlier.shape = NA) +
  geom_jitter(width = 0.2, alpha = 0.6, size = 2) +
  labs(title = "算法执行时间分布 - 小提琴图",
       subtitle = "展示不同任务类型执行时间的分布特征",
       x = "任务类型",
       y = "执行时间 (微秒)",
       caption = "数据来源: 优化算法性能分析") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "none",
    panel.grid.minor = element_blank()
  ) +
  scale_fill_viridis_d() +
  scale_y_continuous(labels = scales::comma, trans = "log10")

# 2. 高级热力图 - 性能指标相关性
performance_matrix <- algorithm_data %>%
  select(execution_time, spill_cost, fitness_score, memory_peak) %>%
  cor()

# 创建热力图数据
heatmap_data <- reshape2::melt(performance_matrix)

p2 <- ggplot(heatmap_data, aes(Var1, Var2, fill = value)) +
  geom_tile() +
  geom_text(aes(label = round(value, 3)), color = "white", size = 4, fontface = "bold") +
  labs(title = "性能指标相关性热力图",
       subtitle = "展示不同性能指标之间的相关性",
       x = "性能指标",
       y = "性能指标",
       fill = "相关系数") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    axis.text.x = element_text(angle = 45, hjust = 1),
    panel.grid = element_blank()
  ) +
  scale_fill_gradient2(low = "blue", high = "red", mid = "white", midpoint = 0,
                      limit = c(-1, 1), space = "Lab", name = "相关系数")

# 3. 高级散点图替代散点矩阵图
p3 <- ggplot(algorithm_data, aes(x = execution_time, y = memory_peak)) +
  geom_point(aes(color = best_algorithm, size = fitness_score), alpha = 0.7) +
  geom_smooth(method = "lm", se = TRUE, alpha = 0.3) +
  facet_wrap(~task_type, scales = "free") +
  labs(title = "性能指标关系散点图",
       subtitle = "执行时间 vs 内存峰值 (按任务类型分面)",
       x = "执行时间 (微秒)",
       y = "内存峰值 (KB)",
       color = "最佳算法",
       size = "适应度得分") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    strip.text = element_text(size = 10, face = "bold")
  ) +
  scale_color_viridis_d() +
  scale_x_continuous(labels = scales::comma, trans = "log10") +
  scale_y_continuous(labels = scales::comma)

# 4. 高级气泡图 - 多维性能展示
p4 <- ggplot(algorithm_data, aes(x = execution_time, y = memory_peak,
                                size = spill_cost, color = fitness_score)) +
  geom_point(alpha = 0.8) +
  geom_text(aes(label = task_name), vjust = -1.5, size = 3, check_overlap = TRUE) +
  labs(title = "多维性能气泡图",
       subtitle = "执行时间 vs 内存峰值 (气泡大小=Spill成本, 颜色=适应度得分)",
       x = "执行时间 (微秒)",
       y = "内存峰值 (KB)",
       size = "Spill成本",
       color = "适应度得分",
       caption = "气泡越大表示Spill成本越高，颜色越深表示适应度得分越高") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    legend.position = "bottom"
  ) +
  scale_x_continuous(labels = scales::comma, trans = "log10") +
  scale_y_continuous(labels = scales::comma) +
  scale_color_viridis_c(option = "plasma") +
  scale_size_continuous(range = c(3, 15), guide = guide_legend(override.aes = list(alpha = 0.8)))

# 5. 高级脊线图 - 性能指标分布
performance_long <- algorithm_data %>%
  select(task_type, execution_time, memory_peak, spill_cost) %>%
  pivot_longer(cols = c(execution_time, memory_peak, spill_cost),
               names_to = "metric", values_to = "value") %>%
  mutate(
    metric_label = case_when(
      metric == "execution_time" ~ "执行时间",
      metric == "memory_peak" ~ "内存峰值",
      metric == "spill_cost" ~ "Spill成本"
    ),
    log_value = log10(value + 1)
  )

p5 <- ggplot(performance_long, aes(x = log_value, y = metric_label, fill = task_type)) +
  geom_density_ridges(alpha = 0.7, scale = 2) +
  labs(title = "性能指标分布脊线图",
       subtitle = "不同任务类型在各性能指标上的分布对比 (对数尺度)",
       x = "指标值 (对数尺度)",
       y = "性能指标",
       fill = "任务类型") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    legend.position = "bottom"
  ) +
  scale_fill_viridis_d()

# 保存高级图表
ggsave("t1/violin_execution_time.png", p1, width = 12, height = 8, dpi = 300)
ggsave("t1/correlation_heatmap.png", p2, width = 10, height = 8, dpi = 300)
ggsave("t1/scatter_plot.png", p3, width = 14, height = 14, dpi = 300)
ggsave("t1/bubble_chart.png", p4, width = 14, height = 10, dpi = 300)
ggsave("t1/ridge_plot.png", p5, width = 12, height = 8, dpi = 300)

# 输出信息
cat("=== T1: 高级性能分析图表已生成 ===\n")
cat("- violin_execution_time.png: 执行时间分布小提琴图\n")
cat("- correlation_heatmap.png: 性能指标相关性热力图\n")
cat("- scatter_plot.png: 性能指标关系散点图\n")
cat("- bubble_chart.png: 多维性能气泡图\n")
cat("- ridge_plot.png: 性能指标分布脊线图\n")