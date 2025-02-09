import os
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# Use the same model lists from previous scripts
native_models = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-mpnet-base-v2",
    "sentence-transformers/multi-qa-mpnet-base-dot-v1",
    "malteos/SciNCL",
    "pritamdeka/S-PubMedBert-MS-MARCO"
]

custom_models = [
    "allenai/specter",
    "allenai/specter-2",
    "allenai/scibert_scivocab_uncased",
    "gsarti/scibert-nli"
]

models_to_try = native_models + custom_models

def calculate_similarity(embeddings1, embeddings2):
    """Calculate cosine similarity between two sets of embeddings"""
    return cosine_similarity(embeddings1, embeddings2)

def process_model_similarities(model_name):
    print(f"\nProcessing similarities for model: {model_name}")
    
    # Load the embeddings from .npy files
    embeddings_dir = f'part_1/embeddings/embeddings_npy/{model_name}/'
    try:
        poster_embeddings = np.load(Path(embeddings_dir) / 'poster_abstract_embeddings.npy')
        judge_embeddings = np.load(Path(embeddings_dir) / 'primary_author_embeddings.npy')
        
        print(f"Loaded poster embeddings with shape: {poster_embeddings.shape}")
        print(f"Loaded judge embeddings with shape: {judge_embeddings.shape}")

        # Calculate similarity matrix
        similarity_scores = calculate_similarity(poster_embeddings, judge_embeddings)
        print(f"Calculated similarity scores with shape: {similarity_scores.shape}")

        # Load metadata for indices and columns
        poster_info = pd.read_excel('Sample_input_abstracts.xlsx')
        judge_names = np.load('part_1/embeddings/judge_names.npy')
        judge_info = pd.read_excel('Example_list_judges.xlsx')

        # Standardize programs and get departments
        standardized_programs = poster_info['Program'].apply(standardize_program_name)
        judge_departments = judge_info['Department']  # Adjust column name as needed
        
        # Adjust similarity scores based on department matches
        adjusted_scores = adjust_similarity_for_department(
            similarity_scores, 
            standardized_programs,
            judge_departments
        )

        # Create DataFrame with proper labels
        similarity_df = pd.DataFrame(
            adjusted_scores,
            index=poster_info['Poster'],    # Adjust column name if different
            columns=judge_names
        )

        # Save to CSV
        scores_dir = f'part_1/similarity_computation/{model_name}'
        os.makedirs(scores_dir, exist_ok=True)

        similarity_df.to_csv(f'{scores_dir}/similarity_scores.csv')
        print(f"Similarity scores saved for model {model_name}")

        # Print statistics
        print("\nSimilarity Score Statistics:")
        print(f"Average similarity: {np.mean(adjusted_scores):.4f}")
        print(f"Maximum similarity: {np.max(adjusted_scores):.4f}")
        print(f"Minimum similarity: {np.min(adjusted_scores):.4f}")
        
    except Exception as e:
        print(f"Error processing model {model_name}: {str(e)}")

# Department abbreviations mapping
DEPT_MAPPING = {
    'BMCE': 'Biomedical and Chemical Engineering',
    'CEE': 'Civil and Environmental Engineering',
    'EECS': 'Electrical Engineering and Computer Science',
    'MAE': 'Mechanical and Aerospace Engineering'
}

# Program to Department mapping
PROGRAM_TO_DEPT = {
    'Biomedical Engineering': 'BMCE',
    'Chemical Engineering': 'BMCE',
    'Civil Engineering': 'CEE',
    'Computer Engineering': 'EECS',
    'Computer Science': 'EECS',
    'Cybersecurity': 'EECS',
    'Electrical Engineering': 'EECS',
    'Engineering Management': 'EECS',  # This might need adjustment
    'Environmental Engineering': 'CEE',
    'Mechanical and Aerospace Engineering': 'MAE',
    'Operations Research and System Analytics': 'EECS'  # This might need adjustment
}

# Function to standardize program names from abstracts
def standardize_program_name(program):
    # TODO: Check fuzzy matching or other methods for better standardization
    # Dictionary to map various forms to standard names
    program_variants = {
        'Computer/Information Science': 'Computer Science',
        'Electrical/Computer Engineering': 'Electrical Engineering',
        'Bioengineering': 'Biomedical Engineering',
    }
    return program_variants.get(program, program)

# Modified similarity computation code
def adjust_similarity_for_department(similarity_scores, poster_programs, judge_departments):
    """
    Adjust similarity scores based on program-department matches
    
    Args:
        similarity_scores: Original similarity matrix
        poster_programs: Series/array of poster programs (standardized)
        judge_departments: Series/array of judge departments (in short form)
        
    Returns:
        Modified similarity matrix with department matches boosted
    """
    adjusted_scores = similarity_scores.copy()
    
    for i, program in enumerate(poster_programs):
        std_program = standardize_program_name(program)
        if std_program in PROGRAM_TO_DEPT:
            matching_dept = PROGRAM_TO_DEPT[std_program]
            for j, dept in enumerate(judge_departments):
                if dept == matching_dept:
                    # print(f"Match found: {std_program} -> {matching_dept}")
                    # print(adjusted_scores[i, j])
                    adjusted_scores[i, j] += 1.0 if adjusted_scores[i, j] > 0.3 else 0.0  # Add boost for department match
                    # print(adjusted_scores[i, j])
    
    return adjusted_scores



def main():
    # Process similarities for each model
    for model_name in models_to_try:
        process_model_similarities(model_name)

if __name__ == "__main__":
    main()