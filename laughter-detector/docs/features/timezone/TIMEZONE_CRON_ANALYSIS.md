# Timezone Handling in Nightly Cron Job

## Current Situation

### How It Works Now:
1. **Single Cron Job** runs at 2:00 AM (or specified time) UTC
2. **Processes All Users** sequentially in the same run
3. **Each User Gets Their "Yesterday"** calculated based on their timezone

### Example Scenario:

**Cron runs at:** 2:00 AM UTC (e.g., Jan 15, 2025 02:00:00 UTC)

**User 1 (PST - UTC-8):**
- Server time: Jan 15, 2025 02:00:00 UTC
- User's local time: Jan 14, 2025 18:00:00 PST (previous day!)
- "Yesterday" for user: Jan 14, 2025 PST
- Process audio from: Jan 14, 2025 00:00:00 PST → Jan 14, 2025 23:59:59 PST
- Converted to UTC: Jan 14, 2025 08:00:00 UTC → Jan 15, 2025 07:59:59 UTC

**User 2 (EST - UTC-5):**
- Server time: Jan 15, 2025 02:00:00 UTC  
- User's local time: Jan 14, 2025 21:00:00 EST (previous day!)
- "Yesterday" for user: Jan 14, 2025 EST
- Process audio from: Jan 14, 2025 00:00:00 EST → Jan 14, 2025 23:59:59 EST
- Converted to UTC: Jan 14, 2025 05:00:00 UTC → Jan 15, 2025 04:59:59 UTC

**User 3 (UTC):**
- Server time: Jan 15, 2025 02:00:00 UTC
- User's local time: Jan 15, 2025 02:00:00 UTC (same!)
- "Yesterday" for user: Jan 14, 2025 UTC
- Process audio from: Jan 14, 2025 00:00:00 UTC → Jan 14, 2025 23:59:59 UTC

## Key Points:

1. **Single Cron Job** - One job processes all users, not separate jobs per user
2. **Timezone-Aware** - Each user's "yesterday" is calculated using their timezone
3. **UTC Storage** - All audio is stored with UTC timestamps (database standard)
4. **Local Display** - UI displays times in user's local timezone

## Potential Issues:

### Issue 1: "Today" vs "Yesterday"
The current `scheduler._process_user_audio()` processes "today" not "yesterday".
For the nightly cron, we need to process "yesterday" for each user.

### Issue 2: Edge Cases
If cron runs at 2 AM UTC and user is in PST:
- PST time is still Jan 14 (18:00 PST)
- So "yesterday" is Jan 14, which is correct

But if cron runs at 2 AM UTC and user is in UTC+9 (Tokyo):
- Tokyo time is Jan 15 11:00 AM
- So "yesterday" would be Jan 14, which is still correct

### Issue 3: What if user is ahead of UTC?
- User in Tokyo (UTC+9) at cron time 2 AM UTC = 11 AM Tokyo time
- "Yesterday" for them is Jan 14 Tokyo time
- This is correct - we want to process the complete previous day

## Solution:

The cron script should:
1. Get current time in UTC
2. For each user, calculate what "yesterday" means in their timezone
3. Process audio for that user's "yesterday" period
4. Convert day boundaries to UTC for Limitless API calls
5. Store everything with UTC timestamps

