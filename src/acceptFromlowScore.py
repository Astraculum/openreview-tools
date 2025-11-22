import openreview
from tqdm import tqdm
import statistics
import os
import pickle
import csv

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

def find_rebuttal_examples(year='2025', conference='ICLR', keywords=None):
    if keywords is None:
        keywords = ['diffusion', 'language', 'text', 'transformer', 'llm', 'token']

    # 1. Initialize client (connect to API V2)
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
    
    print(f"Connecting to {conference} {year} repository...")
    
    # Construct invitation ID
    invitation_id = f'{conference}.cc/{year}/Conference/-/Submission'
    venue_id_match = f'{conference}.cc/{year}/Conference'
    
    # 2. Get all Accepted papers
    # Try to load submissions from cache
    cache_filename = f'submissions_{conference}_{year}.pkl'
    submissions = load_cache(cache_filename)
    if not submissions:
        # Submissions contain decision info, we need to filter for venueid containing Accept
        submissions = client.get_all_notes(
            invitation=invitation_id,
            details='directReplies' # Get replies to calculate scores
        )
        save_cache(submissions, cache_filename)
    
    accepted_papers = []
    print(f"Retrieved {len(submissions)} submissions, filtering for accepted papers...")
    
    for note in submissions:
        # Check if venue status is Accept (Accept (Poster/Oral/Spotlight))
        venue = note.content.get('venue', {}).get('value', '')
        venue_id = note.content.get('venueid', {}).get('value', '')
        
        # Accepted papers have venueid matching the conference or venue containing 'poster', 'spotlight', 'oral'
        if venue_id == venue_id_match or \
           any(x in venue.lower() for x in ['poster', 'spotlight', 'oral']):
            accepted_papers.append(note)

    print(f"Found {len(accepted_papers)} accepted papers. Filtering for controversial papers with keywords: {keywords}...")
    print("-" * 60)

    results = []
    
    # Load reviews cache
    reviews_cache_filename = f'reviews_cache_{conference}_{year}.pkl'
    reviews_cache = load_cache(reviews_cache_filename) or {}
    reviews_cache_updated = False

    keyword_match_count = 0
    score_match_count = 0

    # Keywords indicating a score increase
    positive_keywords = [
        "raised my score", "increase my score", "increasing my score", 
        "raised my rating", "increase my rating", "updated my score", 
        "upgrading my rating", "changed my rating"
    ]

    # 3. Iterate through accepted papers, filter by keywords and scores
    for note in tqdm(accepted_papers):
        try:
            # A. Keyword filtering
            title = note.content.get('title', {}).get('value', '').lower()
            abstract = note.content.get('abstract', {}).get('value', '').lower()
            text_data = title + " " + abstract
            
            # Check if any of the keywords are present
            # For simplicity, let's assume we want at least one match from the list
            # Or if the user provided specific logic. 
            # The original logic was: must contain 'diffusion' AND (language OR text OR ...)
            # Let's generalize: if keywords are provided, at least one must match.
            # If the user wants complex logic, they might need a more complex CLI.
            # For now, let's assume OR logic for the list provided.
            
            # However, the original request was specific to "Diffusion Language Models".
            # Let's try to respect the user's intent. If they pass multiple keywords, maybe they mean AND?
            # But usually CLI args are OR or simple list.
            # Let's stick to: if any keyword is in text_data.
            
            # Wait, the original code had:
            # if 'diffusion' not in text_data: continue
            # if not any(...): continue
            
            # Let's change to: check if ALL provided keywords are present? No that's too strict.
            # Let's check if ANY of the provided keywords are present.
            if not any(kw.lower() in text_data for kw in keywords):
                continue
            
            keyword_match_count += 1


            # B. Get scores and comments
            forum_id = note.id
            
            if forum_id in reviews_cache:
                all_forum_notes = reviews_cache[forum_id]
            else:
                # Fetch all notes in forum (Reviews, Meta Reviews, Comments)
                all_forum_notes = client.get_notes(forum=forum_id)
                reviews_cache[forum_id] = all_forum_notes
                reviews_cache_updated = True
            
            # Extract Reviews and Meta Reviews
            reviews = [n for n in all_forum_notes if any('Official_Review' in inv for inv in n.invitations)]
            meta_reviews = [n for n in all_forum_notes if any('Meta_Review' in inv for inv in n.invitations)]
            
            if keyword_match_count <= 5:
                print(f"DEBUG: Processing {forum_id}. Notes: {len(all_forum_notes)}, Reviews: {len(reviews)}")

            if not reviews:
                continue
                
            current_scores = []
            for review in reviews:
                # In OpenReview, the 'rating' field in the Review Note is typically overwritten 
                # when a reviewer updates their score. Thus, this is the Current/Final score.
                rating_val = review.content.get('rating', {}).get('value', '')
                rating_str = str(rating_val) if rating_val is not None else ''
                
                if rating_str:
                    try:
                        score = int(rating_str.split(':')[0])
                        current_scores.append(score)
                    except:
                        pass
            
            if not current_scores:
                continue
                
            avg_score = statistics.mean(current_scores)
            min_score = min(current_scores)
            
            # C. Check for "Raised Score" evidence in discussion threads
            evidence = []
            for reply in all_forum_notes:
                # Check content for keywords. 
                # We check all text fields in content to be safe (comment, review, etc.)
                content_values = []
                for v in reply.content.values():
                    if isinstance(v, dict) and 'value' in v:
                        content_values.append(str(v['value']))
                    elif isinstance(v, str):
                        content_values.append(v)
                
                content_text = " ".join(content_values).lower()
                
                for kw in positive_keywords:
                    if kw in content_text:
                        # Found evidence!
                        # Extract a snippet around the keyword
                        idx = content_text.find(kw)
                        start = max(0, idx - 50)
                        end = min(len(content_text), idx + 150)
                        snippet = content_text[start:end].replace('\n', ' ')
                        evidence.append(f"...{snippet}...")
                        break

            # D. Filtering criteria
            # 1. Explicit evidence of score raise (Turnaround)
            # 2. Low average score (< 6) but accepted (Borderline/Saved)
            # 3. Very low minimum score (<= 3) but accepted (Controversial)
            
            has_turnaround_evidence = len(evidence) > 0
            is_borderline = avg_score < 6.0
            is_controversial = min_score <= 3
            
            if has_turnaround_evidence or is_borderline or is_controversial:
                score_match_count += 1
                
                # Get Meta Review Info
                meta_recommendation = "N/A"
                meta_confidence = "N/A"
                if meta_reviews:
                    mr = meta_reviews[0]
                    meta_recommendation = mr.content.get('recommendation', {}).get('value', 'N/A')
                    meta_confidence = mr.content.get('confidence', {}).get('value', 'N/A')

                results.append({
                    'title': note.content.get('title', {}).get('value', ''),
                    'url': f"https://openreview.net/forum?id={forum_id}",
                    'avg_score': round(avg_score, 2),
                    'scores': sorted(current_scores),
                    'meta_recommendation': meta_recommendation,
                    'meta_confidence': meta_confidence,
                    'evidence': evidence,
                    'type': 'Turnaround' if has_turnaround_evidence else 'Borderline/Controversial'
                })

                
        except Exception as e:
            # print(f"Error processing {note.id}: {e}")
            continue

    if reviews_cache_updated:
        save_cache(reviews_cache, 'reviews_cache_v4.pkl')

    print(f"\nKeyword matches: {keyword_match_count}")
    print(f"Score matches: {score_match_count}")

    # 4. Output results, sorted by number of raised scores (descending), then by score (ascending)
    results.sort(key=lambda x: (-len(x['evidence']), x['avg_score']))
    
    print("\n" + "="*60)
    print(f"Filtering complete! Found {len(results)} highly valuable Rebuttal examples.")
    print(f"Saving results to rebuttal_candidates.csv")
    print("="*60 + "\n")
    
    with open('rebuttal_candidates.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Title', 'URL', 'Avg Score', 'Scores', 'Raise Count', 'Type', 'Meta Recommendation', 'Meta Confidence', 'Evidence']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for p in results:
            writer.writerow({
                'Title': p['title'],
                'URL': p['url'],
                'Avg Score': p['avg_score'],
                'Scores': str(p['scores']),
                'Raise Count': len(p['evidence']),
                'Type': p['type'],
                'Meta Recommendation': p['meta_recommendation'],
                'Meta Confidence': p['meta_confidence'],
                'Evidence': " || ".join(p['evidence'])
            })
            
    print("Done! Check rebuttal_candidates.csv")

if __name__ == "__main__":
    find_rebuttal_examples()


if __name__ == "__main__":
    find_rebuttal_examples()