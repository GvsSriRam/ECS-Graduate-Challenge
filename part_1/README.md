# Part 1: Judge-Poster Assignment System

## Overview
This module implements the automated judge assignment system for the ECS Graduate Research Day poster competition. It extracts faculty research profiles, analyzes poster abstracts, and generates optimal judge-poster assignments based on research area compatibility while satisfying all scheduling and conflict constraints.

## Directory Structure
```
.
├── README.md
├── requirements.txt
├── data_extraction/          
│   ├── extract-prof.py                    # Basic faculty data extraction
│   ├── extract-prof-and-profile-data.py   # Detailed profile extraction
│   ├── faculty_data_combination.py        # Data consolidation
│   └── faculty_data_extraction.ipynb      # Interactive data processing
├── embeddings/              
│   ├── embed_vectors_scholarly.py         # Research profile embeddings
│   ├── judge_embed_vector.py             # Judge data embeddings
│   └── poster_abstracts_embed_vector.py   # Poster abstract embeddings
└── similarity_computation/  
    └── similarity_score.py                # Judge-poster matching
```

## Setup Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

1. Extract faculty profiles:

- Extract the info from ECS faculty directory
```bash
python data_extraction/extract-prof-and-profile-data.py
python data_extraction/extract-prof.py
```
- Scrape info from web resources
```
Run jupyter notebooks - faculty_data_extraction.ipynb
```
- Combine the information from all sources
```bash
python data_extraction/faculty_data_combination.py
```

2. Generate embeddings:
- Judge embeddings
```bash
python embeddings/embed_vectors_scholarly.py
```
- Poster embeddings
```bash
python embeddings/poster_abstracts_embed_vector.py
```

3. Compute similarity scores:
```bash
python similarity_computation/similarity_score.py
```

## Input Requirements

- `Sample_input_abstracts.xlsx`:
  - Must contain poster abstracts and advisor information
  - Required columns: "Poster", "Abstract", "Advisor"

- `Example_list_judges.xlsx`:
  - Must contain judge availability information
  - Required columns: "Name", "Available_Hour1", "Available_Hour2"

## Output Files

1. Extended poster list (`poster_assignments.xlsx`):
  - Original poster data plus assigned judges
  - Added columns: "Judge1", "Judge2"

2. Extended judge list (`judge_assignments.xlsx`):
  - Original judge data plus assigned posters
  - Added columns: "Poster1" through "Poster6"

3. Assignment matrix (`assignment_matrix.xlsx`):
  - Binary matrix showing all assignments
  - Rows: posters, Columns: judges
  - Entries: 1 (assigned) or 0 (not assigned)

## Constraints Handled

- Each poster gets exactly 2 judges
- Each judge reviews maximum 6 posters
- Odd/even numbered posters scheduled in different hours
- Judge time slot availability respected
- No advisor-advisee assignments
- Research area compatibility maximized

## Technical Details

- Uses sentence transformers for research area matching
- Implements cosine similarity for compatibility scoring
- Employs integer programming for optimal assignment