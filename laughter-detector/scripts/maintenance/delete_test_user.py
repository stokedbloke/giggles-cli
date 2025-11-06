#!/usr/bin/env python3
"""
Delete a test user completely - both from Supabase Auth and the users table.
Usage: python3 delete_test_user.py <email>
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Supabase credentials not found")
    exit(1)

# Use service role key for admin operations
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Get email from command line argument
if len(sys.argv) < 2:
    print("❌ Usage: python3 delete_test_user.py <email>")
    exit(1)

email = sys.argv[1].strip()

# Find user in users table
print(f"🔍 Looking up user: {email}")
result = supabase.table("users").select("id, email").eq("email", email).execute()

if not result.data:
    print(f"❌ User not found in users table: {email}")
    exit(1)

user_id = result.data[0]["id"]
print(f"✅ Found user ID: {user_id}")

# Step 1: Delete from users table (cascading will handle related data)
print(f"\n🗑️  Deleting from users table...")
delete_result = supabase.table("users").delete().eq("id", user_id).execute()
print(f"✅ Deleted from users table")

# Step 2: Delete from Supabase Auth using admin API
print(f"🗑️  Deleting from Supabase Auth...")
from supabase import Client

# Use admin API to delete auth user
try:
    admin_response = supabase.auth.admin.delete_user(user_id)
    print(f"✅ Deleted from Supabase Auth")
except Exception as e:
    print(f"⚠️  Warning: Could not delete from Supabase Auth: {str(e)}")
    print(f"   You may need to delete manually from Supabase Dashboard")

print(f"\n✅ User deletion complete!")
print(f"   User ID: {user_id}")
print(f"   Email: {email}")

