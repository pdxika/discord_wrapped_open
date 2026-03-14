"""
Discord Wrapped 2025 - Pattern Matching Analysis
Extracts patterns, inside jokes, callbacks, locations, and topic shifts.
No LLM required - pure text analysis.

Usage:
    python compute_patterns.py discord_messages.json
"""

import json
import sys
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from config import get_username_map, get_inside_jokes


# === CONFIGURATION ===

USERNAME_MAP = get_username_map()

# Keywords to track
INSIDE_JOKE_KEYWORDS = get_inside_jokes()

# Common US cities and places for map extraction
# We'll use a simple keyword list - can expand this
KNOWN_LOCATIONS = {
    'NYC': {'lat': 40.7128, 'lon': -74.0060, 'name': 'New York City'},
    'New York': {'lat': 40.7128, 'lon': -74.0060, 'name': 'New York City'},
    'Manhattan': {'lat': 40.7831, 'lon': -73.9712, 'name': 'Manhattan, NYC'},
    'Brooklyn': {'lat': 40.6782, 'lon': -73.9442, 'name': 'Brooklyn, NYC'},
    'Chicago': {'lat': 41.8781, 'lon': -87.6298, 'name': 'Chicago'},
    'Dallas': {'lat': 32.7767, 'lon': -96.7970, 'name': 'Dallas'},
    'Baltimore': {'lat': 39.2904, 'lon': -76.6122, 'name': 'Baltimore'},
    'Portland': {'lat': 45.5152, 'lon': -122.6784, 'name': 'Portland'},
    'Houston': {'lat': 29.7604, 'lon': -95.3698, 'name': 'Houston'},
    'San Francisco': {'lat': 37.7749, 'lon': -122.4194, 'name': 'San Francisco'},
    'LA': {'lat': 34.0522, 'lon': -118.2437, 'name': 'Los Angeles'},
    'Los Angeles': {'lat': 34.0522, 'lon': -118.2437, 'name': 'Los Angeles'},
    'Seattle': {'lat': 47.6062, 'lon': -122.3321, 'name': 'Seattle'},
    'Boston': {'lat': 42.3601, 'lon': -71.0589, 'name': 'Boston'},
    'Austin': {'lat': 30.2672, 'lon': -97.7431, 'name': 'Austin'},
    'Denver': {'lat': 39.7392, 'lon': -104.9903, 'name': 'Denver'},
    'Miami': {'lat': 25.7617, 'lon': -80.1918, 'name': 'Miami'},
    'Philadelphia': {'lat': 39.9526, 'lon': -75.1652, 'name': 'Philadelphia'},
    'Philly': {'lat': 39.9526, 'lon': -75.1652, 'name': 'Philadelphia'},
    'DC': {'lat': 38.9072, 'lon': -77.0369, 'name': 'Washington DC'},
    'Washington': {'lat': 38.9072, 'lon': -77.0369, 'name': 'Washington DC'},
}


# === DATA LOADING ===

