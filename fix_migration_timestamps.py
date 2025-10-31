"""Fix timestamp defaults in Crown Safe migration for SQLite compatibility."""

file_path = "db/migrations/versions/2025_10_24_add_crown_safe_models.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace all remaining server_default=sa.text("now()") with timestamp_default
old_pattern = 'server_default=sa.text("now()"))'
new_pattern = "server_default=timestamp_default)"

replacements = content.count(old_pattern)
content = content.replace(old_pattern, new_pattern)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ Fixed {replacements} timestamp defaults in migration file")
