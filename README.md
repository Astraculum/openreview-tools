# OpenReview Rebuttal Analyzer

This tool helps researchers find "Turnaround" papers in OpenReview conferences (e.g., ICLR, NeurIPS). It identifies papers that likely started with low scores but were accepted after a successful rebuttal, based on:
1.  **Low Current Scores**: Papers with an average score < 6 or a minimum score <= 3.
2.  **Text Mining**: Scanning discussion threads for keywords like "raised my score", "increase my rating", etc.

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install openreview-py tqdm
    ```

## Usage

Run the tool via `main.py` with command-line arguments:

```bash
python main.py --year 2025 --conference ICLR --keywords diffusion language text
```

### Arguments

*   `--year`: Conference year (default: 2025)
*   `--conference`: Conference name (default: ICLR)
*   `--keywords`: List of keywords to filter papers by title/abstract (default: diffusion language text transformer llm token)

## Output

The tool generates a `rebuttal_candidates.csv` file containing:
*   **Title**: Paper title
*   **URL**: Link to the OpenReview forum
*   **Avg Score**: Current average score
*   **Scores**: Distribution of scores
*   **Raise Count**: Number of times a reviewer explicitly mentioned raising their score
*   **Type**: "Turnaround" (explicit evidence found) or "Borderline/Controversial" (low scores but accepted)
*   **Evidence**: Snippets of text where reviewers mentioned raising their score.

## Caching

The tool caches submissions and reviews in the `cache/` directory to speed up subsequent runs. If you want to fetch fresh data, delete the corresponding `.pkl` files in `cache/`.