def load_messages(filepath):
    """Load messages from Discord export JSON."""
    print(f"Loading {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get('messages', [])
    print(f"Loaded {len(messages):,} messages")

    # Parse timestamps
    for msg in messages:
        ts_str = msg['timestamp'].replace('+00:00', '')
        msg['_datetime'] = datetime.fromisoformat(ts_str)

    # Sort by timestamp
    messages.sort(key=lambda m: m['_datetime'])

    return messages


# === PATTERN MATCHING ===

def track_inside_jokes(messages):
    """Track inside jokes and their frequency over time."""
    print("\nTracking inside jokes...")

    joke_tracker = defaultdict(lambda: {
        'total_mentions': 0,
        'by_month': defaultdict(int),
        'by_author': Counter(),
        'first_mention': None,
        'sample_messages': []
    })

    for msg in messages:
        content_lower = msg['content'].lower()
        month = msg['_datetime'].strftime('%Y-%m')

        for keyword in INSIDE_JOKE_KEYWORDS:
            if keyword.lower() in content_lower:
                joke = joke_tracker[keyword]
                joke['total_mentions'] += 1
                joke['by_month'][month] += 1
                joke['by_author'][msg['author']] += 1

                if joke['first_mention'] is None:
                    joke['first_mention'] = msg['timestamp']

                # Keep sample messages (up to 5)
                if len(joke['sample_messages']) < 5:
                    joke['sample_messages'].append({
                        'author': msg['author'],
                        'content': msg['content'][:200],
                        'timestamp': msg['timestamp']
                    })

    # Convert to regular dicts
    result = {}
    for keyword, data in joke_tracker.items():
        if data['total_mentions'] > 0:  # Only include if found
            result[keyword] = {
                'total_mentions': data['total_mentions'],
                'by_month': dict(data['by_month']),
                'by_author': dict(data['by_author']),
                'first_mention': data['first_mention'],
                'sample_messages': data['sample_messages']
            }

    print(f"  Found {len(result)} tracked inside jokes")
    for joke, data in sorted(result.items(), key=lambda x: x[1]['total_mentions'], reverse=True):
        print(f"    '{joke}': {data['total_mentions']} mentions")

    return result


def extract_locations(messages):
    """Extract location mentions for map visualization."""
    print("\nExtracting location mentions...")

    location_mentions = defaultdict(int)
    location_samples = defaultdict(list)

    for msg in messages:
        content = msg['content']

        for location, coords in KNOWN_LOCATIONS.items():
            # Case-insensitive search with word boundaries
            pattern = r'\b' + re.escape(location) + r'\b'
            if re.search(pattern, content, re.IGNORECASE):
                location_mentions[coords['name']] += 1

                # Keep sample mentions
                if len(location_samples[coords['name']]) < 3:
                    location_samples[coords['name']].append({
                        'author': msg['author'],
                        'content': content[:150],
                        'timestamp': msg['timestamp']
                    })

    # Build map data
    map_data = []
    for location_name, count in location_mentions.items():
        # Find coords
        coords = next(
            (v for k, v in KNOWN_LOCATIONS.items() if v['name'] == location_name),
            None
        )
        if coords:
            map_data.append({
                'name': location_name,
                'mentions': count,
                'lat': coords['lat'],
                'lon': coords['lon'],
                'samples': location_samples[location_name]
            })

    # Sort by mentions
    map_data.sort(key=lambda x: x['mentions'], reverse=True)

    print(f"  Found {len(map_data)} locations mentioned")
    for loc in map_data[:5]:
        print(f"    {loc['name']}: {loc['mentions']} mentions")

    return map_data


def detect_callbacks(messages):
    """Detect when old jokes/references get brought back up."""
    print("\nDetecting callbacks...")

    # Track first mention of key phrases
    phrase_first_mention = {}
    callbacks = []

    # Simple approach: look for repeated unique phrases (3+ words)
    # Track phrases that appeared, then find later references

    tracked_phrases = set()
    phrase_counts = Counter()

    # First pass: collect and count phrases
    for msg in messages:
        # Extract potential memorable phrases (in quotes or all caps)
        quotes = re.findall(r'"([^"]{15,50})"', msg['content'])
        caps = re.findall(r'\b[A-Z]{5,}(?:\s+[A-Z]{5,}){1,3}\b', msg['content'])

        for phrase in quotes + caps:
            # Filter out too common phrases
            phrase_counts[phrase.lower()] += 1

            if phrase not in phrase_first_mention:
                phrase_first_mention[phrase] = {
                    'first_seen': msg['timestamp'],
                    'author': msg['author']
                }
                tracked_phrases.add(phrase.lower())

    # Filter: only track phrases that appeared 2-20 times (not too rare, not too common)
    valid_phrases = {p for p, count in phrase_counts.items() if 2 <= count <= 20}

    # Now find callbacks (same phrase 30+ days later)
    for msg in messages:
        content_lower = msg['content'].lower()

        for phrase, data in phrase_first_mention.items():
            # Only check valid phrases (not too common, not too rare)
            if phrase.lower() not in valid_phrases:
                continue

            if phrase.lower() in content_lower:
                first_time = datetime.fromisoformat(data['first_seen'].replace('+00:00', ''))
                this_time = msg['_datetime']

                days_gap = (this_time - first_time).days

                if days_gap >= 30:  # At least 30 days later
                    callbacks.append({
                        'phrase': phrase,
                        'original_author': data['author'],
                        'original_date': data['first_seen'],
                        'callback_author': msg['author'],
                        'callback_date': msg['timestamp'],
                        'days_gap': days_gap
                    })

    # Find longest-running callback
    longest_callback = max(callbacks, key=lambda x: x['days_gap']) if callbacks else None

    # Most repeated callbacks
    callback_frequency = Counter(c['phrase'] for c in callbacks)

    print(f"  Found {len(callbacks)} callbacks")
    print(f"  Longest gap: {longest_callback['days_gap'] if longest_callback else 0} days")
    print(f"  Most repeated: {callback_frequency.most_common(1) if callback_frequency else 'None'}")

    return {
        'total_callbacks': len(callbacks),
        'longest_callback': longest_callback,
        'most_repeated': dict(callback_frequency.most_common(10)),
        'all_callbacks': callbacks[:50]  # Limit to 50 for output size
    }


def detect_topic_pivots(messages):
    """Detect sudden topic changes (apropos award)."""
    print("\nDetecting topic pivots...")

    # This is tricky without NLP, but we can use heuristics:
    # - Look for messages that get no replies in a thread
    # - Followed by a completely different conversation

    pivots = []

    # Build message ID to content map
    msg_map = {m['id']: m for m in messages}

    for i, msg in enumerate(messages[:-5]):  # Need lookahead
        # Check if message has replies
        has_reply = False
        next_messages = messages[i+1:i+6]  # Look at next 5 messages

        for next_msg in next_messages:
            ref = next_msg.get('reference')
            if ref and isinstance(ref, dict) and ref.get('message_id') == msg['id']:
                has_reply = True
                break

        # If no replies, might be a topic pivot
        if not has_reply and len(msg['content']) > 20:
            # Check if next messages are from different authors about different thing
            next_authors = [m['author'] for m in next_messages]
            if len(set(next_authors)) >= 2 and msg['author'] in next_authors:
                # Potential pivot
                pivots.append({
                    'author': msg['author'],
                    'content': msg['content'][:200],
                    'timestamp': msg['timestamp'],
                    'channel': msg.get('channel_name', 'unknown')
                })

    # Count by author
    by_author = Counter(p['author'] for p in pivots)

    print(f"  Found {len(pivots)} potential topic pivots")
    print(f"  Top pivoter: {by_author.most_common(1)[0] if by_author else 'None'}")

    return {
        'total_pivots': len(pivots),
        'by_author': dict(by_author),
        'sample_pivots': pivots[:20]  # Top 20
    }


# === MAIN ===

def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_patterns.py discord_messages.json")
        sys.exit(1)

    filepath = sys.argv[1]

    # Load data
    messages = load_messages(filepath)

    # Run pattern analyses
    inside_jokes = track_inside_jokes(messages)
    locations = extract_locations(messages)
    callbacks = detect_callbacks(messages)
    topic_pivots = detect_topic_pivots(messages)

    # Compile output
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_file': filepath,
            'total_messages_analyzed': len(messages)
        },
        'inside_jokes': inside_jokes,
        'locations': locations,
        'callbacks': callbacks,
        'topic_pivots': topic_pivots
    }

    # Save output
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / 'patterns.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    print("\n" + "="*60)
    print("PATTERN ANALYSIS COMPLETE")
    print("="*60)
    print(f"Inside jokes tracked: {len(inside_jokes)}")
    print(f"Locations found: {len(locations)}")
    print(f"Callbacks detected: {callbacks['total_callbacks']}")
    print(f"Topic pivots: {topic_pivots['total_pivots']}")
    print(f"\nOutput saved: {output_file}")
    print("="*60)


if __name__ == "__main__":
    main()
