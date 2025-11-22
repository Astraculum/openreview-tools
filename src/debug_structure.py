import openreview
import json

def debug_structure():
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
    print("Fetching a few submissions...")
    # Fetch just a few notes to inspect structure
    submissions = client.get_notes(
        invitation='ICLR.cc/2025/Conference/-/Submission',
        limit=200,
        details='directReplies'
    )
    
    if not submissions:
        print("No submissions found.")
        return

    print(f"Fetched {len(submissions)} submissions.")
    
    venue_ids = set()
    venues = set()
    
    for note in submissions:
        v_id = note.content.get('venueid', {}).get('value', 'N/A')
        v = note.content.get('venue', {}).get('value', 'N/A')
        venue_ids.add(v_id)
        venues.add(v)
        
    print("\nUnique Venue IDs:")
    for v in venue_ids:
        print(v)
        
    print("\nUnique Venues:")
    for v in venues:
        print(v)

if __name__ == "__main__":
    debug_structure()
