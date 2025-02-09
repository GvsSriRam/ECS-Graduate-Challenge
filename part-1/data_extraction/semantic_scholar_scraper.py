import requests
import json
import time
from typing import Dict, List, Optional

class SemanticScholarScraper:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            # Add your API key here if you have one
            # "x-api-key": "YOUR_API_KEY"
        }

    def get_author_data(self, author_name: str) -> Dict:
        """
        Get author data from Semantic Scholar API
        """
        try:
            # Search for author
            print(f"Searching for author: {author_name}")
            search_url = f"{self.base_url}/author/search"
            params = {
                "query": author_name,
                "fields": "name,affiliations,citationCount,hIndex,paperCount,papers.title,papers.year,papers.abstract,papers.venue,papers.citationCount,papers.authors,papers.url"
            }
            
            response = requests.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            authors = response.json().get('data', [])
            if not authors:
                print(f"No authors found for: {author_name}")
                return {}

            # Get the first matching author
            author = authors[0]
            author_id = author.get('authorId')

            # Get detailed author information
            author_url = f"{self.base_url}/author/{author_id}"
            params = {
                "fields": "name,affiliations,citationCount,hIndex,paperCount,papers.title,papers.year,papers.abstract,papers.venue,papers.citationCount,papers.authors,papers.url"
            }

            response = requests.get(author_url, headers=self.headers, params=params)
            response.raise_for_status()
            author_data = response.json()

            # Format the data
            formatted_data = {
                "name": author_data.get('name', ''),
                "affiliation": author_data.get('affiliations', [''])[0] if author_data.get('affiliations') else '',
                "interests": [],  # Semantic Scholar doesn't provide research interests directly
                "citedby": author_data.get('citationCount', 0),
                "h_index": author_data.get('hIndex', 0),
                "i10_index": 0,  # Semantic Scholar doesn't provide i10-index
                "top_primary_author_publications": [],
                "top_secondary_author_publications": []
            }

            # Process publications
            papers = author_data.get('papers', [])
            for paper in papers:
                paper_data = {
                    "title": paper.get('title', ''),
                    "year": paper.get('year', ''),
                    "abstract": paper.get('abstract', ''),
                    "venue": paper.get('venue', ''),
                    "citations": paper.get('citationCount', 0),
                    "authors": [author.get('name', '') for author in paper.get('authors', [])],
                    "url": paper.get('url', '')
                }

                # Check if the author is the primary author
                if paper_data['authors'] and author_data['name'] in paper_data['authors'][0]:
                    formatted_data['top_primary_author_publications'].append(paper_data)
                else:
                    formatted_data['top_secondary_author_publications'].append(paper_data)

            # Sort and limit publications
            formatted_data['top_primary_author_publications'].sort(
                key=lambda x: x['citations'], reverse=True)
            formatted_data['top_secondary_author_publications'].sort(
                key=lambda x: x['citations'], reverse=True)

            formatted_data['top_primary_author_publications'] = \
                formatted_data['top_primary_author_publications'][:3]
            formatted_data['top_secondary_author_publications'] = \
                formatted_data['top_secondary_author_publications'][:3]

            return formatted_data

        except requests.exceptions.RequestException as e:
            print(f"Error making request: {str(e)}")
            print("No author found with name: ", author_name)
            return {}
        except Exception as e:
            print(f"Error processing data: {str(e)}")
            print("No author found with name: ", author_name)
            return {}

    def save_to_json(self, data: Dict, filename: str):
        """Save data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Data successfully saved to {filename}")
        except Exception as e:
            print(f"Error saving to JSON: {str(e)}")

def main():
    # Example usage
    author_name = "Riyad Aboutaha"  # Replace with the author name you want to search
    output_file = "scholar_data.json"
    
    scraper = SemanticScholarScraper()
    author_data = scraper.get_author_data(author_name)
    
    if author_data:
        scraper.save_to_json(author_data, output_file)
    else:
        print("Failed to retrieve author data")

if __name__ == "__main__":
    main()