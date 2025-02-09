import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import os

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
            scores = self.scores_df[judge][self.scores_df[judge] > 0]
            if len(scores) >= 8:
                _, normality_pval = stats.normaltest(scores)
                skew = stats.skew(scores)
                scoring_bias[judge] = 1 - normality_pval + abs(skew) / 3
            elif(len(scores) > 0):
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
                
                if (~qualified).sum() > 0:
                    fpr = (selected & ~qualified).sum() / (~qualified).sum()
                    false_positives[f"{attribute}_{group}"] = fpr
                    
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
            selection_rates = self.calculate_selection_rates(adjusted_rankings)
            fps, fns = self.calculate_error_rates(adjusted_rankings, scores)
            
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
                
            if dp_violations:
                attribute, _ = max(dp_violations, key=lambda x: x[1])
                rates = selection_rates[attribute]
                max_group = max(rates.items(), key=lambda x: x[1])[0]
                min_group = min(rates.items(), key=lambda x: x[1])[0]
                
                max_group_members = self.protected_attributes[
                    self.protected_attributes[attribute] == max_group
                ].index
                min_group_members = self.protected_attributes[
                    self.protected_attributes[attribute] == min_group
                ].index
                
                threshold_rank = int(len(rankings) * self.selection_threshold)
                max_selected = adjusted_rankings[max_group_members] <= threshold_rank
                min_not_selected = adjusted_rankings[min_group_members] > threshold_rank
                
                if max_selected.any() and min_not_selected.any():
                    max_idx = adjusted_rankings[max_group_members][max_selected].idxmax()
                    min_idx = adjusted_rankings[min_group_members][min_not_selected].idxmin()
                    
                    max_rank = adjusted_rankings[max_idx]
                    min_rank = adjusted_rankings[min_idx]
                    
                    adjusted_rankings[max_idx] = min_rank
                    adjusted_rankings[min_idx] = max_rank
            
            iterations += 1
            
        return adjusted_rankings
    
    def compute_rankings(self) -> pd.DataFrame:
        """
        Compute fair rankings with comprehensive metrics.
        """
        # Calculate mitigated scores
        mitigated_scores = self.mitigate_bias(self.scores_df)
        
        # Calculate base rankings
        mean_scores = mitigated_scores.mean(axis=1)
        initial_rankings = mean_scores.rank(ascending=False, method='min')
        
        # Apply fairness constraints
        final_rankings = self.apply_fairness_constraints(initial_rankings, mean_scores)
        
        # Create simple output DataFrame
        results = pd.DataFrame({
            'Poster-ID': final_rankings.index,
            'Rank': final_rankings.values.astype(int)
        })
        
        return results.sort_values('Rank')

def main():
    try:
        # Check for input file
        if not os.path.exists('scores_file.xlsx'):
            print("Error: poster_scores.xlsx not found in current directory")
            return
            
        # Load scores
        print("Loading scores...")
        scores_df = pd.read_excel('scores_file.xlsx')
        scores_df.set_index(scores_df.columns[0], inplace=True)
        
        # Initialize ranking system
        ranker = CompleteFairRankingSystem(scores_df)
        
        # Compute rankings
        print("Computing rankings...")
        rankings = ranker.compute_rankings()
        
        # Save results
        rankings.to_excel('rankings.xlsx', index=False)
        print("\nRankings saved to rankings.xlsx")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()