import openreview
from tqdm import tqdm
import statistics
import os
import pickle
import json

CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def load_cache(name):
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        # print(f"Loading {name} from cache...")
        with open(path, 'rb') as f:
            return pickle.load(f)
    return None

def save_cache(data, name):
    path = os.path.join(CACHE_DIR, name)
    # print(f"Saving {name} to cache...")
    with open(path, 'wb') as f:
        pickle.dump(data, f)

def analyze_scores():
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
    
    print("Loading submissions...")
    submissions = load_cache('submissions.pkl')
    if not submissions:
        print("No submissions found in cache. Please run acceptFromlowScore.py first or fetch them.")
        return

    # Filter for accepted papers
    accepted_papers = []
    for note in submissions:
        venue_id = note.content.get('venueid', {}).get('value', '')
        if venue_id == 'ICLR.cc/2025/Conference':
            accepted_papers.append(note)
            
    print(f"Found {len(accepted_papers)} accepted papers.")
    
    # We will analyze a subset to demonstrate
    sample_papers = accepted_papers[:10]
    
    for note in sample_papers:
        print(f"\nPaper: {note.content.get('title', {}).get('value', '')} ({note.id})")
        
        # Fetch all notes in forum
        forum_notes = client.get_notes(forum=note.id)
        
        reviews = []
        meta_review = None
        decision = None
        
        for n in forum_notes:
            invitations = getattr(n, 'invitations', [])
            if isinstance(invitations, str): invitations = [invitations]
            
            if any('Official_Review' in i for i in invitations):
                reviews.append(n)
            elif any('Meta_Review' in i for i in invitations):
                meta_review = n
            elif any('Decision' in i for i in invitations):
                decision = n
                
        # Analyze Reviews
        print(f"  Found {len(reviews)} reviews.")
        
        initial_scores = []
        final_scores = []
        
        for review in reviews:
            rating_val = review.content.get('rating', {}).get('value', '')
            current_score = None
            if isinstance(rating_val, int):
                current_score = rating_val
            elif isinstance(rating_val, str) and rating_val:
                try:
                    current_score = int(rating_val.split(':')[0])
                except:
                    pass
                
            final_scores.append(current_score)
            
            # Check for edits to find initial score
            initial_score = current_score # Default to current
            
            try:
                edits = client.get_note_edits(note_id=review.id)
                # Sort edits by date descending (latest first)
                edits.sort(key=lambda x: x.cdate, reverse=True)
                
                has_rating_change = False
                for edit in edits:
                    if edit.content and 'rating' in edit.content:
                        has_rating_change = True
                        # The edit contains the NEW value.
                        # So this edit set the rating to edit.content['rating'].
                        # This should match the current rating if it's the latest edit.
                        pass
                
                if has_rating_change:
                    # We know the score changed.
                    # Since we can't get the original, we'll mark it.
                    initial_score = "Changed"
                    
            except Exception as e:
                # print(f"    Error checking edits: {e}")
                pass
            
            print(f"    Review {review.id}: Final={current_score}, Initial={initial_score}")
            
        # Analyze Meta Review
        if meta_review:
            rec = meta_review.content.get('recommendation', {}).get('value', '')
            print(f"  Meta Review Recommendation: {rec}")
            
        # Analyze Decision
        if decision:
            dec = decision.content.get('decision', {}).get('value', '')
            print(f"  Decision: {dec}")

if __name__ == "__main__":
    analyze_scores()
