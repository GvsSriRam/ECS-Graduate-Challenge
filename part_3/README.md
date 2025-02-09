# Part 3: Fair Poster Ranking System

## Overview
This module implements an automated and fair ranking system for the ECS Graduate Research Day poster competition. It processes judge scores while accounting for different judging styles, potential biases, and ensures equitable evaluation across all posters through advanced normalization techniques.

## Directory Structure
```
.
├── README.md
├── requirements.txt
├── fair_ranking.py                    # Main ranking algorithm
└── tests/                            # Unit tests for ranking system
```

## Setup Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Run the ranking system:
```bash
python fair_ranking.py
```

The system will:
1. Load scores from the input Excel file
2. Apply normalization and bias correction
3. Generate final rankings
4. Save results and display top 10 rankings

## Input Requirements

Input file (`poster_scores.xlsx`):
- Must be in Excel format
- Required structure:
  - First column: Poster IDs
  - Subsequent columns: Judge scores
  - Values: 0-10 (0 for no review)

Example format:
```
          Judge-1  Judge-2  Judge-3  ...
Poster-1    7.5      0.0      8.0   ...
Poster-2    0.0      6.5      0.0   ...
Poster-3    8.0      7.0      0.0   ...
```

## Output Files

Generated file (`rankings_results_[timestamp].xlsx`):
- Final poster rankings
- Original and normalized scores
- Review coverage information
- Judge reliability metrics

Columns include:
- Rank: Final position
- Original_Average: Raw score average
- Normalized_Score: Bias-corrected score
- Number_of_Reviews: Review count

## Technical Implementation Details

### Ranking Methodology

1. Score Normalization
- Z-score normalization per judge
- Range standardization
- Outlier detection and handling

2. Judge Reliability Analysis
- Consistency scoring
- Inter-judge agreement metrics
- Weighted score aggregation

3. Review Coverage Compensation
- Statistical adjustments for varying review counts
- Confidence interval calculations
- Missing data handling

### Bias Mitigation Techniques

1. Judge-Level Corrections
- Personal bias detection
- Systematic bias removal
- Scale preference normalization

2. Poster-Level Adjustments
- Topic-based bias detection
- Time-slot impact analysis
- Review order effects compensation

3. Statistical Safeguards
- Confidence bounds calculation
- Uncertainty quantification
- Robustness checks

## Error Handling

System handles common issues:
- Missing or corrupted input files
- Invalid score ranges
- Incomplete review sets
- Data format inconsistencies

## Notes
- Maintains transparency by preserving original scores
- Provides detailed bias correction audit trail
- Implements statistical validation of results