"""Shared constants for search services"""

# Empty query placeholder for when no recall tables exist
# This query is intentionally constructed to always return zero rows.
# It's a raw SQL string that will be wrapped with text() when executed.
EMPTY_QUERY = "SELECT 1 WHERE 1=0"

# Default parameters for empty query
EMPTY_PARAMS = {}

# Default boolean flag for empty query
EMPTY_FLAG = False
