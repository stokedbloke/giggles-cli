import sys
import os
sys.path.insert(0, '.')
os.chdir('/Users/neilsethi/git/giggles-cli/laughter-detector')
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
user_id = 'd223fee9-b279-4dc7-8cd1-188dc09ccdd1'

# Get segments
segs = supabase.table('audio_segments').select('file_path, start_time').eq('user_id', user_id).gte('start_time', '2025-11-03T08:00:00Z').lt('end_time', '2025-11-04T08:00:00Z').execute()

print(f"Found {len(segs.data)} segments in database")
print("\nChecking file existence:")
base_dir = os.getcwd()

for seg in segs.data[:5]:
    fp = seg.get('file_path', '')
    if fp:
        # Try relative path
        rel_path = os.path.join(base_dir, fp.lstrip('/')) if not os.path.isabs(fp) else fp
        exists = os.path.exists(rel_path)
        
        print(f"\n  Path in DB: {fp}")
        print(f"    Full path: {rel_path}")
        print(f"    Exists: {exists}")

# Check clips directory
clips_dir = os.path.join(base_dir, 'uploads', 'clips', user_id)
print(f"\nClips directory: {clips_dir}")
print(f"  Exists: {os.path.exists(clips_dir)}")
if os.path.exists(clips_dir):
    files = [f for f in os.listdir(clips_dir) if f.endswith('.wav')]
    print(f"  WAV files: {len(files)}")
    for f in files[:5]:
        print(f"    - {f}")
