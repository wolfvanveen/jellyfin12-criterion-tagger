#!/usr/bin/env python3
"""
Jellyfin Criterion Collection Tagger updated for Jellyfin 12.0

Tags Criterion Collection movies in your Jellyfin library.
Requires: criterion-collection.json (1,669 titles)

Usage: python3 tag-criterion.py

Adjust DB_PATH below if your Jellyfin database is in a different location.
"""

import sqlite3
import json
import re
from difflib import SequenceMatcher

DB_PATH = "jellyfin.db"
CRITERION_JSON = "criterion-collection.json"

def normalize(title):
    title = re.sub(r'^(The|A|An)\s+', '', title, flags=re.IGNORECASE)
    return re.sub(r'[^\w\s]', '', title.lower()).strip()

def similarity(s1, s2):
    return SequenceMatcher(None, s1, s2).ratio()

# Load criterion list
with open(CRITERION_JSON) as f:
    criterion = json.load(f)

# Connect to Jellyfin
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get all movies
cursor.execute("""
    SELECT Id, Name, ProductionYear, Tags
    FROM BaseItems
    WHERE Type = 'MediaBrowser.Controller.Entities.Movies.Movie'
""")

matches = []
for item_id, name, year, tags in cursor.fetchall():
    if tags and 'criterion' in tags.lower():
        continue  # Already tagged

    norm = normalize(name)

    # Match against criterion list
    for c in criterion:
        if c['year'] == year and similarity(norm, normalize(c['title'])) >= 0.90:
            matches.append((item_id, name, year, tags or ''))
            break

if not matches:
    print("No new Criterion movies found")
    conn.close()
    exit()

# Show matches
print(f"Found {len(matches)} Criterion movies:\n")
for _, name, year, _ in matches:
    print(f"  • {name} ({year})")

# Confirm and tag
if input(f"\nTag these {len(matches)} movies? (yes/no): ").lower() == 'yes':
    for item_id, name, year, tags in matches:
        new_tags = (tags + '|criterion') if tags else 'criterion'
        cursor.execute("UPDATE BaseItems SET Tags = ? WHERE Id = ?", (new_tags, item_id))
        print(f"  ✓ {name}")

    conn.commit()
    print(f"\n✓ Tagged {len(matches)} movies with 'criterion'")

conn.close()