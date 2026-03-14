#!/usr/bin/env python3
"""
Compute Bechdel Test Stats for Discord Wrapped

Bechdel test: How often were two women talking to each other NOT about men?

For Discord, we'll define this as:
- Conversation between two women (reply chain)
- Not mentioning any men in the group
- Topic is something other than men/dating
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from config import get_username_map

USERNAME_MAP = get_username_map()

# Women in the server
WOMEN = []  # TODO: Add usernames of women in your server for the Bechdel test
WOMEN_DISPLAY = {u: USERNAME_MAP[u] for u in WOMEN}

# Men in the server (for detecting mentions)
MEN = [u for u in USERNAME_MAP.keys() if u not in WOMEN]
MEN_NAMES = [USERNAME_MAP[u].lower() for u in MEN]
MEN_USERNAMES = [u.lower() for u in MEN]


def load_messages(filepath):
    """Load messages from Discord export JSON."""
    print(f"Loading {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    messages = data.get('messages', [])
    print(f"Loaded {len(messages):,} messages\n")
    return messages


def mentions_men(content):
    """Check if message content mentions men."""
    content_lower = content.lower()

    # Check for male usernames or display names
    if any(name in content_lower for name in MEN_NAMES):
        return True
    if any(username in content_lower for username in MEN_USERNAMES):
        return True

    # Check for gendered terms
    gendered_terms = [
        'boyfriend', 'husband', 'guy', 'guys', 'man', 'men', 'male',
        'he ', 'him ', 'his ', "he's", "he'd"
    ]

    if any(term in content_lower for term in gendered_terms):
        return True

    return False


def compute_bechdel_stats(messages):
    """Compute Bechdel test statistics."""
    print("Computing Bechdel test stats...")

    # Build message ID map
    msg_map = {msg['id']: msg for msg in messages}

    # Track conversations between women
    woman_to_woman_convos = []
    woman_to_woman_about_men = []
    woman_to_woman_not_about_men = []

    for msg in messages:
        author = msg.get('author', '')

        # Only look at messages from women
        if author not in WOMEN:
            continue

        # Check if this is a reply
        ref = msg.get('reference')
        if not ref or not isinstance(ref, dict):
            continue

        ref_msg_id = ref.get('message_id')
        ref_msg = msg_map.get(ref_msg_id)

        if not ref_msg:
            continue

        ref_author = ref_msg.get('author', '')

        # Check if replying to another woman
        if ref_author not in WOMEN:
            continue

        # Don't count self-replies
        if ref_author == author:
            continue

        # This is a woman-to-woman conversation!
        convo_data = {
            'from': USERNAME_MAP.get(author, author),
            'to': USERNAME_MAP.get(ref_author, ref_author),
            'message': msg.get('content', '')[:200],
            'timestamp': msg.get('timestamp', ''),
            'about_men': False
        }

        woman_to_woman_convos.append(convo_data)

        # Check if it mentions men
        if mentions_men(msg.get('content', '')) or mentions_men(ref_msg.get('content', '')):
            convo_data['about_men'] = True
            woman_to_woman_about_men.append(convo_data)
        else:
            woman_to_woman_not_about_men.append(convo_data)

    # Calculate percentages
    total_convos = len(woman_to_woman_convos)
    about_men_count = len(woman_to_woman_about_men)
    not_about_men_count = len(woman_to_woman_not_about_men)

    bechdel_pass_rate = (not_about_men_count / total_convos * 100) if total_convos > 0 else 0

    # Break down by pair
    pair_stats = defaultdict(lambda: {'total': 0, 'about_men': 0, 'not_about_men': 0})

    for convo in woman_to_woman_convos:
        pair = tuple(sorted([convo['from'], convo['to']]))
        pair_stats[pair]['total'] += 1

        if convo['about_men']:
            pair_stats[pair]['about_men'] += 1
        else:
            pair_stats[pair]['not_about_men'] += 1

    return {
        'total_woman_to_woman_conversations': total_convos,
        'about_men': about_men_count,
        'not_about_men': not_about_men_count,
        'bechdel_pass_rate': bechdel_pass_rate,
        'pair_breakdown': {
            f"{pair[0]}-{pair[1]}": {
                'total': stats['total'],
                'about_men': stats['about_men'],
                'not_about_men': stats['not_about_men'],
                'pass_rate': (stats['not_about_men'] / stats['total'] * 100) if stats['total'] > 0 else 0
            }
            for pair, stats in pair_stats.items()
        },
        'sample_passing_conversations': [
            {
                'from': c['from'],
                'to': c['to'],
                'message': c['message'],
                'timestamp': c['timestamp'][:10]
            }
            for c in woman_to_woman_not_about_men[:5]
        ]
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_bechdel_test.py discord_messages.json")
        sys.exit(1)

    messages = load_messages(sys.argv[1])

    stats = compute_bechdel_stats(messages)

    # Save results
    output_path = Path("output/bechdel_test.json")
    output_path.parent.mkdir(exist_ok=True)

    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_file': sys.argv[1],
            'women_analyzed': list(WOMEN_DISPLAY.values())
        },
        'stats': stats
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print("BECHDEL TEST RESULTS")
    print('='*60)
    print(f"Total woman-to-woman conversations: {stats['total_woman_to_woman_conversations']}")
    print(f"About men: {stats['about_men']} ({stats['about_men']/stats['total_woman_to_woman_conversations']*100:.1f}%)")
    print(f"NOT about men: {stats['not_about_men']} ({stats['bechdel_pass_rate']:.1f}%)")
    print(f"\nBECHDEL PASS RATE: {stats['bechdel_pass_rate']:.1f}%")

    print(f"\n\nPair breakdown:")
    for pair, pair_stats in stats['pair_breakdown'].items():
        print(f"  {pair}: {pair_stats['pass_rate']:.1f}% pass rate ({pair_stats['not_about_men']}/{pair_stats['total']})")

    print(f"\n\nSaved to {output_path}")


if __name__ == "__main__":
    main()
