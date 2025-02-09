import os
import pandas as pd
from sentence_transformers import SentenceTransformer, models
import numpy as np

# Use the same model lists as embed_vectors_scholarly.py
# Native sentence-transformer models
native_models = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-mpnet-base-v2",
    "sentence-transformers/multi-qa-mpnet-base-dot-v1",
    "malteos/SciNCL",
    "pritamdeka/S-PubMedBert-MS-MARCO"
]

# Models requiring custom transformer setup
custom_models = [
    "allenai/specter",
    "allenai/specter-2",
    "allenai/scibert_scivocab_uncased",
    "gsarti/scibert-nli"
]

models_to_try = native_models + custom_models

def build_model(model_name):
    # List of models that need special handling
    non_sentence_transformer_models = [
        "allenai/specter",
        "allenai/specter-2",
        "allenai/scibert_scivocab_uncased",
        "gsarti/scibert-nli"
    ]
    
    try:
        if model_name in non_sentence_transformer_models:
            # Create a sentence transformer model with mean pooling for these models
            word_embedding_model = models.Transformer(model_name)
            pooling_model = models.Pooling(
                word_embedding_model.get_word_embedding_dimension(),
                pooling_mode_mean_tokens=True,
                pooling_mode_cls_token=False,
                pooling_mode_max_tokens=False
            )
            return SentenceTransformer(modules=[word_embedding_model, pooling_model])
        else:
            # For native sentence transformer models, use direct initialization
            return SentenceTransformer(model_name)
    except Exception as e:
        print(f"Error loading model {model_name}: {str(e)}")
        return None

def process_data_with_model(file_path, model_name):
    # Load the data
    df = pd.read_excel(file_path, engine='openpyxl')
    
    # Build model
    model = build_model(model_name)
    if model is None:
        print(f"Skipping model {model_name} due to loading failure")
        return

    # Generate embeddings
    df['Abstract'] = df['Abstract'].fillna('')  # Replace NaN with empty string
    embeddings = []
    
    # Generate embeddings using the model
    for text in df['Abstract']:
        embedding = model.encode(text, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
        embeddings.append(embedding)
    
    # Convert to numpy array
    embeddings = np.array(embeddings)
    
    # Save embeddings in numpy format
    output_file_path_npy = f'part_1/embeddings/embeddings_npy/{model_name}/poster_abstract_embeddings.npy'
    # Create the output directory if it does not exist
    output_dir = os.path.dirname(output_file_path_npy)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    np.save(output_file_path_npy, embeddings)

    # Save embeddings in CSV format
    output_file_path_csv = f'part_1/embeddings/embeddings_csv/{model_name}/poster_abstract_embeddings.csv'
    # Create the output directory if it does not exist
    output_dir = os.path.dirname(output_file_path_csv)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save embeddings to CSV
    pd.DataFrame(embeddings).to_csv(output_file_path_csv, index=False)
    print(f"Embeddings saved for model: {model_name}")

def main():
    # Path to the Excel file containing the abstracts
    input_file_path = 'Sample_input_abstracts.xlsx'
    
    # Process the data with each model
    for model_name in models_to_try:
        print(f"Processing abstracts using model: {model_name}")
        process_data_with_model(input_file_path, model_name)

if __name__ == "__main__":
    main()