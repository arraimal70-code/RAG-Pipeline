#!/usr/bin/env python3
"""
Statistical analysis tools for RAG Pipeline experiments.

Provides:
- Confidence intervals
- Significance testing
- Effect size calculations
- Bootstrap resampling
- Comparative analysis
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats
import json
from pathlib import Path


class StatisticalAnalyzer:
    """Statistical analysis for experimental results."""
    
    def __init__(self):
        self.results = {}
    
    def calculate_confidence_interval(
        self, 
        data: List[float], 
        confidence: float = 0.95
    ) -> Tuple[float, float, float]:
        """
        Calculate confidence interval for mean.
        
        Returns:
            (mean, lower_bound, upper_bound)
        """
        n = len(data)
        mean = np.mean(data)
        se = stats.sem(data)  # Standard error of mean
        
        # t-distribution for small samples, normal for large
        if n < 30:
            h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
        else:
            h = se * stats.norm.ppf((1 + confidence) / 2)
        
        return mean, mean - h, mean + h
    
    def bootstrap_confidence_interval(
        self,
        data: List[float],
        num_samples: int = 10000,
        confidence: float = 0.95
    ) -> Tuple[float, float, float]:
        """
        Calculate bootstrap confidence interval.
        
        Returns:
            (mean, lower_bound, upper_bound)
        """
        bootstrap_means = []
        
        for _ in range(num_samples):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_means.append(np.mean(sample))
        
        mean = np.mean(bootstrap_means)
        lower = np.percentile(bootstrap_means, (1 - confidence) / 2 * 100)
        upper = np.percentile(bootstrap_means, (1 + confidence) / 2 * 100)
        
        return mean, lower, upper
    
    def paired_t_test(
        self,
        baseline: List[float],
        treatment: List[float]
    ) -> Dict[str, float]:
        """
        Perform paired t-test between baseline and treatment.
        
        Returns:
            Dictionary with t-statistic, p-value, and effect size
        """
        t_stat, p_value = stats.ttest_rel(baseline, treatment)
        
        # Cohen's d for effect size
        diff = np.array(treatment) - np.array(baseline)
        pooled_std = np.sqrt((np.std(baseline)**2 + np.std(treatment)**2) / 2)
        cohens_d = np.mean(diff) / pooled_std if pooled_std > 0 else 0
        
        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'cohens_d': cohens_d,
            'significant': p_value < 0.05,
            'effect_size_interpretation': self._interpret_effect_size(cohens_d)
        }
    
    def independent_t_test(
        self,
        group1: List[float],
        group2: List[float]
    ) -> Dict[str, float]:
        """
        Perform independent t-test between two groups.
        
        Returns:
            Dictionary with t-statistic, p-value, and effect size
        """
        t_stat, p_value = stats.ttest_ind(group1, group2)
        
        # Cohen's d
        pooled_std = np.sqrt((np.std(group1)**2 + np.std(group2)**2) / 2)
        cohens_d = (np.mean(group1) - np.mean(group2)) / pooled_std if pooled_std > 0 else 0
        
        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'cohens_d': cohens_d,
            'significant': p_value < 0.05,
            'effect_size_interpretation': self._interpret_effect_size(cohens_d)
        }
    
    def wilcoxon_test(
        self,
        baseline: List[float],
        treatment: List[float]
    ) -> Dict[str, float]:
        """
        Perform Wilcoxon signed-rank test (non-parametric alternative to paired t-test).
        
        Returns:
            Dictionary with test statistic and p-value
        """
        stat, p_value = stats.wilcoxon(baseline, treatment)
        
        return {
            'test_statistic': stat,
            'p_value': p_value,
            'significant': p_value < 0.05
        }
    
    def mann_whitney_test(
        self,
        group1: List[float],
        group2: List[float]
    ) -> Dict[str, float]:
        """
        Perform Mann-Whitney U test (non-parametric alternative to independent t-test).
        
        Returns:
            Dictionary with test statistic and p-value
        """
        stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        
        return {
            'test_statistic': stat,
            'p_value': p_value,
            'significant': p_value < 0.05
        }
    
    def calculate_effect_size(
        self,
        baseline: List[float],
        treatment: List[float],
        method: str = 'cohens_d'
    ) -> Dict[str, float]:
        """
        Calculate effect size between baseline and treatment.
        
        Methods:
        - cohens_d: Cohen's d (standardized mean difference)
        - hedges_g: Hedges' g (corrected Cohen's d for small samples)
        - glass_delta: Glass's delta (uses control group SD)
        
        Returns:
            Dictionary with effect size and interpretation
        """
        mean_diff = np.mean(treatment) - np.mean(baseline)
        
        if method == 'cohens_d':
            pooled_std = np.sqrt((np.std(baseline)**2 + np.std(treatment)**2) / 2)
            effect_size = mean_diff / pooled_std if pooled_std > 0 else 0
            
        elif method == 'hedges_g':
            pooled_std = np.sqrt((np.std(baseline)**2 + np.std(treatment)**2) / 2)
            cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0
            
            # Correction factor
            n1, n2 = len(baseline), len(treatment)
            correction = 1 - (3 / (4 * (n1 + n2) - 9))
            effect_size = cohens_d * correction
            
        elif method == 'glass_delta':
            std_control = np.std(baseline)
            effect_size = mean_diff / std_control if std_control > 0 else 0
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return {
            'effect_size': effect_size,
            'method': method,
            'interpretation': self._interpret_effect_size(effect_size)
        }
    
    def _interpret_effect_size(self, effect_size: float) -> str:
        """Interpret effect size magnitude."""
        abs_effect = abs(effect_size)
        
        if abs_effect < 0.2:
            return "negligible"
        elif abs_effect < 0.5:
            return "small"
        elif abs_effect < 0.8:
            return "medium"
        else:
            return "large"
    
    def compare_configurations(
        self,
        baseline_results: Dict[str, List[float]],
        treatment_results: Dict[str, List[float]],
        metric_name: str
    ) -> Dict[str, Any]:
        """
        Compare two configurations across a metric.
        
        Args:
            baseline_results: Dictionary with 'scores' list
            treatment_results: Dictionary with 'scores' list
            metric_name: Name of the metric being compared
        
        Returns:
            Comprehensive comparison report
        """
        baseline_scores = baseline_results['scores']
        treatment_scores = treatment_results['scores']
        
        # Basic statistics
        baseline_mean, baseline_lower, baseline_upper = self.calculate_confidence_interval(baseline_scores)
        treatment_mean, treatment_lower, treatment_upper = self.calculate_confidence_interval(treatment_scores)
        
        # Statistical tests
        paired_test = self.paired_t_test(baseline_scores, treatment_scores)
        effect_size = self.calculate_effect_size(baseline_scores, treatment_scores)
        
        # Bootstrap for robustness
        bootstrap_mean, bootstrap_lower, bootstrap_upper = self.bootstrap_confidence_interval(
            treatment_scores
        )
        
        # Calculate improvement
        improvement = treatment_mean - baseline_mean
        percent_improvement = (improvement / baseline_mean * 100) if baseline_mean != 0 else 0
        
        return {
            'metric': metric_name,
            'baseline': {
                'mean': baseline_mean,
                'ci_lower': baseline_lower,
                'ci_upper': baseline_upper,
                'std': np.std(baseline_scores),
                'n': len(baseline_scores)
            },
            'treatment': {
                'mean': treatment_mean,
                'ci_lower': treatment_lower,
                'ci_upper': treatment_upper,
                'bootstrap_ci_lower': bootstrap_lower,
                'bootstrap_ci_upper': bootstrap_upper,
                'std': np.std(treatment_scores),
                'n': len(treatment_scores)
            },
            'comparison': {
                'absolute_improvement': improvement,
                'percent_improvement': percent_improvement,
                'paired_t_test': paired_test,
                'effect_size': effect_size
            },
            'conclusion': self._generate_conclusion(
                improvement, paired_test['p_value'], effect_size['effect_size']
            )
        }
    
    def _generate_conclusion(
        self,
        improvement: float,
        p_value: float,
        effect_size: float
    ) -> str:
        """Generate human-readable conclusion."""
        significant = p_value < 0.05
        effect_interpretation = self._interpret_effect_size(effect_size)
        
        if significant and improvement > 0:
            return f"Statistically significant improvement ({effect_interpretation} effect size, p={p_value:.4f})"
        elif significant and improvement < 0:
            return f"Statistically significant degradation ({effect_interpretation} effect size, p={p_value:.4f})"
        elif not significant:
            return f"No statistically significant difference (p={p_value:.4f})"
        else:
            return "Inconclusive results"
    
    def analyze_experiment_results(
        self,
        experiment_file: Path
    ) -> Dict[str, Any]:
        """
        Analyze results from an experiment file.
        
        Returns:
            Comprehensive statistical analysis
        """
        with open(experiment_file, 'r') as f:
            results = json.load(f)
        
        analysis = {
            'experiment_id': results.get('experiment_id'),
            'timestamp': results.get('timestamp'),
            'metrics': {}
        }
        
        # Analyze each metric
        for metric_name, metric_data in results.get('metrics', {}).items():
            if isinstance(metric_data, dict) and 'scores' in metric_data:
                scores = metric_data['scores']
                
                # Basic statistics
                mean, lower, upper = self.calculate_confidence_interval(scores)
                bootstrap_mean, bootstrap_lower, bootstrap_upper = self.bootstrap_confidence_interval(scores)
                
                analysis['metrics'][metric_name] = {
                    'mean': mean,
                    'std': np.std(scores),
                    'ci_95_lower': lower,
                    'ci_95_upper': upper,
                    'bootstrap_ci_95_lower': bootstrap_lower,
                    'bootstrap_ci_95_upper': bootstrap_upper,
                    'median': np.median(scores),
                    'min': np.min(scores),
                    'max': np.max(scores),
                    'n': len(scores)
                }
        
        return analysis
    
    def generate_comparison_report(
        self,
        comparisons: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a formatted comparison report.
        
        Args:
            comparisons: List of comparison results from compare_configurations
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("STATISTICAL COMPARISON REPORT")
        report.append("=" * 80)
        report.append("")
        
        for comp in comparisons:
            report.append(f"Metric: {comp['metric']}")
            report.append("-" * 80)
            
            # Baseline
            report.append(f"Baseline:")
            report.append(f"  Mean: {comp['baseline']['mean']:.4f}")
            report.append(f"  95% CI: [{comp['baseline']['ci_lower']:.4f}, {comp['baseline']['ci_upper']:.4f}]")
            report.append(f"  Std: {comp['baseline']['std']:.4f}")
            report.append(f"  N: {comp['baseline']['n']}")
            report.append("")
            
            # Treatment
            report.append(f"Treatment:")
            report.append(f"  Mean: {comp['treatment']['mean']:.4f}")
            report.append(f"  95% CI: [{comp['treatment']['ci_lower']:.4f}, {comp['treatment']['ci_upper']:.4f}]")
            report.append(f"  Bootstrap 95% CI: [{comp['treatment']['bootstrap_ci_lower']:.4f}, {comp['treatment']['bootstrap_ci_upper']:.4f}]")
            report.append(f"  Std: {comp['treatment']['std']:.4f}")
            report.append(f"  N: {comp['treatment']['n']}")
            report.append("")
            
            # Comparison
            report.append(f"Comparison:")
            report.append(f"  Absolute improvement: {comp['comparison']['absolute_improvement']:.4f}")
            report.append(f"  Percent improvement: {comp['comparison']['percent_improvement']:.2f}%")
            report.append(f"  p-value: {comp['comparison']['paired_t_test']['p_value']:.4f}")
            report.append(f"  Significant: {comp['comparison']['paired_t_test']['significant']}")
            report.append(f"  Effect size (Cohen's d): {comp['comparison']['effect_size']['effect_size']:.4f}")
            report.append(f"  Effect interpretation: {comp['comparison']['effect_size']['interpretation']}")
            report.append("")
            report.append(f"Conclusion: {comp['conclusion']}")
            report.append("")
            report.append("=" * 80)
            report.append("")
        
        return "\n".join(report)


def main():
    """Example usage of statistical analysis."""
    analyzer = StatisticalAnalyzer()
    
    # Example: Compare baseline vs treatment
    baseline_scores = [0.72, 0.75, 0.71, 0.74, 0.73, 0.76, 0.72, 0.75, 0.74, 0.73]
    treatment_scores = [0.78, 0.81, 0.79, 0.82, 0.80, 0.83, 0.79, 0.81, 0.80, 0.82]
    
    comparison = analyzer.compare_configurations(
        {'scores': baseline_scores},
        {'scores': treatment_scores},
        'Recall@5'
    )
    
    print(analyzer.generate_comparison_report([comparison]))


if __name__ == "__main__":
    main()
