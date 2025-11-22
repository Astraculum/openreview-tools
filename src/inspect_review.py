import openreview
import json
import os
import pickle

CACHE_DIR = 'cache'

def load_cache(name):
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        print(f"Loading {name} from cache...")
        with open(path, 'rb') as f:
            return pickle.load(f)
    return None

def inspect_review():
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
    
    print("Fetching one accepted submission...")
    submissions = load_cache('submissions.pkl')
    if not submissions:
        print("No submissions in cache.")
        return
    
    target_note = None
    for note in submissions:
        venue_id = note.content.get('venueid', {}).get('value', '')
        if venue_id == 'ICLR.cc/2025/Conference':
            target_note = note
            break
            
    if not target_note:
        print("No accepted paper found.")
        return

    print(f"Inspecting paper: {target_note.id}")
    
    reviews = client.get_notes(forum=target_note.id, invitation='ICLR.cc/2025/Conference/-/Official_Review')
    print(f"Found {len(reviews)} reviews.")
    
    if reviews:
        review = reviews[0]
        print(f"Review ID: {review.id}")
        
        # Check for process logs
        print("\n--- Checking Process Logs ---")
        try:
            logs = client.get_process_logs(id=review.id)
            print(f"Found {len(logs)} logs.")
            for log in logs:
                print(f"Log ID: {log.id}, Status: {log.status}")
        except Exception as e:
            print(f"get_process_logs failed: {e}")

if __name__ == "__main__":
    inspect_review()
