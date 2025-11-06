#!/usr/bin/env python3
"""Check timezone conversion for Nov 6, 2025 to see if there's a 1-hour offset issue."""
import pytz
from datetime import datetime, timedelta

# Check what timezone America/Los_Angeles uses on Nov 6, 2025
la_tz = pytz.timezone('America/Los_Angeles')

# Nov 6, 2025 at various times
test_times_utc = [
    datetime(2025, 11, 6, 14, 0, 0, tzinfo=pytz.UTC),  # 14:00 UTC (should be 6:00 AM PST)
    datetime(2025, 11, 6, 14, 38, 50, tzinfo=pytz.UTC),  # 14:38:50 UTC (should be 6:38:50 AM PST)
    datetime(2025, 11, 6, 16, 0, 0, tzinfo=pytz.UTC),  # 16:00 UTC (should be 8:00 AM PST)
]

print("=" * 80)
print("TIMEZONE CONVERSION CHECK - Nov 6, 2025")
print("=" * 80)
print(f"\nTimezone: America/Los_Angeles")
print(f"DST Status: {la_tz.localize(datetime(2025, 11, 6, 12, 0, 0)).dst()}")
print(f"UTC Offset: {la_tz.localize(datetime(2025, 11, 6, 12, 0, 0)).strftime('%z')}")
print("\nUTC → PST/PDT Conversions:")
print("-" * 80)

for utc_time in test_times_utc:
    local_time = utc_time.astimezone(la_tz)
    print(f"UTC:   {utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Local: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z %z')}")
    print(f"       (Date: {local_time.strftime('%A, %B %d')}, Time: {local_time.strftime('%I:%M:%S %p')})")
    print()

# Check DST transition date for 2025
print("=" * 80)
print("DST TRANSITION CHECK")
print("=" * 80)
# DST typically ends first Sunday in November
# Nov 1, 2025 is a Saturday, so Nov 2, 2025 is the first Sunday
dst_end_2025 = datetime(2025, 11, 2, 2, 0, 0)  # 2 AM local time
dst_end_local = la_tz.localize(dst_end_2025)
dst_end_utc = dst_end_local.astimezone(pytz.UTC)

print(f"DST ends: {dst_end_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"         = {dst_end_utc.strftime('%Y-%m-%d %H:%M:%S %Z')} UTC")
print(f"\nOn Nov 6, 2025:")
nov6_noon_local = la_tz.localize(datetime(2025, 11, 6, 12, 0, 0))
print(f"  Timezone: {nov6_noon_local.tzname()}")
print(f"  UTC Offset: {nov6_noon_local.strftime('%z')}")
print(f"  DST Active: {nov6_noon_local.dst() != timedelta(0)}")

# Now check what 14:38:50 UTC converts to
test_utc = datetime(2025, 11, 6, 14, 38, 50, tzinfo=pytz.UTC)
test_local = test_utc.astimezone(la_tz)
print(f"\n" + "=" * 80)
print("YOUR SPECIFIC CASE: 6:38 AM clip")
print("=" * 80)
print(f"If UI shows: 06:38:50 AM")
print(f"UTC time would be: {test_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Local time (PST): {test_local.strftime('%Y-%m-%d %H:%M:%S %Z %z')}")
print(f"                   {test_local.strftime('%A, %B %d at %I:%M:%S %p')}")
print(f"\nIf you see 6:38 AM in UI, the actual UTC time is 14:38:50 UTC")
print(f"Which converts to: {test_local.strftime('%I:%M:%S %p')} {test_local.tzname()}")

