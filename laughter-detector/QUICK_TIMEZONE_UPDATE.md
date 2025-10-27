# Quick Timezone Update

For your user (`solutionsethi@gmail.com`), update the timezone to:

```
America/Los_Angeles
```

## Steps in Supabase SQL Editor

1. Click on the `timezone` field in the row for your user
2. Replace `UTC` with: `America/Los_Angeles`
3. Save/commit the change

## Common Timezones (if you need others)

- **Pacific Time (Los Angeles)**: `America/Los_Angeles`
- **Mountain Time (Denver)**: `America/Denver`
- **Central Time (Chicago)**: `America/Chicago`
- **Eastern Time (New York)**: `America/New_York`
- **UTC/London**: `UTC` or `Europe/London`
- **Tokyo**: `Asia/Tokyo`

## Important Notes

- Use IANA timezone names (e.g., `America/Los_Angeles`)
- Do NOT use abbreviations like "PST" or "PDT"
- The system automatically handles DST transitions
- Example: If you're in Pacific Time, use `America/Los_Angeles`

## After Updating

1. Restart your development server
2. Log out and log back in
3. The system will use your local timezone for all timestamps
