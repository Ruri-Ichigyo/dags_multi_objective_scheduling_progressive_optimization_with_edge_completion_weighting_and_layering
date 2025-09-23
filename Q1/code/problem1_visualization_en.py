#!/usr/bin/env python3
"""
Problem 1 Visualization Analysis Script (English Version)
"""
import matplotlib.pyplot as plt
import numpy as np
from problem1_analysis import *

def visualize_memory_patterns(case_name: str, save_plots: bool = True):
    """Visualize memory usage patterns for a single case"""
    json_file = JSON_DIR / f"{case_name}.json"
    sched_file = SCHED_DIR / f"{case_name}_schedule.txt"

    if not json_file.exists() or not sched_file.exists():
        print(f"File not found: {case_name}")
        return

    # Load data
    G, nodes_map = load_graph(json_file)
    optimized_order = parse_schedule_txt(sched_file)
    baseline_order = baseline_topological_order(G)

    # Analyze memory usage
    baseline_stats = analyze_memory_usage(baseline_order, nodes_map)
    optimized_stats = analyze_memory_usage(optimized_order, nodes_map)

    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{case_name} Memory Usage Optimization Comparison', fontsize=16, fontweight='bold')

    # Baseline L1 memory usage
    steps_baseline = range(len(baseline_stats['l1_history']))
    ax1.plot(steps_baseline, baseline_stats['l1_history'], 'b-', linewidth=1, alpha=0.7, label='L1')
    ax1.axhline(y=baseline_stats['peak_l1'], color='r', linestyle='--', alpha=0.8, label=f'L1 Peak: {baseline_stats["peak_l1"]:,}')
    ax1.set_title('Baseline Approach - L1 Memory Usage')
    ax1.set_xlabel('Execution Steps')
    ax1.set_ylabel('Memory Usage')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Optimized L1 memory usage
    steps_optimized = range(len(optimized_stats['l1_history']))
    ax2.plot(steps_optimized, optimized_stats['l1_history'], 'g-', linewidth=1, alpha=0.7, label='L1')
    ax2.axhline(y=optimized_stats['peak_l1'], color='r', linestyle='--', alpha=0.8, label=f'L1 Peak: {optimized_stats["peak_l1"]:,}')
    ax2.set_title('Optimized Approach - L1 Memory Usage')
    ax2.set_xlabel('Execution Steps')
    ax2.set_ylabel('Memory Usage')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # UB memory comparison (if any)
    if baseline_stats['peak_ub'] > 0 or optimized_stats['peak_ub'] > 0:
        ax3.plot(steps_baseline, baseline_stats['ub_history'], 'b-', linewidth=1, alpha=0.7, label='Baseline UB')
        ax3.plot(steps_optimized, optimized_stats['ub_history'], 'g-', linewidth=1, alpha=0.7, label='Optimized UB')
        ax3.axhline(y=baseline_stats['peak_ub'], color='b', linestyle='--', alpha=0.5)
        ax3.axhline(y=optimized_stats['peak_ub'], color='g', linestyle='--', alpha=0.5)
        ax3.set_title('UB Memory Usage Comparison')
        ax3.legend()
    else:
        ax3.text(0.5, 0.5, 'UB Memory Not Used', transform=ax3.transAxes, ha='center', va='center', fontsize=12)
        ax3.set_title('UB Memory Usage')
    ax3.set_xlabel('Execution Steps')
    ax3.set_ylabel('Memory Usage')
    ax3.grid(True, alpha=0.3)

    # Memory reduction visualization
    categories = ['L1', 'UB', 'Total']
    baseline_vals = [baseline_stats['peak_l1'], baseline_stats['peak_ub'], baseline_stats['peak_total']]
    optimized_vals = [optimized_stats['peak_l1'], optimized_stats['peak_ub'], optimized_stats['peak_total']]

    x = np.arange(len(categories))
    width = 0.35

    bars1 = ax4.bar(x - width/2, baseline_vals, width, label='Baseline', alpha=0.8)
    bars2 = ax4.bar(x + width/2, optimized_vals, width, label='Optimized', alpha=0.8)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height):,}', ha='center', va='bottom', fontsize=9)

    ax4.set_title('Peak Memory Comparison')
    ax4.set_xlabel('Memory Type')
    ax4.set_ylabel('Peak Usage')
    ax4.set_xticks(x)
    ax4.set_xticklabels(categories)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    if save_plots:
        output_file = ROOT / f"{case_name}_memory_analysis_en.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Chart saved to: {output_file}")

    plt.show()


def create_overall_comparison():
    """Create overall comparison chart for all cases"""
    cases = ['Conv_Case0', 'Conv_Case1', 'FlashAttention_Case0', 'FlashAttention_Case1', 'Matmul_Case0', 'Matmul_Case1']

    results = []
    for case in cases:
        analysis = analyze_case(case)
        if analysis:
            results.append(analysis)

    if not results:
        return

    # Prepare data
    case_names = [r['case_name'] for r in results]
    baseline_l1 = [r['baseline']['peak_l1'] for r in results]
    optimized_l1 = [r['optimized']['peak_l1'] for r in results]
    l1_improvements = [r['improvements']['l1_pct'] for r in results]

    # Create comparison charts
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle('Problem 1 Optimization Results - All Cases Comparison', fontsize=16, fontweight='bold')

    # L1 peak memory comparison
    x = np.arange(len(case_names))
    width = 0.35

    bars1 = ax1.bar(x - width/2, baseline_l1, width, label='Baseline', alpha=0.8, color='lightcoral')
    bars2 = ax1.bar(x + width/2, optimized_l1, width, label='Optimized', alpha=0.8, color='lightgreen')

    ax1.set_title('L1 Peak Memory Comparison')
    ax1.set_xlabel('Test Cases')
    ax1.set_ylabel('Peak Memory')
    ax1.set_xticks(x)
    ax1.set_xticklabels([name.replace('_', '\n') for name in case_names], fontsize=9)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # Add improvement percentage labels
    for i, improvement in enumerate(l1_improvements):
        if improvement > 0:
            ax1.text(i, max(baseline_l1[i], optimized_l1[i]) + max(baseline_l1) * 0.05,
                    f'-{improvement:.1f}%', ha='center', va='bottom', fontweight='bold', color='red')

    # Memory reduction percentage
    bars3 = ax2.bar(case_names, l1_improvements, alpha=0.8, color='steelblue')
    ax2.set_title('L1 Memory Reduction Percentage')
    ax2.set_xlabel('Test Cases')
    ax2.set_ylabel('Reduction Percentage (%)')
    ax2.set_xticklabels([name.replace('_', '\n') for name in case_names], fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, val in zip(bars3, l1_improvements):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()

    output_file = ROOT / "problem1_overall_comparison_en.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Overall comparison chart saved to: {output_file}")
    plt.show()


if __name__ == "__main__":
    # Visualize representative cases
    cases = ['Conv_Case0', 'FlashAttention_Case0', 'Matmul_Case0']

    for case in cases:
        print(f"\nGenerating visualization analysis for {case}...")
        visualize_memory_patterns(case)

    # Generate overall comparison chart
    print("\nGenerating overall comparison chart...")
    create_overall_comparison()