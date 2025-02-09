import os
import pandas as pd
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np

MODEL_NAME = 'all_MiniLM'

# Function to initialize the model and tokenizer
def load_model():
    tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
    model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
    return tokenizer, model

# Function to compute embeddings
def get_embedding(text, tokenizer, model):
    inputs = tokenizer(text, return_tensors='pt', max_length=512, truncation=True, padding='max_length')
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.cpu().numpy()

# Main function to process the data
def process_data(file_path):
    # Load the data
    df = pd.read_excel(file_path, engine='openpyxl')

    # Load model and tokenizer
    tokenizer, model = load_model()

    # Generate embeddings
    df['Abstract'] = df['Abstract'].fillna('')  # Replace NaN with empty string
    df['embeddings'] = df['Abstract'].apply(lambda x: get_embedding(x, tokenizer, model))
    df = df.dropna(subset=['Abstract'])

    # Save emneddings in numpy format
    embeddings = df['embeddings'].values
    embeddings = np.vstack(embeddings)

    # Save the data with embeddings
    output_file_path_npy = f'part-1/embeddings/embeddings_npy/{MODEL_NAME}/poster_abstract_embeddings.npy'
    # Create the output directory if it does not exist
    output_dir = os.path.dirname(output_file_path_npy)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    np.save(output_file_path_npy, embeddings)

    # Save the data with embeddings
    output_file_path_csv = f'part-1/embeddings/embeddings_csv/{MODEL_NAME}/poster_abstract_embeddings.csv'
    # Create the output directory if it does not exist
    output_dir = os.path.dirname(output_file_path_csv)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    df.to_csv(output_file_path_csv, index=False)
    print(f"Embeddings saved to {output_file_path_csv}")

# Path to the Excel file containing the abstracts
input_file_path = 'Sample_input_abstracts.xlsx'

# Process the data
process_data(input_file_path)
