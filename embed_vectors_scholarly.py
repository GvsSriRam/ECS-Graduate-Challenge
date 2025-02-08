import os
import csv
import json
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import re

def normalize_name_for_json(name: str) -> str:
    """
    Converts a professor's name to a format that matches the JSON filename in the dataset.
    Assumes format is 'first_last.json' with all lowercase and underscores for spaces,
    removing any periods or special characters from middle initials or suffixes.
    """
    # Normalize the name by removing any non-alphanumeric characters except spaces
    normalized_name = re.sub(r'[^\w\s]', '', name)
    # Replace all spaces with underscores and convert to lowercase
    normalized_name = normalized_name.replace(' ', '_').lower()
    return f"{normalized_name}.json"

def build_text_from_publications(interests, publications):
    """
    Combines a professor's interests with the titles and abstracts of their publications.
    """
    interests_text = " ".join(interests)
    pubs_text = " ".join(f"{pub['title']} {pub['abstract']}" for pub in publications)
    return f"{interests_text} {pubs_text}".strip()

def main():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    csv_file = "ecs_faculty_staff.csv"  # Ensure this matches the actual CSV filename
    primary_embeddings = []
    secondary_embeddings = []

    # Set the directory where JSON files are stored
    base_directory = os.path.join(os.getcwd(), 'faculty_scholarly')

    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            prof_name = row["name"].strip()
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

                primary_text = build_text_from_publications(interests, primary_pubs)
                secondary_text = build_text_from_publications(interests, secondary_pubs)
                
                primary_emb = model.encode(primary_text)
                secondary_emb = model.encode(secondary_text)
                
                primary_embeddings.append(primary_emb)
                secondary_embeddings.append(secondary_emb)

    primary_embeddings = np.array(primary_embeddings)
    secondary_embeddings = np.array(secondary_embeddings)
    np.save("primary_author_embeddings.npy", primary_embeddings)
    np.save("secondary_author_embeddings.npy", secondary_embeddings)

    # Save embeddings to CSV for easier access or use in other applications
    pd.DataFrame(primary_embeddings).to_csv("primary_author_embeddings.csv", index=False)
    pd.DataFrame(secondary_embeddings).to_csv("secondary_author_embeddings.csv", index=False)
    print("Embeddings saved as .npy and .csv files.")

if __name__ == "__main__":
    main()
