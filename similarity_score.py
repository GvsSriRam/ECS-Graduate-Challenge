import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

def parse_embeddings(embedding_str):
    # Remove surrounding brackets, split by space, and convert to float
    return np.array([float(x) for x in embedding_str.strip('[]').replace('\n', '').split()])

def load_embeddings(file_name, embedding_column):
    # Load the CSV file
    df = pd.read_csv(file_name)
    # Apply the parsing function to the specified 'embedding' column
    df['parsed_embeddings'] = df[embedding_column].apply(parse_embeddings)
    return df

def calculate_similarity(df1, df2):
    # Stack the embedding arrays for cosine similarity calculation
    embeddings1 = np.stack(df1['parsed_embeddings'].values)
    embeddings2 = np.stack(df2['parsed_embeddings'].values)
    # Compute the cosine similarity matrix
    return cosine_similarity(embeddings1, embeddings2)

# Load embeddings from CSV files using the appropriate column names
poster_embeddings = load_embeddings('poster_abstract_embeddings.csv', 'embeddings')
judge_embeddings = load_embeddings('ecs_judges_with_embeddings.csv', 'embedding')

# Calculate the similarity matrix
similarity_scores = calculate_similarity(poster_embeddings, judge_embeddings)

# Convert similarity matrix to DataFrame for saving
similarity_df = pd.DataFrame(similarity_scores, 
                             index=poster_embeddings['Poster #'], 
                             columns=judge_embeddings['name'])

# Save the DataFrame to a CSV file
similarity_df.to_csv('similarity_scores.csv')

print("Similarity scores saved to 'similarity_scores.csv'.")
