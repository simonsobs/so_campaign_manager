"""
Example showing how to parse time strings into timedelta objects.
"""
from datetime import timedelta
from socm.utils.time_utils import parse_timedelta, format_timedelta

# Examples of parsing time strings
examples = [
    "1d",       # 1 day
    "6h",       # 6 hours
    "30m",      # 30 minutes
    "45s",      # 45 seconds
    "1d12h",    # 1 day and 12 hours
    "2d6h30m",  # 2 days, 6 hours, and 30 minutes
    "90m",      # 90 minutes
    "invalid",  # Invalid format, should return None
]

print("Parsing time strings to timedelta:")
for example in examples:
    result = parse_timedelta(example)
    print(f"  '{example}' -> {result}")

# Example using timedelta in a MissionNullTests-like class
print("\nUsing timedeltas in code:")

# From configuration string
config_duration = "2d"
delta = parse_timedelta(config_duration)
print(f"  Config string '{config_duration}' parsed to {delta}")

# Converting back to string representation
td = timedelta(days=3, hours=5, minutes=15)
formatted = format_timedelta(td)
print(f"  timedelta {td} formatted as '{formatted}'")
