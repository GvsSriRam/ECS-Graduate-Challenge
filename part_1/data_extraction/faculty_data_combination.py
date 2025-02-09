import os
import pandas as pd
import json
import ast
from typing import List, Dict
from pathlib import Path

def load_faculty_data(csv_path: str) -> pd.DataFrame:
    """
    Load faculty data from CSV file.
    
    Args:
        csv_path: Path to the CSV file
    Returns:
        DataFrame containing faculty data
    """
    return pd.read_csv(csv_path)

def parse_interests(interests_str: str) -> List[str]:
    """
    Parse interests string into a list of cleaned interests.
    Handles various string formats including nested lists and quoted strings.
    
    Args:
        interests_str: String containing interests data
    Returns:
        List of cleaned interest strings
    """
    if pd.isna(interests_str):
        return []
        
    try:
        # Try to safely evaluate the string as a literal
        interests = ast.literal_eval(interests_str)
        if isinstance(interests, list):
            # Clean each interest string and remove empty strings
            cleaned = [interest.strip("'\" ") for interest in interests]
            return [i for i in cleaned if i]
    except (ValueError, SyntaxError):
        # If literal_eval fails, try simple string splitting
        pass
    
    # Default to simple string splitting if other methods fail
    return [interest.strip("'\" ") for interest in interests_str.split(',') if interest.strip("'\" ")]

def load_scholarly_data(faculty_name: str, scholarly_dir: str) -> Dict:
    """
    Load scholarly data for a faculty member from JSON file.
    
    Args:
        faculty_name: Name of faculty member
        scholarly_dir: Directory containing scholarly data JSON files
    Returns:
        Dictionary containing scholarly data or None if file doesn't exist
    """
    json_path = Path(scholarly_dir) / f"{faculty_name.lower().replace(' ', '_')}.json"
    print(json_path)
    if not json_path.exists():
        print(f"No scholarly data found for {faculty_name}")
        return None
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def combine_interests(csv_interests: List[str], scholarly_interests: List[str]) -> List[str]:
    """
    Combine and deduplicate interests from both sources.
    
    Args:
        csv_interests: List of interests from CSV
        scholarly_interests: List of interests from scholarly data
    Returns:
        Combined and deduplicated list of interests
    """
    # Remove any empty strings and normalize spacing
    csv_clean = [i.strip().lower() for i in csv_interests if i.strip()]
    scholarly_clean = [i.strip().lower() for i in scholarly_interests if i.strip()]
    
    # If all interests in csv are already in scholarly, return scholarly
    if all(interest in scholarly_clean for interest in csv_clean):
        return scholarly_clean
    
    return list(set(csv_clean + scholarly_clean))

def save_scholarly_data(data: Dict, faculty_name: str, scholarly_dir: str) -> None:
    """
    Save updated scholarly data back to JSON file.
    
    Args:
        data: Dictionary containing scholarly data
        faculty_name: Name of faculty member
        scholarly_dir: Directory to save JSON files
    """
    json_path = Path(scholarly_dir) / f"{faculty_name.lower().replace(' ', '_')}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    # Configuration
    CSV_PATH = 'part_1/data_extraction/profiles_csv/ecs_faculty_profiles.csv'
    SCHOLARLY_DIR = 'faculty_scholarly'
    
    # Load faculty data
    faculty_data = load_faculty_data(CSV_PATH)
    
    # Process each faculty member
    for _, row in faculty_data.iterrows():
        faculty_name = row['name']
        print(f"Processing {faculty_name}")
        
        # Load scholarly data
        scholarly_data = load_scholarly_data(faculty_name, SCHOLARLY_DIR)
        if not scholarly_data:
            continue
        
        # Combine interests
        csv_interests = parse_interests(row['areas_of_expertise'])
        print(f"CSV interests: {csv_interests}")
        scholarly_interests = scholarly_data.get('interests', [])
        print(f"Scholarly interests: {scholarly_interests}")
        combined_interests = combine_interests(csv_interests, scholarly_interests)
        
        # Update and save scholarly data
        scholarly_data['interests'] = combined_interests
        save_scholarly_data(scholarly_data, faculty_name, SCHOLARLY_DIR)
        print(f"Updated interests for {faculty_name}: {combined_interests}")

if __name__ == "__main__":
    main()