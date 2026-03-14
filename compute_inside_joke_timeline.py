#!/usr/bin/env python3
"""
Build inside joke timeline visualization data.

For each inside joke:
- When it originated
- Frequency over time (by month)
- Who uses it most
- Derivative patterns (new topics spawned from it)
- Peak usage periods
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

def load_data():
    """Load messages and existing patterns."""
    with open('discord_messages.json', 'r') as f:
        data = json.load(f)
    messages = data.get('messages', [])

    with open('output/patterns.json', 'r') as f:
        patterns = json.load(f)

    return messages, patterns


def build_joke_timeline(messages, joke_keyword):
    """Build timeline data for a specific inside joke."""
    mentions = []

    for msg in messages:
        content = msg.get('content', '').lower()
        if joke_keyword.lower() in content:
            mentions.append({
                'timestamp': msg.get('timestamp', ''),
                'author': msg.get('author', ''),
                'content': msg.get('content', '')[:200],
                'channel': msg.get('channel_name', '')
            })

    # Sort by timestamp
    mentions.sort(key=lambda x: x['timestamp'])

    if not mentions:
        return None

    # Group by month
    by_month = defaultdict(int)
    for mention in mentions:
        month = mention['timestamp'][:7]  # YYYY-MM
        by_month[month] += 1

    # Find derivatives (messages shortly after that reference the joke)
    derivatives = []
    for i, mention in enumerate(mentions):
        # Look at next few messages in same channel
        mention_time = datetime.fromisoformat(mention['timestamp'].replace('Z', '+00:00'))
        mention_channel = mention['channel']

        # Find messages in same channel within 5 minutes
        for msg in messages:
            if msg.get('channel_name') != mention_channel:
                continue

            msg_time_str = msg.get('timestamp', '')
            if not msg_time_str:
                continue

            try:
                msg_time = datetime.fromisoformat(msg_time_str.replace('Z', '+00:00'))
                time_diff = (msg_time - mention_time).total_seconds()

                # Within 5 minutes after
                if 0 < time_diff < 300:
                    content = msg.get('content', '').lower()
                    # Check if it builds on the joke (mentions it or related keywords)
                    if joke_keyword.lower() in content or len(content) > 20:
                        derivatives.append({
                            'original_mention': mention['content'][:100],
                            'derivative': msg.get('content', '')[:200],
                            'author': msg.get('author', ''),
                            'timestamp': msg.get('timestamp', '')
                        })
                        break  # One derivative per mention
            except:
                continue

    # Get top contributors
    authors = Counter(m['author'] for m in mentions)

    return {
        'keyword': joke_keyword,
        'total_mentions': len(mentions),
        'first_mention': mentions[0]['timestamp'],
        'last_mention': mentions[-1]['timestamp'],
        'peak_month': max(by_month.items(), key=lambda x: x[1])[0],
        'by_month': dict(by_month),
        'top_contributors': dict(authors.most_common(5)),
        'sample_mentions': [
            {
                'author': m['author'],
                'content': m['content'],
                'timestamp': m['timestamp'][:10]
            }
            for m in mentions[:5]
        ],
        'derivatives': derivatives[:10]  # Top 10 derivatives
    }


def main():
    print("Loading data...")
    messages, patterns = load_data()

    inside_jokes = patterns.get('inside_jokes', {})

    print(f"Building timelines for {len(inside_jokes)} inside jokes...\n")

    timelines = {}

    for joke_name, joke_data in inside_jokes.items():
        print(f"Processing: {joke_name}...")

        timeline = build_joke_timeline(messages, joke_name)

        if timeline:
            timelines[joke_name] = timeline
            print(f"  ✓ {timeline['total_mentions']} mentions, "
                  f"peak: {timeline['peak_month']}, "
                  f"{len(timeline['derivatives'])} derivatives\n")

    # Save results
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'note': 'Timeline visualization data for inside jokes'
        },
        'timelines': timelines
    }

    output_path = Path('output/inside_joke_timelines.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print("INSIDE JOKE TIMELINES COMPLETE")
    print('='*60)
    print(f"Created timelines for {len(timelines)} jokes")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
