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
├── similarity_computation/  
│   └── similarity_score.py                # Judge-poster matching
└── poster_assignment/
    └── poster_assignment.py               # Optimal assignment algorithm

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
4. Run Poster Assignment:
```bash
# After generating embeddings and similarity scores
python poster_assignment/poster_assignment.py
```

## Input Requirements

- `Sample_input_abstracts.xlsx`:
  - Must contain poster abstracts and advisor information
  - Required columns: "Poster", "Abstract", "Advisor"

- `Example_list_judges.xlsx`:
  - Must contain judge availability information
  - Required columns: "Name", "Available_Hour1", "Available_Hour2"
- For Poster Assignment:
  - `similarity_scores.csv`:
    - Contains similarity scores computed between faculty research profiles and poster abstracts
      - Format: Matrix where rows are posters and columns are judges
      - Values: Computed similarity scores from research area and abstract matching
  - Scores are derived from:
    - Research interests similarity
    - Publication abstracts similarity
    - Research area matching

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
4. 

## Constraints Handled

- Each poster gets exactly 2 judges
- Each judge reviews maximum 6 posters
- Odd/even numbered posters scheduled in different hours
- Judge time slot availability respected
- No advisor-advisee assignments
- Research area compatibility maximized

## Technical Implementation Details

### Embedding Models Evaluated
We evaluate several state-of-the-art models for generating research area embeddings:

1. Native Sentence-Transformer Models:
- `sentence-transformers/all-MiniLM-L6-v2`: Lightweight, fast, good balance of performance
- `sentence-transformers/all-mpnet-base-v2`: Higher accuracy, larger model
- `sentence-transformers/multi-qa-mpnet-base-dot-v1`: Optimized for similarity matching
- `malteos/SciNCL`: Specifically trained on scientific text
- `pritamdeka/S-PubMedBert-MS-MARCO`: Specialized for scientific/medical content

2. Custom Transformer Models:
- `allenai/specter`: Trained on scientific papers citations
- `allenai/specter-2`: Improved version with better scientific understanding
- `allenai/scibert_scivocab_uncased`: Scientific text specialized BERT
- `gsarti/scibert-nli`: Scientific BERT with natural language inference

3. Poster Assignment Module:
- The poster assignment system implements:
   - Optimization Model:
     - Uses integer linear programming (PuLP)
     -  Maximizes research area compatibility
     -  Enforces scheduling and advisor constraints
- Key Features:
   - Multi-format output generation (Excel, CSV, JSON)
   - Comprehensive error handling
   - Input validation and data integrity checks

### Faculty Profile Extraction
For each faculty member, we extract comprehensive research information from multiple sources. Sample extracted data structure:

```json
{
  "name": "Faculty Name",
  "affiliation": "Syracuse University",
  "interests": [
    "research area 1",
    "research area 2",
    ...
  ],
  "citedby": <citation_count>,
  "h_index": <h_index>,
  "i10_index": <i10_index>,
  "top_primary_author_publications": [
    {
      "title": "Publication Title",
      "year": "Publication Year",
      "abstract": "Publication Abstract",
      "venue": "Publication Venue",
      "citations": <citation_count>,
      "authors": ["Author 1", "Author 2", ...],
      "url": "Publication URL"
    },
    ...
  ],
  "top_secondary_author_publications": [
    // Similar structure as primary publications
  ]
}
```

### Similarity Computation
- Implements cosine similarity for research area matching
- Uses weighted combination of:
  - Research interests similarity
  - Publication abstracts similarity
  - Publication venues alignment
- Normalizes scores for fair comparison
- Employs integer programming for optimal assignment while respecting all constraints
