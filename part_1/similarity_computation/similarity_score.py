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

        # Create DataFrame with proper labels
        similarity_df = pd.DataFrame(
            similarity_scores,
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
        print(f"Average similarity: {np.mean(similarity_scores):.4f}")
        print(f"Maximum similarity: {np.max(similarity_scores):.4f}")
        print(f"Minimum similarity: {np.min(similarity_scores):.4f}")
        
    except Exception as e:
        print(f"Error processing model {model_name}: {str(e)}")

def main():
    # Process similarities for each model
    for model_name in models_to_try:
        process_model_similarities(model_name)

if __name__ == "__main__":
    main()