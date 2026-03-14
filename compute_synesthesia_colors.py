#!/usr/bin/env python3
"""
Use LLM to extract Andrew's synesthesia color mappings for all group members.
"""

import json
import sys
from pathlib import Path

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("ERROR: anthropic package not installed")
    sys.exit(1)

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


def extract_synesthesia_discussion(messages):
    """Extract all messages related to synesthesia discussion."""

    # Find all synesthesia mentions
    synesthesia_msgs = []
    for msg in messages:
        content = msg.get('content', '').lower()
        if 'synesthesia' in content or 'synesthetic' in content:
            synesthesia_msgs.append(msg)

    # Sort by timestamp
    synesthesia_msgs.sort(key=lambda m: m.get('timestamp', ''))

    return synesthesia_msgs


def analyze_with_llm(client, messages):
    """Use Claude to extract color mappings from synesthesia discussion."""

    # Format messages for LLM
    conversation = []
    for msg in messages:
        author = msg.get('author', 'unknown')
        display_name = USERNAME_MAP.get(author, author)
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')[:10]
        conversation.append(f"[{timestamp}] {display_name}: {content}")

    conversation_text = "\n".join(conversation)

    prompt = f"""Analyze this Discord conversation about synesthesia (seeing people as colors).

Extract all color associations mentioned for server members.

Conversation:
{conversation_text}

Please extract a JSON mapping of person → color for all members mentioned. Format:
{{
  "Person1": "blue",
  "Person2": "dark green",
  "Person3": "red",
  ...
}}

Only include people where a color is explicitly stated. If someone's color isn't mentioned, don't guess."""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    return response.content[0].text


def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_synesthesia_colors.py discord_messages.json")
        sys.exit(1)

    messages = load_messages(sys.argv[1])

    print("Extracting synesthesia discussion...")
    synesthesia_msgs = extract_synesthesia_discussion(messages)
    print(f"Found {len(synesthesia_msgs)} relevant messages\n")

    print("Sample messages:")
    for msg in synesthesia_msgs[:15]:
        author = USERNAME_MAP.get(msg.get('author', ''), msg.get('author', 'unknown'))
        timestamp = msg.get('timestamp', '')[:10]
        content = msg.get('content', '')
        print(f"[{timestamp}] {author}: {content[:150]}")
    print()

    # Use LLM to extract colors
    print("\nAnalyzing with Claude to extract color mappings...")
    client = anthropic.Anthropic()

    color_mappings = analyze_with_llm(client, synesthesia_msgs)

    print("\n" + "="*60)
    print("SYNESTHESIA COLOR MAPPINGS")
    print("="*60)
    print(color_mappings)
    print()

    # Save to file
    output_path = Path("output/synesthesia_colors.json")
    with open(output_path, 'w') as f:
        f.write(color_mappings)

    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
