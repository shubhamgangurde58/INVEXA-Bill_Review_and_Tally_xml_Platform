from datetime import datetime, timezone


# Return the current time as a timezone-aware UTC datetime.
# Every document builder calls this so all timestamps follow one rule
# and we never mix local time with UTC in the database.
def utc_now():
    return datetime.now(timezone.utc)
