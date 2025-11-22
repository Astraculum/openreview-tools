import argparse
from src.acceptFromlowScore import find_rebuttal_examples

def main():
    parser = argparse.ArgumentParser(description="Find controversial accepted papers with successful rebuttals.")
    parser.add_argument('--year', type=str, default='2025', help='Conference year (e.g., 2025)')
    parser.add_argument('--conference', type=str, default='ICLR', help='Conference name (e.g., ICLR)')
    parser.add_argument('--keywords', type=str, nargs='+', default=['diffusion', 'language', 'text', 'transformer', 'llm', 'token'], help='Keywords to filter papers (e.g., diffusion language)')
    
    args = parser.parse_args()
    
    find_rebuttal_examples(args.year, args.conference, args.keywords)

if __name__ == "__main__":
    main()
