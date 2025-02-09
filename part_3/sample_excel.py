import pandas as pd
import numpy as np
np.random.seed(42)  # for reproducibility

def create_scores_file():
    # Create the binary matrix first
    binary_data = {
        'Poster-1': [1,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        'Poster-2': [0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        'Poster-3': [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
        'Poster-4': [0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
        'Poster-5': [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        'Poster-6': [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        'Poster-7': [1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        'Poster-8': [0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    }
    
    # Convert to DataFrame
    df = pd.DataFrame(binary_data).T
    
    # Create column names
    df.columns = [f'Judge-{i+1}' for i in range(40)]
    
    # Replace 1s with random scores (normal distribution around 7)
    scores_df = df.copy()
    for i in range(len(scores_df)):
        for j in range(len(scores_df.columns)):
            if scores_df.iloc[i,j] == 1:
                # Generate score between 1-10, centered around 7
                score = np.clip(round(np.random.normal(7, 1) * 2) / 2, 1, 10)
                scores_df.iloc[i,j] = score
    
    # Save to Excel
    scores_df.to_excel('scores_file.xlsx')
    
    # Print sample info
    print("\nSample file generated with following characteristics:")
    print(f"Number of posters: {len(scores_df)}")
    print(f"Number of judges: {len(scores_df.columns)}")
    print("\nScore distribution:")
    scores = scores_df.values.flatten()
    scores = scores[scores > 0]
    print(pd.Series(scores).value_counts().sort_index())
    print("\nReviews per poster:")
    print(scores_df.astype(bool).sum(axis=1))

# Generate the file
create_scores_file()