# System to assign judges to research posters based on research area matching and constraints
import numpy as np
import pandas as pd
from pulp import *
import json
import os

class PosterAssignmentSystem:
    def __init__(self):
        # Initialize empty data structures
        self.posters_df = None
        self.judges_df = None
        self.similarity_matrix = None
        
    def load_data(self, posters_file, judges_file, similarity_matrix_file):
        """Load and validate input data"""
        print("\nLoading data files...")
        
        # Load posters data
        self.posters_df = pd.read_excel(posters_file)
        self.posters_df = self.posters_df.dropna(subset=['Title', 'Abstract'])
        print(f"Loaded {len(self.posters_df)} valid posters")
        
        # Load judges data
        self.judges_df = pd.read_excel(judges_file)
        print(f"Loaded {len(self.judges_df)} judges")
        
        # Load similarity matrix
        full_similarity_matrix = pd.read_csv(similarity_matrix_file)
        num_posters = len(self.posters_df)
        num_judges = len(self.judges_df)
        
        # Take required subset of similarity matrix
        self.similarity_matrix = full_similarity_matrix.iloc[:num_posters, :num_judges]
        print(f"Using similarity matrix of shape: {self.similarity_matrix.shape}")
        
        # Print column information
        print("\nPoster DataFrame columns:", self.posters_df.columns.tolist())
        print("Judge DataFrame columns:", self.judges_df.columns.tolist())
    
    def create_optimization_model(self):
        """Create and solve the optimization model"""
        num_posters = len(self.posters_df)
        num_judges = len(self.judges_df)
        
        print(f"\nCreating optimization model for {num_posters} posters and {num_judges} judges")
        
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
        
        print("\nAdding constraints...")
        
        # Constraint 1: Each poster must have exactly 2 judges
        for i in range(num_posters):
            prob += lpSum(x[i,j] for j in range(num_judges)) == 2
            print(f"Poster {i+1} must have exactly 2 judges")
            
        # Constraint 2: Each judge can review at most 6 posters
        for j in range(num_judges):
            prob += lpSum(x[i,j] for i in range(num_posters)) <= 6
            print(f"Judge {j+1} can review at most 6 posters")
            
        # Constraints 3 & 4: Time slot constraints
        for j in range(num_judges):
            judge_hour = self.judges_df.iloc[j].get('Hour available', 
                                                  self.judges_df.iloc[j].get('Hour'))
            
            if pd.notna(judge_hour):
                for i in range(num_posters):
                    poster_number = i + 1
                    is_odd = poster_number % 2 == 1
                    
                    # Hour 1: Only odd-numbered posters
                    if judge_hour == 1:
                        if not is_odd:  # if poster is even
                            prob += x[i,j] == 0
                            print(f"Judge {j+1} (Hour 1 only) cannot judge poster {poster_number} (even - Hour 2)")
                    
                    # Hour 2: Only even-numbered posters
                    elif judge_hour == 2:
                        if is_odd:  # if poster is odd
                            prob += x[i,j] == 0
                            print(f"Judge {j+1} (Hour 2 only) cannot judge poster {poster_number} (odd - Hour 1)")
                    
                    # Both hours available: No additional constraints needed
                    elif judge_hour == "both":
                        continue
                    else:
                        print(f"Warning: Unknown hour value {judge_hour} for judge {j+1}")
        
        # Constraint 5: Advisor-advisee constraint
        for i in range(num_posters):
            advisor = str(self.posters_df.iloc[i].get('Advisor First', ''))
            if advisor:
                for j in range(num_judges):
                    judge_name = str(self.judges_df.iloc[j].get('Judge FirstName', ''))
                    if advisor.lower().strip() == judge_name.lower().strip():
                        prob += x[i,j] == 0
                        print(f"Judge {j+1} cannot judge poster {i+1} (advisor constraint)")
        
        print("\nSolving optimization problem...")
        prob.solve()
        
        # Print assignment information
        if LpStatus[prob.status] == 'Optimal':
            print("\nAssignment Results:")
            for i in range(num_posters):
                poster_number = i + 1
                assigned_judges = []
                for j in range(num_judges):
                    if value(x[i,j]) == 1:
                        judge_hour = self.judges_df.iloc[j].get('Hour available', 
                                                              self.judges_df.iloc[j].get('Hour'))
                        assigned_judges.append(f"Judge {j+1} (Hour {judge_hour})")
                hour = "1st" if poster_number % 2 == 1 else "2nd"
                print(f"Poster {poster_number} ({hour} hour) -> {', '.join(assigned_judges)}")
        
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
        """Save DataFrame in Excel, CSV, and JSON formats"""
        # Create output directory
        os.makedirs('output', exist_ok=True)
        base_path = os.path.join('output', base_filename)
        
        # Save as Excel
        if sheet_name:
            with pd.ExcelWriter(f"{base_path}.xlsx", engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            df.to_excel(f"{base_path}.xlsx", index=False)
        
        # Save as CSV
        df.to_csv(f"{base_path}.csv", index=False)
        
        # Save as JSON
        json_data = df.apply(lambda x: x.map(self.convert_to_json_serializable) 
                           if x.dtype.kind in 'iuf' else x).to_dict('records')
        with open(f"{base_path}.json", 'w') as f:
            json.dump(json_data, f, indent=2)
    
    def generate_email(self, first_name, last_name):
        """Generate email from judge's name (firstinitiallastname@syr.edu)"""
        first_name = ''.join(e for e in first_name if e.isalnum()).lower()
        last_name = ''.join(e for e in last_name if e.isalnum()).lower()
        email = f"{first_name[0]}{last_name}@syr.edu"
        return email
    
    def save_assignments(self, prob, x, output_prefix):
        """Save assignment results in multiple formats"""
        if LpStatus[prob.status] != 'Optimal':
            print("No optimal solution found")
            return
            
        num_posters = len(self.posters_df)
        num_judges = len(self.judges_df)
        
        # 1. Generate extended poster assignments
        poster_assignments = []
        for i in range(num_posters):
            assigned_judges = []
            for j in range(num_judges):
                if value(x[i,j]) == 1:
                    assigned_judges.append(j + 1)
            
            row = self.posters_df.iloc[i].to_dict()
            row['judge-1'] = assigned_judges[0] if len(assigned_judges) > 0 else None
            row['judge-2'] = assigned_judges[1] if len(assigned_judges) > 1 else None
            
            # Add judge hours
            if row['judge-1'] is not None:
                row['judge-1-hour'] = self.judges_df.iloc[row['judge-1']-1].get('Hour available', 
                                                                               self.judges_df.iloc[row['judge-1']-1].get('Hour'))
            if row['judge-2'] is not None:
                row['judge-2-hour'] = self.judges_df.iloc[row['judge-2']-1].get('Hour available', 
                                                                               self.judges_df.iloc[row['judge-2']-1].get('Hour'))
            poster_assignments.append(row)
        
        extended_posters_df = pd.DataFrame(poster_assignments)
        self.save_multiple_formats(
            extended_posters_df, 
            f"{output_prefix}_extended_posters",
            "Poster Assignments"
        )
        
        # 2. Generate extended judge assignments
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
        
        # 3. Generate judge assignments with email
        judge_assignments_with_email = []
        for j in range(num_judges):
            assigned_posters = []
            for i in range(num_posters):
                if value(x[i,j]) == 1:
                    assigned_posters.append(i + 1)
            
            row = self.judges_df.iloc[j].to_dict()
            # Add email address
            first_name = str(row.get('Judge FirstName', ''))
            last_name = str(row.get('Judge LastName', ''))
            row['Email'] = self.generate_email(first_name, last_name)
            
            # Add poster assignments and titles
            for p in range(6):
                row[f'poster-{p+1}'] = assigned_posters[p] if p < len(assigned_posters) else None
                poster_num = row[f'poster-{p+1}']
                if poster_num is not None:
                    row[f'poster-{p+1}-title'] = self.posters_df.iloc[poster_num-1]['Title']
                else:
                    row[f'poster-{p+1}-title'] = None
                    
            judge_assignments_with_email.append(row)
        
        extended_judges_email_df = pd.DataFrame(judge_assignments_with_email)
        self.save_multiple_formats(
            extended_judges_email_df, 
            f"{output_prefix}_extended_judges_with_email",
            "Judge Assignments With Email"
        )
        
        # 4. Generate binary assignment matrix
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
        
        # 5. Generate statistics
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
        
        print(f"\nOutput files created in 'output' directory with prefix '{output_prefix}':")
        print("1. Extended posters (xlsx, csv, json)")
        print("2. Extended judges (xlsx, csv, json)")
        print("3. Extended judges with email (xlsx, csv, json)")
        print("4. Binary matrix (xlsx, csv, json)")
        print("5. Statistics (xlsx, csv, json)")

def main():
    # Initialize and run the assignment system
    system = PosterAssignmentSystem()
    
    try:
        # Load input data
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
        print(f"\nError occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()