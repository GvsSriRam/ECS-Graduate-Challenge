import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from datetime import datetime

@dataclass
class FairnessMetrics:
    """Comprehensive fairness metrics"""
    demographic_parity_difference: float
    demographic_parity_ratio: float
    equalized_odds_difference: Dict[str, float]
    false_positive_rate: Dict[str, float]
    false_negative_rate: Dict[str, float]
    bias_score: float
    selection_rate: Dict[str, Dict[str, float]]

@dataclass
class BiasMetrics:
    """Bias detection metrics"""
    systematic_bias: Dict[str, float]
    coverage_bias: float
    scoring_bias: Dict[str, float]
    distribution_bias: float

class CompleteFairRankingSystem:
    def __init__(
        self,
        scores_df: pd.DataFrame,
        protected_attributes: Optional[pd.DataFrame] = None,
        min_reviews: int = 2,
        selection_threshold: float = 0.25,
        fairness_threshold: float = 0.1
    ):
        """
        Initialize complete fair ranking system.
        
        Args:
            scores_df: DataFrame with poster scores (rows=posters, cols=judges)
            protected_attributes: DataFrame with sensitive/protected attributes
            min_reviews: Minimum reviews needed for full confidence
            selection_threshold: Fraction of top posters considered "selected"
            fairness_threshold: Maximum allowed fairness disparity
        """
        self.scores_df = scores_df
        self.protected_attributes = protected_attributes
        self.min_reviews = min_reviews
        self.selection_threshold = selection_threshold
        self.fairness_threshold = fairness_threshold
        self.bias_metrics = None
        self.fairness_metrics = None
        
    def detect_systematic_bias(self) -> Dict[str, float]:
        """
        Detect systematic bias in judge scoring patterns.
        """
        bias_scores = {}
        for judge in self.scores_df.columns:
            scores = self.scores_df[judge][self.scores_df[judge] > 0]
            if len(scores) > 1:
                iso_forest = IsolationForest(contamination=0.1, random_state=42)
                outlier_labels = iso_forest.fit_predict(scores.values.reshape(-1, 1))
                bias_scores[judge] = np.mean(outlier_labels == -1)
            else:
                bias_scores[judge] = 0.5
        return bias_scores
    
    def calculate_coverage_bias(self) -> float:
        """
        Calculate bias in review coverage.
        """
        review_counts = (self.scores_df > 0).sum(axis=1)
        expected_reviews = len(self.scores_df.columns) / 2
        coverage_bias = abs(review_counts - expected_reviews) / expected_reviews
        return coverage_bias.mean()
    
    def detect_scoring_bias(self) -> Dict[str, float]:
        """
        Detect bias in scoring patterns.
        """
        scoring_bias = {}
        for judge in self.scores_df.columns:
            scores = self.scores_df[judge].dropna()
            if len(scores) >=8:
                # Test for normality
                _, normality_pval = stats.normaltest(scores)
                # Calculate skewness
                skew = stats.skew(scores)
                scoring_bias[judge] = 1 - normality_pval + abs(skew) / 3
            elif(len(scores) >0):
                scoring_bias[judge] = 0.5
            else:
                scoring_bias[judge] = np.nan
        return scoring_bias
    
    def calculate_selection_rates(self, rankings: pd.Series) -> Dict[str, Dict[str, float]]:
        """
        Calculate selection rates across protected groups.
        """
        if self.protected_attributes is None:
            return {}
            
        selection_rates = {}
        cutoff_rank = int(len(rankings) * self.selection_threshold)
        selected = rankings[rankings <= cutoff_rank].index
        
        for attribute in self.protected_attributes.columns:
            rates = {}
            groups = self.protected_attributes[attribute].unique()
            
            for group in groups:
                group_members = self.protected_attributes[
                    self.protected_attributes[attribute] == group
                ].index
                group_size = len(group_members)
                selected_from_group = len(set(selected) & set(group_members))
                rates[group] = selected_from_group / group_size if group_size > 0 else 0
                
            selection_rates[attribute] = rates
            
        return selection_rates
    
    def calculate_error_rates(
        self, 
        rankings: pd.Series,
        scores: pd.Series
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Calculate false positive and negative rates.
        """
        if self.protected_attributes is None:
            return {}, {}
            
        score_threshold = scores.quantile(1 - self.selection_threshold)
        rank_threshold = int(len(rankings) * self.selection_threshold)
        
        false_positives = {}
        false_negatives = {}
        
        for attribute in self.protected_attributes.columns:
            groups = self.protected_attributes[attribute].unique()
            
            for group in groups:
                group_members = self.protected_attributes[
                    self.protected_attributes[attribute] == group
                ].index
                
                qualified = scores[group_members] >= score_threshold
                selected = rankings[group_members] <= rank_threshold
                
                # False positive rate
                if (~qualified).sum() > 0:
                    fpr = (selected & ~qualified).sum() / (~qualified).sum()
                    false_positives[f"{attribute}_{group}"] = fpr
                    
                # False negative rate
                if qualified.sum() > 0:
                    fnr = (~selected & qualified).sum() / qualified.sum()
                    false_negatives[f"{attribute}_{group}"] = fnr
                    
        return false_positives, false_negatives
    
    def mitigate_bias(self, scores: pd.DataFrame) -> pd.DataFrame:
        """
        Apply bias mitigation techniques.
        """
        mitigated = scores.copy()
        
        # 1. Systematic bias correction
        systematic_bias = self.detect_systematic_bias()
        for judge, bias_score in systematic_bias.items():
            if bias_score > 0.3:
                correction = 1 - (bias_score * 0.5)
                mitigated[judge] *= correction
        
        # 2. Coverage bias mitigation
        coverage_bias = (self.scores_df > 0).sum(axis=1)
        coverage_weights = 1 / np.sqrt(coverage_bias)
        mitigated = mitigated.multiply(coverage_weights, axis=0)
        
        # 3. Distribution normalization
        scaler = StandardScaler()
        for judge in mitigated.columns:
            scores = mitigated[judge]
            valid_mask = scores > 0
            if valid_mask.sum() > 1:
                mitigated.loc[valid_mask, judge] = scaler.fit_transform(
                    scores[valid_mask].values.reshape(-1, 1)
                ).ravel()
                
        return mitigated
    
    def apply_fairness_constraints(
        self,
        rankings: pd.Series,
        scores: pd.Series
    ) -> pd.Series:
        """
        Apply fairness constraints to rankings.
        """
        if self.protected_attributes is None:
            return rankings
            
        adjusted_rankings = rankings.copy()
        iterations = 0
        max_iterations = 100
        
        while iterations < max_iterations:
            # Calculate current metrics
            selection_rates = self.calculate_selection_rates(adjusted_rankings)
            fps, fns = self.calculate_error_rates(adjusted_rankings, scores)
            
            # Check if constraints are satisfied
            dp_violations = []
            error_violations = []
            
            for attribute, rates in selection_rates.items():
                max_rate = max(rates.values())
                min_rate = min(rates.values())
                if max_rate - min_rate > self.fairness_threshold:
                    dp_violations.append((attribute, max_rate - min_rate))
            
            max_fp_diff = max(fps.values()) - min(fps.values()) if fps else 0
            max_fn_diff = max(fns.values()) - min(fns.values()) if fns else 0
            
            if max_fp_diff > self.fairness_threshold:
                error_violations.append(('FPR', max_fp_diff))
            if max_fn_diff > self.fairness_threshold:
                error_violations.append(('FNR', max_fn_diff))
            
            if not dp_violations and not error_violations:
                break
                
            # Apply corrections
            if dp_violations:
                # Fix worst demographic parity violation
                attribute, _ = max(dp_violations, key=lambda x: x[1])
                rates = selection_rates[attribute]
                max_group = max(rates.items(), key=lambda x: x[1])[0]
                min_group = min(rates.items(), key=lambda x: x[1])[0]
                
                # Swap one ranking between groups
                max_group_members = self.protected_attributes[
                    self.protected_attributes[attribute] == max_group
                ].index
                min_group_members = self.protected_attributes[
                    self.protected_attributes[attribute] == min_group
                ].index
                
                # Find candidates for swap
                threshold_rank = int(len(rankings) * self.selection_threshold)
                max_selected = adjusted_rankings[max_group_members] <= threshold_rank
                min_not_selected = adjusted_rankings[min_group_members] > threshold_rank
                
                if max_selected.any() and min_not_selected.any():
                    # Swap rankings
                    max_idx = adjusted_rankings[max_group_members][max_selected].idxmax()
                    min_idx = adjusted_rankings[min_group_members][min_not_selected].idxmin()
                    
                    max_rank = adjusted_rankings[max_idx]
                    min_rank = adjusted_rankings[min_idx]
                    
                    adjusted_rankings[max_idx] = min_rank
                    adjusted_rankings[min_idx] = max_rank
            
            iterations += 1
            
        return adjusted_rankings
    
    def compute_rankings(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Compute fair rankings with comprehensive metrics.
        """
        # 1. Bias mitigation
        mitigated_scores = self.mitigate_bias(self.scores_df)
        
        # 2. Calculate base rankings
        mean_scores = mitigated_scores.mean(axis=1)
        initial_rankings = mean_scores.rank(ascending=False, method='min')
        
        # 3. Apply fairness constraints
        final_rankings = self.apply_fairness_constraints(initial_rankings, mean_scores)
        
        # 4. Calculate final metrics
        selection_rates = self.calculate_selection_rates(final_rankings)
        fps, fns = self.calculate_error_rates(final_rankings, mean_scores)
        
        # Calculate comprehensive metrics
        dp_differences = []
        dp_ratios = []
        
        for rates in selection_rates.values():
            max_rate = max(rates.values())
            min_rate = min(rates.values())
            dp_differences.append(max_rate - min_rate)
            dp_ratios.append(min_rate / max_rate if max_rate > 0 else 1.0)
        
        self.fairness_metrics = FairnessMetrics(
            demographic_parity_difference=np.mean(dp_differences),
            demographic_parity_ratio=np.mean(dp_ratios),
            equalized_odds_difference=selection_rates,
            false_positive_rate=fps,
            false_negative_rate=fns,
            bias_score=np.mean([
                np.mean(list(self.detect_systematic_bias().values())),
                self.calculate_coverage_bias(),
                np.mean(list(self.detect_scoring_bias().values()))
            ]),
            selection_rate=selection_rates
        )
        
        # Create results DataFrame
        results = pd.DataFrame({
            'rank': final_rankings,
            'original_score': self.scores_df.mean(axis=1),
            'mitigated_score': mitigated_scores.mean(axis=1),
            'n_reviews': (self.scores_df > 0).sum(axis=1)
        })
        
        # Add protected attributes if available
        if self.protected_attributes is not None:
            for col in self.protected_attributes.columns:
                results[f'protected_{col}'] = self.protected_attributes[col]
        
        return results.sort_values('rank'), self.fairness_metrics.__dict__

def load_and_rank_posters(
    scores_filepath: str,
    protected_filepath: Optional[str] = None,
    min_reviews: int = 2,
    selection_threshold: float = 0.25,
    fairness_threshold: float = 0.1
) -> Tuple[pd.DataFrame, Dict]:
    """
    Load data and compute fair rankings.
    
    Args:
        scores_filepath: Path to Excel file with judge scores
        protected_filepath: Optional path to protected attributes file
        min_reviews: Minimum reviews needed
        selection_threshold: Fraction of top posters considered "selected"
        fairness_threshold: Maximum allowed fairness disparity
        
    Returns:
        Tuple of (rankings DataFrame, fairness metrics dict)
    """
    # Load scores
    scores_df = pd.read_excel(scores_filepath)
    if not scores_df.index.name:
        scores_df.set_index(scores_df.columns[0], inplace=True)
    
    # Load protected attributes if provided
    protected_df = None
    if protected_filepath:
        protected_df = pd.read_excel(protected_filepath)
        if not protected_df.index.name:
            protected_df.set_index(protected_df.columns[0], inplace=True)
    
    # Initialize ranking system
    ranker = CompleteFairRankingSystem(
        scores_df,
        protected_df,
        min_reviews,
        selection_threshold,
        fairness_threshold
    )
    
    # Compute rankings
    rankings, metrics = ranker.compute_rankings()
    
    return rankings, metrics

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Fair Poster Ranking System')
    parser.add_argument('scores_file', help='Excel file with judge scores')
    parser.add_argument('--protected', help='Excel file with protected attributes')
    parser.add_argument('--min-reviews', type=int, default=2,
                      help='Minimum reviews needed (default: 2)')
    parser.add_argument('--selection-threshold', type=float, default=0.25,
                      help='Selection threshold (default: 0.25)')
    parser.add_argument('--fairness-threshold', type=float, default=0.1,
                      help='Maximum allowed fairness disparity (default: 0.1)')
    parser.add_argument('--output-dir', default='.',
                      help='Directory to save output files (default: current directory)')
    
    args = parser.parse_args()
    
    try:
        # Compute rankings
        print("Computing fair rankings...")
        rankings, metrics = load_and_rank_posters(
            args.scores_file,
            args.protected,
            args.min_reviews,
            args.selection_threshold,
            args.fairness_threshold
        )
        
        # Create timestamp for output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save rankings
        rankings_path = f'{args.output_dir}/fair_rankings_{timestamp}.xlsx'
        rankings.to_excel(rankings_path)
        
        # Save metrics
        metrics_path = f'{args.output_dir}/fairness_metrics_{timestamp}.json'
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
            
        print(f"\nResults successfully saved:")
        print(f"- Rankings: {rankings_path}")
        print(f"- Metrics: {metrics_path}")
        
        # Print summary statistics
        print("\nFairness Metrics Summary:")
        print(f"- Demographic Parity Difference: {metrics['demographic_parity_difference']:.3f}")
        print(f"- Demographic Parity Ratio: {metrics['demographic_parity_ratio']:.3f}")
        print(f"- Overall Bias Score: {metrics['bias_score']:.3f}")
        
        if metrics['selection_rate']:
            print("\nSelection Rates by Group:")
            for attribute, rates in metrics['selection_rate'].items():
                print(f"\n{attribute}:")
                for group, rate in rates.items():
                    print(f"  - {group}: {rate:.3f}")
        
        # Print top rankings
        print("\nTop 5 Ranked Posters:")
        top5 = rankings.head()
        print(top5[['rank', 'original_score', 'mitigated_score', 'n_reviews']])
        
    except FileNotFoundError as e:
        print(f"\nError: Could not find input file - {str(e)}")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print(f"\nError: The input file is empty or has no valid data")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: An unexpected error occurred - {str(e)}")
        sys.exit(1).add_argument('--fairness-threshold', type=float, default=0.1,
                      help='Fairness threshold (default: 0.1)')
    
    args = parser.parse_args()
    
    # Compute rankings
    rankings, metrics = load_and_rank_posters(
        args.scores_file,
        args.protected,
        args.min_reviews,
        args.selection_threshold,
        args.fairness_threshold
    )
    
    # Save results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save rankings
    rankings_path = f'fair_rankings_{timestamp}.xlsx'
    rankings.to_excel(rankings_path)
    
    # Save metrics
    metrics_path = f'fairness_metrics_{timestamp}.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
        
    print(f"\nResults saved:")
    print(f"- Rankings: {rankings_path}")
    print(f"- Metrics: {metrics_path}")
    
    # Print summary
    print("\nFairness Metrics Summary:")
    print(f"- Demographic Parity Difference: {metrics['demographic_parity_difference']:.3f}")
    print(f"- Demographic Parity Ratio: {metrics['demographic_parity_ratio']:.3f}")
    print(f"- Bias Score: {metrics['bias_score']:.3f}")
    
    # Print top 5 rankings
    print("\nTop 5 Posters:")
    top5 = rankings.head()
    print(top5[['rank', 'original_score', 'mitigated_score', 'n_reviews']])