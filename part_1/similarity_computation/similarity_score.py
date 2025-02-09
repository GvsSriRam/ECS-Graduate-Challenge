import os
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

MODEL_NAME = 'all_MiniLM'

def calculate_similarity(embeddings1, embeddings2):
    """Calculate cosine similarity between two sets of embeddings"""
    return cosine_similarity(embeddings1, embeddings2)

# Load the embeddings from .npy files
embeddings_dir = f'part-1/embeddings/embeddings_npy/{MODEL_NAME}/'
poster_embeddings = np.load(Path(embeddings_dir) / 'poster_abstract_embeddings.npy')
judge_embeddings = np.load(Path(embeddings_dir) / 'primary_author_embeddings.npy')

print(f"Loaded poster embeddings with shape: {poster_embeddings.shape}")
print(f"Loaded judge embeddings with shape: {judge_embeddings.shape}")

# Calculate similarity matrix
similarity_scores = calculate_similarity(poster_embeddings, judge_embeddings)
print(f"Calculated similarity scores with shape: {similarity_scores.shape}")

# Load metadata for indices and columns
# Assuming you have these files with the corresponding information
poster_info = pd.read_excel('Sample_input_abstracts.xlsx')  # Or whatever format your poster info is in
judge_info = pd.read_excel('Example_list_judges.xlsx')      # Or whatever format your judge info is in

judge_names = np.load('part-1/embeddings/judge_names.npy')

# Create DataFrame with proper labels
similarity_df = pd.DataFrame(
    similarity_scores,
    index=poster_info['Poster'],    # Adjust column name if different
    columns=judge_names        # Adjust column name if different
)

# Save to CSV
scores_dir = f'part-1/similarity_computation/{MODEL_NAME}'
os.makedirs(scores_dir, exist_ok=True)

similarity_df.to_csv(f'{scores_dir}/similarity_scores.csv')
print("Similarity scores saved to 'similarity_scores.csv'")

# Optional: Print some statistics
print("\nSimilarity Score Statistics:")
print(f"Average similarity: {np.mean(similarity_scores):.4f}")
print(f"Maximum similarity: {np.max(similarity_scores):.4f}")
print(f"Minimum similarity: {np.min(similarity_scores):.4f}")