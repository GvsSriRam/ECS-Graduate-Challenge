import numpy as np
import pandas as pd
from pulp import *
import json

class PosterAssignmentSystem:
    def __init__(self):
        self.posters_df = None
        self.judges_df = None
        self.similarity_matrix = None
        
    def load_data(self, posters_file, judges_file, similarity_matrix_file):
        """Load input data"""
        # Load posters data
        self.posters_df = pd.read_excel(posters_file)
        self.posters_df = self.posters_df.dropna(subset=['Title', 'Abstract'])
        
        # Load judges data
        self.judges_df = pd.read_excel(judges_file)
        
        # Load and trim similarity matrix
        full_similarity_matrix = pd.read_csv(similarity_matrix_file)
        self.similarity_matrix = full_similarity_matrix.iloc[:len(self.posters_df), :len(self.judges_df)]
        
        print(f"Processing {len(self.posters_df)} posters and {len(self.judges_df)} judges")
    
    def create_optimization_model(self):
        """Create and solve the optimization model"""
        num_posters = len(self.posters_df)
        num_judges = len(self.judges_df)
        
        # Create optimization problem
        prob = LpProblem("Poster_Assignment", LpMaximize)
        
        # Decision variables
        x = LpVariable.dicts("assign",
                           ((i, j) for i in range(num_posters) 
                            for j in range(num_judges)),
                           cat='Binary')
        
        # Objective: Maximize total similarity score
        prob += lpSum(self.similarity_matrix.iloc[i, j] * x[i,j] 
                     for i in range(num_posters) 
                     for j in range(num_judges))
        
        # Constraints
        # Each poster must have exactly 2 judges
        for i in range(num_posters):
            prob += lpSum(x[i,j] for j in range(num_judges)) == 2
        
        # Each judge can review at most 6 posters
        for j in range(num_judges):
            prob += lpSum(x[i,j] for i in range(num_posters)) <= 6
        
        # Advisor-advisee constraint
        for i in range(num_posters):
            advisor = str(self.posters_df.iloc[i].get('Advisor First', ''))
            if advisor:
                for j in range(num_judges):
                    judge_name = str(self.judges_df.iloc[j].get('Judge FirstName', ''))
                    if advisor.lower().strip() == judge_name.lower().strip():
                        prob += x[i,j] == 0
        
        # Solve
        prob.solve()
        return prob, x

    def convert_to_json_serializable(self, obj):
        """Convert numpy/pandas types to Python native types"""
        if isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif pd.isna(obj):
            return None
        return obj

    def save_multiple_formats(self, df, base_filename, sheet_name=None):
        """Save a DataFrame in multiple formats"""
        # Save as Excel
        if sheet_name:
            with pd.ExcelWriter(f"{base_filename}.xlsx", engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            df.to_excel(f"{base_filename}.xlsx", index=False)
        
        # Save as CSV
        df.to_csv(f"{base_filename}.csv", index=False)
        
        # Save as JSON
        json_data = df.apply(lambda x: x.map(self.convert_to_json_serializable) 
                           if x.dtype.kind in 'iuf' else x).to_dict('records')
        with open(f"{base_filename}.json", 'w') as f:
            json.dump(json_data, f, indent=2)
    
    def save_assignments(self, prob, x, output_prefix):
        """Save assignments in all formats"""
        if LpStatus[prob.status] != 'Optimal':
            print("No optimal solution found")
            return
            
        num_posters = len(self.posters_df)
        num_judges = len(self.judges_df)
        
        # 1. Extended poster file with judge assignments
        poster_assignments = []
        for i in range(num_posters):
            assigned_judges = []
            for j in range(num_judges):
                if value(x[i,j]) == 1:
                    assigned_judges.append(j + 1)
            
            row = self.posters_df.iloc[i].to_dict()
            row['judge-1'] = assigned_judges[0] if len(assigned_judges) > 0 else None
            row['judge-2'] = assigned_judges[1] if len(assigned_judges) > 1 else None
            poster_assignments.append(row)
        
        extended_posters_df = pd.DataFrame(poster_assignments)
        self.save_multiple_formats(
            extended_posters_df, 
            f"{output_prefix}_extended_posters",
            "Poster Assignments"
        )
        
        # 2. Extended judge file with poster assignments
        judge_assignments = []
        for j in range(num_judges):
            assigned_posters = []
            for i in range(num_posters):
                if value(x[i,j]) == 1:
                    assigned_posters.append(i + 1)
            
            row = self.judges_df.iloc[j].to_dict()
            # Fill up to 6 poster columns
            for p in range(6):
                row[f'poster-{p+1}'] = assigned_posters[p] if p < len(assigned_posters) else None
            judge_assignments.append(row)
        
        extended_judges_df = pd.DataFrame(judge_assignments)
        self.save_multiple_formats(
            extended_judges_df, 
            f"{output_prefix}_extended_judges",
            "Judge Assignments"
        )
        
        # 3. Binary assignment matrix
        binary_matrix = np.zeros((num_posters, num_judges))
        for i in range(num_posters):
            for j in range(num_judges):
                binary_matrix[i,j] = 1 if value(x[i,j]) == 1 else 0
        
        binary_df = pd.DataFrame(
            binary_matrix,
            index=[f"Poster-{i+1}" for i in range(num_posters)],
            columns=[f"Judge-{j+1}" for j in range(num_judges)]
        )
        self.save_multiple_formats(
            binary_df.reset_index(), 
            f"{output_prefix}_binary_matrix",
            "Assignment Matrix"
        )
        
        # 4. Summary statistics
        stats = {
            'total_posters': num_posters,
            'total_judges': num_judges,
            'assignments_per_poster': 2,
            'max_posters_per_judge': 6,
            'actual_assignments': int(binary_matrix.sum()),
            'average_similarity_score': float(
                sum(self.similarity_matrix.iloc[i,j] * binary_matrix[i,j]
                    for i in range(num_posters)
                    for j in range(num_judges)) / binary_matrix.sum()
            )
        }
        
        stats_df = pd.DataFrame([stats])
        self.save_multiple_formats(
            stats_df,
            f"{output_prefix}_statistics",
            "Statistics"
        )
        
        print(f"\nFiles created with prefix '{output_prefix}':")
        print("1. Extended posters (xlsx, csv, json)")
        print("2. Extended judges (xlsx, csv, json)")
        print("3. Binary matrix (xlsx, csv, json)")
        print("4. Statistics (xlsx, csv, json)")

def main():
    system = PosterAssignmentSystem()
    
    try:
        # Load data
        system.load_data(
            'Sample_input_abstracts.xlsx',
            'Example_list_judges.xlsx',
            'similarity_scores.csv'
        )
        
        # Create and solve optimization model
        prob, x = system.create_optimization_model()
        
        # Save assignments in all formats
        system.save_assignments(prob, x, 'assignments')
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()