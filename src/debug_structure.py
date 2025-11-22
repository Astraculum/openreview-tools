import openreview
import json

def debug_structure():
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
    print("Fetching a few submissions...")
    # Fetch just a few notes to inspect structure
    submissions = client.get_notes(
        invitation='ICLR.cc/2025/Conference/-/Submission',
        limit=50,
        details='directReplies'
    )
    
    if not submissions:
        print("No submissions found.")
        return

    print(f"Fetched {len(submissions)} submissions.")
    
    for note in submissions:
        # Look for a submission that has replies
        if not note.details or 'directReplies' not in note.details:
            continue

        replies = note.details['directReplies']
        
        # Check if this submission has reviews
        has_reviews = any('Official_Review' in r['invitations'][0] for r in replies)
        if not has_reviews:
            continue

        print(f"\nSubmission {note.id}: {note.content.get('title', {}).get('value', '')}")
        
        for reply in replies:
            invitations = reply['invitations']
            print(f"  Reply ID: {reply['id']}, Invitations: {invitations}")
            
            if 'ICLR.cc/2025/Conference/-/Official_Review' in invitations[0]:

                print(f"  [Review] {reply['id']}")
                print(f"    Keys: {list(reply['content'].keys())}")
                if 'rating' in reply['content']:
                    print(f"    rating: {reply['content']['rating'].get('value')}")
                if 'final_rating' in reply['content']:
                    print(f"    final_rating: {reply['content']['final_rating'].get('value')}")
            
            elif 'Meta_Review' in invitations[0]:
                print(f"  [Meta_Review] {reply['id']}")
                if 'recommendation' in reply['content']:
                    print(f"    recommendation: {reply['content']['recommendation'].get('value')}")
        
        break

if __name__ == "__main__":
    debug_structure()
