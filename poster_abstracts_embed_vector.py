import pandas as pd
from transformers import AutoTokenizer, AutoModel
import torch

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

    # Save the data with embeddings
    output_file_path = 'poster_abstract_embeddings.csv'
    df.to_csv(output_file_path, index=False)
    print(f"Embeddings saved to {output_file_path}")

# Path to the Excel file containing the abstracts
input_file_path = '/Users/pranathi/Documents/SU courses/ecs_coding_challenge/Sample_input_abstracts.xlsx'

# Process the data
process_data(input_file_path)
