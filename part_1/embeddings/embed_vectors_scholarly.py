import os
import csv
import json
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, models
import re

# Compare different models
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

def normalize_name_for_json(name: str) -> str:
    """
    Converts a professor's name to a format that matches the JSON filename in the dataset.
    Assumes format is 'first_last.json' with all lowercase and underscores for spaces,
    removing any periods or special characters from middle initials or suffixes.
    """
    # Normalize the name by removing any non-alphanumeric characters except spaces
    # normalized_name = re.sub(r'[^\w\s]', '', name)
    # Replace all spaces with underscores and convert to lowercase
    normalized_name = name.replace(' ', '_').lower()
    return f"{normalized_name}.json"

def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    # Remove special characters
    text = re.sub(r'[^\w\s]', ' ', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

def build_text_from_publications(interests, publications):
    """
    Combines a professor's interests with the titles and abstracts of their publications.
    """
    interests_text = " ".join(interests)
    pubs_text = " ".join(f"{preprocess_text(pub['title'])} {preprocess_text(pub['abstract'])}" for pub in publications)
    return f"{interests_text} {pubs_text}".strip()

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

def embed_text(model_name):
    # model = SentenceTransformer("all-MiniLM-L6-v2")
    model = build_model(model_name)
    if model is None:
        print(f"Skipping model {model_name} due to loading failure")
        return

    csv_file = "part_1/data_extraction/profiles_csv/ecs_faculty_staff.csv"  # Ensure this matches the actual CSV filename
    primary_embeddings = []
    secondary_embeddings = []
    prof_names = []

    # Set the directory where JSON files are stored
    base_directory = os.path.join(os.getcwd(), 'faculty_scholarly')

    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            prof_name = row["name"].strip()
            prof_names.append(prof_name)
            json_filename = normalize_name_for_json(prof_name)
            json_path = os.path.join(base_directory, json_filename)  

            if not os.path.exists(json_path):
                print(f"Warning: JSON file not found for '{prof_name}': {json_filename}.")
                emb_dim = model.get_sentence_embedding_dimension()
                primary_embeddings.append(np.zeros(emb_dim))
                secondary_embeddings.append(np.zeros(emb_dim))
                continue
            
            with open(json_path, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
                interests = data.get("interests", [])
                primary_pubs = data.get("top_primary_author_publications", [])
                secondary_pubs = data.get("top_secondary_author_publications", [])
                # print(primary_pubs)
                # print(secondary_pubs)

                primary_text = build_text_from_publications(interests, primary_pubs)
                secondary_text = build_text_from_publications(interests, secondary_pubs)
                
                primary_emb = model.encode(primary_text, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
                secondary_emb = model.encode(secondary_text, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
                
                primary_embeddings.append(primary_emb)
                secondary_embeddings.append(secondary_emb)

    primary_embeddings = np.array(primary_embeddings)
    secondary_embeddings = np.array(secondary_embeddings)

    output_file_path_npy_primary = f'part_1/embeddings/embeddings_npy/{model_name}/primary_author_embeddings.npy'
    output_file_path_npy_secondary = f'part_1/embeddings/embeddings_npy/{model_name}/secondary_author_embeddings.npy'
    # Create the output directory if it does not exist
    output_dir = os.path.dirname(output_file_path_npy_primary)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    np.save(output_file_path_npy_primary, primary_embeddings)
    np.save(output_file_path_npy_secondary, secondary_embeddings)

    output_file_path_csv_primary = f'part_1/embeddings/embeddings_csv/{model_name}/primary_author_embeddings.csv'
    output_file_path_csv_secondary = f'part_1/embeddings/embeddings_csv/{model_name}/secondary_author_embeddings.csv'
    # Create the output directory if it does not exist
    output_dir = os.path.dirname(output_file_path_csv_primary)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save embeddings to CSV for easier access or use in other applications
    pd.DataFrame(primary_embeddings).to_csv(output_file_path_csv_primary, index=False)
    pd.DataFrame(secondary_embeddings).to_csv(output_file_path_csv_secondary, index=False)
    print("Embeddings saved as .npy and .csv files.")

    output_file_path_names = 'part_1/embeddings/judge_names.npy'
    np.save(output_file_path_names, np.array(prof_names))

def main():
    for model_name in models_to_try:
        print(f"Embedding text using model: {model_name}")
        embed_text(model_name)

if __name__ == "__main__":
    main()
