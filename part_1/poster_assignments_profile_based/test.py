import os

def find_csv_file(file_name):
    current_directory = os.getcwd()
    print("Current Working Directory:", current_directory)
    
    # You might want to adjust this to search in specific subdirectories
    for root, dirs, files in os.walk(current_directory):
        if file_name in files:
            return os.path.join(root, file_name)
    
    return None

csv_file_path = find_csv_file('similarity_scores.csv')
if csv_file_path:
    print("CSV File found at:", csv_file_path)
else:
    print("CSV file not found.")
