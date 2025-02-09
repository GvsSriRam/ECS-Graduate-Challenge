# ECS-Graduate-Challenge
# ECS Graduate Research Day Judge Assignment System

## Overview
This repository implements an automated system for the ECS Graduate Research Day poster competition, handling judge assignments, score collection, and poster ranking. The system is split into three independent modules, each solving a specific aspect of the competition management.

## Repository Structure
```
.
├── LICENSE
├── README.md
├── part_1/                  # Judge-Poster Assignment Module
├── part_2/                  # Score Collection System
├── part_3/                  # Poster Ranking System
├── Sample_input_abstracts.xlsx  # Example poster data
└── Example_list_judges.xlsx     # Example judge data
```

## Modules

### Part 1: Judge-Poster Assignment
- Scrapes the web resources (ECS faculty directory, google scholar, semantic scholar,researchgate, etc.) for identifying the works of each faculty of College of ECS, Syracuse University.
- Matches faculty judges to student posters based on research compatibility
- Handles scheduling and conflict constraints
- Uses NLP techniques for research area matching

### Part 2: Score Collection
- Web-based system for judges to input scores
- Mobile-friendly interface with QR code support
- Real-time score collection and validation

### Part 3: Poster Ranking
- Processes collected scores to rank posters
- Implements fairness-aware ranking algorithms
- Generates final competition results

## Getting Started

Each part has its own virtual environment and requirements. Please refer to the README in each part's directory for specific setup and usage instructions:

- [Part 1 Documentation](part_1/README.md)
- [Part 2 Documentation](part_2/README.md)
- [Part 3 Documentation](part_3/README.md)

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.