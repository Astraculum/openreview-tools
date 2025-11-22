import openreview
from tqdm import tqdm
import statistics
import os
import pickle

CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def load_cache(name):
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        print(f"Loading {name} from cache...")
        with open(path, 'rb') as f:
            return pickle.load(f)
    return None

def save_cache(data, name):
    path = os.path.join(CACHE_DIR, name)
    print(f"Saving {name} to cache...")
    with open(path, 'wb') as f:
        pickle.dump(data, f)

def find_rebuttal_examples():
    # 1. Initialize client (connect to API V2)
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
    
    print("Connecting to ICLR 2025 repository...")
    
    # 2. Get all Accepted papers
    # Try to load submissions from cache
    submissions = load_cache('submissions.pkl')
    if not submissions:
        # ICLR 2025 Submissions contain decision info, we need to filter for venueid containing Accept
        submissions = client.get_all_notes(
            invitation='ICLR.cc/2025/Conference/-/Submission',
            details='directReplies' # Get replies to calculate scores
        )
        save_cache(submissions, 'submissions.pkl')
    
    accepted_papers = []
    print(f"Retrieved {len(submissions)} submissions, filtering for accepted papers...")
    
    for note in submissions:
        # Check if venue status is Accept (Accept (Poster/Oral/Spotlight))
        venue = note.content.get('venue', {}).get('value', '')
        venue_id = note.content.get('venueid', {}).get('value', '')
        
        # ICLR 2025 Accepted papers have venueid 'ICLR.cc/2025/Conference' 
        # or venue containing 'poster', 'spotlight', 'oral'
        if venue_id == 'ICLR.cc/2025/Conference' or \
           any(x in venue.lower() for x in ['poster', 'spotlight', 'oral']):
            accepted_papers.append(note)

    print(f"Found {len(accepted_papers)} accepted papers. Filtering for controversial papers in [Diffusion Language Models]...")
    print("-" * 60)

    results = []
    
    # Load reviews cache
    reviews_cache = load_cache('reviews_cache_v2.pkl') or {}
    reviews_cache_updated = False

    keyword_match_count = 0
    score_match_count = 0

    # 3. Iterate through accepted papers, filter by keywords and scores
    for note in tqdm(accepted_papers):
        try:
            # A. Keyword filtering (Domain: Diffusion Language Models/Text Diffusion)
            title = note.content.get('title', {}).get('value', '').lower()
            abstract = note.content.get('abstract', {}).get('value', '').lower()
            text_data = title + " " + abstract
            
            # Must contain diffusion
            if 'diffusion' not in text_data:
                continue
            # Must contain language/text related words
            if not any(kw in text_data for kw in ['language', 'text', 'transformer', 'llm', 'token']):
                continue
            
            keyword_match_count += 1

            # B. Get scores
            # In API V2, reviews usually exist as directReplies, or need to be fetched separately
            # Here we double check reviews
            forum_id = note.id
            
            if forum_id in reviews_cache:
                reviews = reviews_cache[forum_id]
            else:
                # Fetch all notes in forum to find reviews
                # We filter for notes that have 'Official_Review' in their invitation
                all_notes = client.get_notes(forum=forum_id)
                reviews = [n for n in all_notes if any('Official_Review' in inv for inv in n.invitations)]
                reviews_cache[forum_id] = reviews
                reviews_cache_updated = True
            
            if keyword_match_count <= 5:
                print(f"DEBUG: Processing {forum_id}. Reviews count: {len(reviews)}")

            if not reviews:
                continue
                
            initial_scores = []
            final_scores = []

            for review in reviews:
                # ICLR 2025 rating format is usually "8: Strong Accept", extract number before colon
                # Initial Rating
                rating_val = review.content.get('rating', {}).get('value', '')
                rating_str = str(rating_val) if rating_val is not None else ''
                
                # Final Rating (Post-Rebuttal)
                final_rating_val = review.content.get('final_rating', {}).get('value', '')
                final_rating_str = str(final_rating_val) if final_rating_val is not None else ''

                if keyword_match_count <= 5:
                     print(f"DEBUG: id={forum_id} rating='{rating_str}' final='{final_rating_str}'")

                current_initial_score = None
                if rating_str:
                    try:
                        # Handle "8: Strong Accept" or just "8"
                        current_initial_score = int(rating_str.split(':')[0])
                        initial_scores.append(current_initial_score)
                    except:
                        pass
                
                if final_rating_str:
                    try:
                        score = int(final_rating_str.split(':')[0])
                        final_scores.append(score)
                    except:
                        pass
                elif current_initial_score is not None:
                    # If no final rating, assume score is unchanged
                    final_scores.append(current_initial_score)
            
            if not initial_scores:
                if keyword_match_count <= 5:
                    print(f"DEBUG: No scores found for {forum_id}")
                continue
                
            avg_initial_score = statistics.mean(initial_scores)
            min_initial_score = min(initial_scores)
            
            avg_final_score = statistics.mean(final_scores) if final_scores else avg_initial_score

            # C. Core filtering criteria: Find "Turnaround" examples
            # Condition 1: Average score below 6 (Borderline, saved by Rebuttal)
            # Condition 2: Although average is okay, there is a very low score (<=4), indicating author successfully rebutted that reviewer
            # We use INITIAL scores to find papers that started low
            is_controversial = avg_initial_score < 6.0 or min_initial_score <= 4
            
            if is_controversial:
                score_match_count += 1
                results.append({
                    'title': note.content.get('title', {}).get('value', ''),
                    'url': f"https://openreview.net/forum?id={forum_id}",
                    'avg_initial': round(avg_initial_score, 2),
                    'avg_final': round(avg_final_score, 2),
                    'initial_scores': sorted(initial_scores),
                    'final_scores': sorted(final_scores),
                    'keywords': 'Diffusion + NLP'
                })
                
        except Exception as e:
            # print(f"Error processing {note.id}: {e}")
            continue

    if reviews_cache_updated:
        save_cache(reviews_cache, 'reviews_cache_v2.pkl')

    print(f"\nKeyword matches: {keyword_match_count}")
    print(f"Score matches: {score_match_count}")

    # 4. Output results, sorted by score from low to high (lower score means harder Rebuttal, higher learning value)
    results.sort(key=lambda x: x['avg_initial'])
    
    print("\n" + "="*60)
    print(f"Filtering complete! Found {len(results)} highly valuable Rebuttal examples:")
    print("="*60 + "\n")
    
    for idx, p in enumerate(results):
        print(f"{idx+1}. [Avg Initial {p['avg_initial']} -> Final {p['avg_final']}]")
        print(f"   Initial Dist: {p['initial_scores']}")
        print(f"   Final Dist:   {p['final_scores']}")
        print(f"   Title: {p['title']}")
        print(f"   Link: {p['url']}")
        print("   Suggestion: Check how the author responded to the low-score reviewer")
        print("-" * 30)


if __name__ == "__main__":
    find_rebuttal_examples()