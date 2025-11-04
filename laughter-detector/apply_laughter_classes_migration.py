#!/usr/bin/env python3
"""
Apply the laughter classes migration to add class_id and class_name columns.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def apply_migration():
    """Apply the laughter classes migration."""
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        return False
    
    try:
        # Create Supabase client with service role key
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print("🔧 Applying laughter classes migration...")
        
        # Check current table structure
        print("📋 Checking current table structure...")
        result = supabase.rpc('get_table_columns', {'table_name': 'laughter_detections'}).execute()
        
        if result.data:
            columns = [col['column_name'] for col in result.data]
            print(f"Current columns: {columns}")
            
            if 'class_id' in columns and 'class_name' in columns:
                print("✅ Migration already applied - class_id and class_name columns exist")
                return True
        else:
            print("⚠️ Could not check table structure, proceeding with migration...")
        
        # Apply migration using raw SQL
        migration_sql = """
        ALTER TABLE public.laughter_detections 
        ADD COLUMN IF NOT EXISTS class_id INTEGER,
        ADD COLUMN IF NOT EXISTS class_name TEXT;
        """
        
        print("📝 Adding class_id and class_name columns...")
        result = supabase.rpc('exec_sql', {'sql': migration_sql}).execute()
        
        if result.data:
            print("✅ Migration applied successfully!")
            
            # Add comments
            comment_sql = """
            COMMENT ON COLUMN public.laughter_detections.class_id IS 'YAMNet class ID for the detected laughter type';
            COMMENT ON COLUMN public.laughter_detections.class_name IS 'YAMNet class name for the detected laughter type (e.g., "Laughter", "Giggle", "Belly laugh")';
            """
            
            print("📝 Adding column comments...")
            supabase.rpc('exec_sql', {'sql': comment_sql}).execute()
            
            # Create indexes
            index_sql = """
            CREATE INDEX IF NOT EXISTS idx_laughter_detections_class_id ON public.laughter_detections(class_id);
            CREATE INDEX IF NOT EXISTS idx_laughter_detections_class_name ON public.laughter_detections(class_name);
            """
            
            print("📝 Creating indexes...")
            supabase.rpc('exec_sql', {'sql': index_sql}).execute()
            
            print("✅ Migration completed successfully!")
            return True
            
        else:
            print("❌ Migration failed")
            return False
            
    except Exception as e:
        print(f"❌ Error applying migration: {str(e)}")
        return False

def check_existing_data():
    """Check if existing laughter detections have class information."""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print("\n🔍 Checking existing laughter detections...")
        
        # Get a sample of existing detections
        result = supabase.table("laughter_detections").select("id, class_id, class_name, probability").limit(5).execute()
        
        if result.data:
            print(f"Found {len(result.data)} sample detections:")
            for detection in result.data:
                class_id = detection.get('class_id', 'NULL')
                class_name = detection.get('class_name', 'NULL')
                prob = detection.get('probability', 0)
                print(f"  ID: {detection['id'][:8]}... | Class ID: {class_id} | Class Name: {class_name} | Prob: {prob:.3f}")
        else:
            print("No laughter detections found")
            
    except Exception as e:
        print(f"❌ Error checking data: {str(e)}")

if __name__ == "__main__":
    print("🚀 Laughter Classes Migration Tool")
    print("=" * 40)
    
    success = apply_migration()
    
    if success:
        check_existing_data()
        
        print("\n🎯 Next Steps:")
        print("1. Process some new audio to see different laughter types")
        print("2. Check the day detail view to see class names")
        print("3. You should now see: Laughter, Baby laughter, Giggle, Belly laugh, Chuckle")
    else:
        print("\n❌ Migration failed. Check your Supabase credentials and try again.")
