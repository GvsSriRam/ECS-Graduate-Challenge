#!/usr/bin/env python3

import pandas as pd
from sentence_transformers import SentenceTransformer

# ============= FILE PATHS & MODEL =============
INPUT_CSV = "ecs_faculty_profiles.csv"                      # your input CSV
OUTPUT_CSV = "ecs_judges_with_embeddings.csv"     # output CSV
MODEL_NAME = "all-MiniLM-L6-v2"                   # pick a huggingface model

# ============= HELPER FUNCTION =============
def create_judge_text(row):
    """
    Combine relevant columns of the judge row into a single text block for embedding.
    Adjust columns to match your actual CSV structure.
    """
    name = str(row.get("name", ""))
    positions = str(row.get("positions", ""))
    department = str(row.get("department", ""))
    location = str(row.get("location", ""))
    email = str(row.get("email", ""))
    phone = str(row.get("phone", ""))
    
    # Potentially lists in CSV; handle them:
    degrees = row.get("degrees", "")
    if isinstance(degrees, list):
        degrees = ", ".join(degrees)
    else:
        degrees = str(degrees)
    
    areas_of_expertise = row.get("areas_of_expertise", "")
    if isinstance(areas_of_expertise, list):
        areas_of_expertise = ", ".join(areas_of_expertise)
    else:
        areas_of_expertise = str(areas_of_expertise)
    
    honors_and_awards = row.get("honors_and_awards", "")
    if isinstance(honors_and_awards, list):
        honors_and_awards = ", ".join(honors_and_awards)
    else:
        honors_and_awards = str(honors_and_awards)
    
    selected_publications = row.get("selected_publications", "")
    if isinstance(selected_publications, list):
        selected_publications = ", ".join(selected_publications)
    else:
        selected_publications = str(selected_publications)
    
    biography = str(row.get("biography", ""))
    
    # Consolidate into a single string
    text_block = (
        f"Name: {name}\n"
        f"Positions: {positions}\n"
        f"Department: {department}\n"
        f"Location: {location}\n"
        f"Degrees: {degrees}\n"
        f"Areas of Expertise: {areas_of_expertise}\n"
        f"Honors and Awards: {honors_and_awards}\n"
        f"Selected Publications: {selected_publications}\n"
        f"Biography: {biography}"
    )
    
    return text_block


def main():
    # ============= 1) LOAD CSV =============
    df_judges = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df_judges)} rows from {INPUT_CSV}")
    
    # ============= 2) CREATE TEXT BLOCKS =============
    judge_texts = []
    for _, row in df_judges.iterrows():
        full_text = create_judge_text(row)
        judge_texts.append(full_text)
    
    # ============= 3) EMBEDDING MODEL =============
    print(f"Loading SentenceTransformer model: {MODEL_NAME}")
    embedder = SentenceTransformer(MODEL_NAME)
    
    print("Generating embeddings for judges...")
    judge_embeddings = embedder.encode(judge_texts, convert_to_numpy=True)
    
    # ============= 4) SAVE EMBEDDINGS =============
    # We'll store them in a new column "embedding"
    df_judges["embedding"] = list(judge_embeddings)
    
    # Save to CSV (embedding will appear as a Python list string)
    df_judges.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved judge embeddings to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
