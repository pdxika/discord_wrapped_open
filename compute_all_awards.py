#!/usr/bin/env python3
"""
Compute ALL Discord Wrapped 2025 Awards

Awards to compute:
1. Aproposter - most random unrelated responses/topics
2. Most likely to do 9/11
3. Most likely to bring up 9/11
4. Most Gen Z (already computed)
5. Most Boomer (already computed)
6. Katamari Damacy - person whose posts brought most people into conversation
7. Bunny Lebowski - most nihilistic (already computed)
8. Breck Garrett - toxic positivity (already computed)
9. 2001: A Space Odyscord - person who aged into a fetus (?)
10. Phoebe Bridgers - emotional motion sickness (already computed)
11. HER award - digital crossing into real life
12. Taylor Swift - easter eggs (hints way before reveals)
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from config import get_username_map

USERNAME_MAP = get_username_map()


def load_messages(filepath):
    """Load messages from Discord export JSON."""
    print(f"Loading {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    messages = data.get('messages', [])
    print(f"Loaded {len(messages):,} messages\n")
    return messages


def compute_aproposter(messages):
    """Award for most random unrelated responses/topics."""
    print("Computing Aproposter award (most random unrelated responses)...")

    # For each author, find how often their messages are unrelated to previous message
    # We'll use message references (replies) as proxy - messages WITHOUT refs are potentially random

    author_stats = defaultdict(lambda: {'total': 0, 'unreferenced': 0, 'topic_switches': 0})

    prev_msg = None
    for msg in messages:
        author = msg.get('author', '')
        if author not in USERNAME_MAP:
            continue

        has_reference = msg.get('reference') is not None
        author_stats[author]['total'] += 1

        if not has_reference:
            author_stats[author]['unreferenced'] += 1

        # Check if they switched topics (different channel from previous)
        if prev_msg and prev_msg.get('author') != author:
            if prev_msg.get('channel_name') != msg.get('channel_name'):
                author_stats[author]['topic_switches'] += 1

        prev_msg = msg

    # Score = (unreferenced rate + topic switch rate) / 2
    scores = {}
    for author, stats in author_stats.items():
        if stats['total'] > 100:  # Only consider active users
            unreferenced_rate = stats['unreferenced'] / stats['total']
            topic_switch_rate = stats['topic_switches'] / stats['total']
            scores[author] = (unreferenced_rate + topic_switch_rate) / 2

    winner = max(scores.items(), key=lambda x: x[1])
    return {
        'winner': USERNAME_MAP.get(winner[0], winner[0]),
        'score': winner[1],
        'reasoning': f"Had {author_stats[winner[0]]['unreferenced']} non-reply messages and {author_stats[winner[0]]['topic_switches']} topic switches across channels - highest tendency to introduce random new topics"
    }


def compute_katamari_award(messages):
    """Person whose posts consistently brought the most people into conversation."""
    print("Computing Katamari Damacy award (conversation starter)...")

    # For each author, track how many unique people replied to their messages
    author_engagement = defaultdict(lambda: {'posts': 0, 'unique_responders': set(), 'total_responses': 0})

    # Build message ID to author map
    msg_id_to_author = {msg['id']: msg.get('author', '') for msg in messages}

    for msg in messages:
        author = msg.get('author', '')
        if author not in USERNAME_MAP:
            continue

        author_engagement[author]['posts'] += 1

        # Check if this message references someone else's message
        ref = msg.get('reference')
        if ref and isinstance(ref, dict):
            ref_msg_id = ref.get('message_id')
            original_author = msg_id_to_author.get(ref_msg_id)

            if original_author and original_author in USERNAME_MAP and original_author != author:
                author_engagement[original_author]['unique_responders'].add(author)
                author_engagement[original_author]['total_responses'] += 1

    # Score = unique responders per post
    scores = {}
    for author, stats in author_engagement.items():
        if stats['posts'] > 100:
            scores[author] = len(stats['unique_responders']) / stats['posts']

    winner = max(scores.items(), key=lambda x: x[1])
    winner_stats = author_engagement[winner[0]]

    return {
        'winner': USERNAME_MAP.get(winner[0], winner[0]),
        'unique_responders': len(winner_stats['unique_responders']),
        'total_responses': winner_stats['total_responses'],
        'reasoning': f"Their messages attracted responses from {len(winner_stats['unique_responders'])} different people, averaging {scores[winner[0]]:.2f} unique responders per post"
    }


def compute_space_odyscord(messages):
    """Person who aged so much they turned into a fetus - most philosophical/circular."""
    # This is abstract - need LLM for this
    return {
        'winner': "TBD (needs LLM analysis)",
        'reasoning': "Requires analyzing philosophical depth and circular reasoning patterns"
    }


def compute_her_award(messages):
    """Digital crossing into real life - ideas seeded in discord that became real."""
    print("Computing HER award (digital to real life)...")

    # Look for patterns like:
    # - "I'm going to..." followed by later "I did..."
    # - "Should I..." followed by later "I bought/did..."
    # - Mentions of discord wrapped, recommendations that were acted on

    # Sample messages about taking action
    action_patterns = [
        'i did', 'i bought', 'i made', 'i created', 'i started',
        'discord wrapped', 'actually did', 'thanks for', 'took your advice'
    ]

    author_actions = defaultdict(list)

    for msg in messages:
        content = msg.get('content', '').lower()
        author = msg.get('author', '')

        if author not in USERNAME_MAP:
            continue

        if any(pattern in content for pattern in action_patterns):
            author_actions[author].append({
                'content': msg.get('content', '')[:200],
                'timestamp': msg.get('timestamp', '')
            })

    # Count by author
    counts = {author: len(actions) for author, actions in author_actions.items()}
    if counts:
        winner = max(counts.items(), key=lambda x: x[1])
        return {
            'winner': USERNAME_MAP.get(winner[0], winner[0]),
            'count': winner[1],
            'reasoning': f"Most instances of turning discord ideas into reality, with {winner[1]} documented actions",
            'examples': author_actions[winner[0]][:3]  # Top 3 examples
        }

    return {'winner': 'TBD', 'reasoning': 'Needs manual review'}


def compute_taylor_swift_award(messages):
    """Easter eggs - hinted at something way before revealing it."""
    # This requires sophisticated pattern matching - need LLM
    return {
        'winner': "TBD (needs LLM analysis)",
        'reasoning': "Requires analyzing message patterns for foreshadowing and reveals"
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_all_awards.py discord_messages.json")
        sys.exit(1)

    messages = load_messages(sys.argv[1])

    awards = {}

    # Compute each award
    awards['aproposter'] = compute_aproposter(messages)
    awards['katamari'] = compute_katamari_award(messages)
    awards['space_odyscord'] = compute_space_odyscord(messages)
    awards['her_award'] = compute_her_award(messages)
    awards['taylor_swift'] = compute_taylor_swift_award(messages)

    # Save results
    output_path = Path("output/new_awards.json")
    output_path.parent.mkdir(exist_ok=True)

    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_file': sys.argv[1]
        },
        'awards': awards
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print("NEW AWARDS COMPUTED")
    print('='*60)
    for award_name, award_data in awards.items():
        print(f"\n{award_name.upper().replace('_', ' ')}:")
        print(f"  Winner: {award_data.get('winner', 'TBD')}")
        print(f"  {award_data.get('reasoning', '')}")

    print(f"\n\nSaved to {output_path}")


if __name__ == "__main__":
    main()
