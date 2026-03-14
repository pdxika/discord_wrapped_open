"""
Discord Wrapped 2025 - LLM Analysis
Uses Claude to generate personality reads, sentiment-based awards, and messages.
Requires ANTHROPIC_API_KEY environment variable.

Usage:
    python compute_llm_analysis.py discord_messages.json
"""

import json
import sys
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from config import get_username_map, get_llm_model

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("WARNING: anthropic package not installed. Install with: pip install anthropic")


# === CONFIGURATION ===

USERNAME_MAP = get_username_map()


def compute_partner_assignments(person_data):
    """Auto-assign message-writing partners based on conversation data."""
    from collections import Counter
    max_writes = max(2, len(person_data) // 3)
    write_counts = Counter()
    assignments = {}

    for username in person_data:
        top_partners = person_data[username].get('relationships', {}).get('top_reply_targets', [])
        for partner in top_partners:
            partner_user = partner['username']
            if write_counts[partner_user] < max_writes and partner_user != username and partner_user in person_data:
                assignments[username] = partner_user
                write_counts[partner_user] += 1
                break

    return assignments


# === DATA LOADING ===

def load_messages(filepath):
    """Load messages from Discord export JSON."""
    print(f"Loading {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get('messages', [])
    print(f"Loaded {len(messages):,} messages\n")

    return messages


def load_wrapped_data():
    """Load existing wrapped data from previous analyses."""
    output_dir = Path('output')

    # Load group wrapped
    with open(output_dir / 'group_wrapped.json', 'r') as f:
        group_data = json.load(f)

    # Load individual wrapped files
    person_data = {}
    for username in USERNAME_MAP.keys():
        filepath = output_dir / f'wrapped_{username}.json'
        if filepath.exists():
            with open(filepath, 'r') as f:
                person_data[username] = json.load(f)

    return group_data, person_data


# === LLM ANALYSIS ===

def analyze_person_personality(client, messages, username, person_stats):
    """
    Generate personality read for a specific person.

    Args:
        client: Anthropic client
        messages: List of all messages
        username: Discord username
        person_stats: Pre-computed stats for this person

    Returns:
        dict with personality analysis
    """
    display_name = USERNAME_MAP.get(username, username)
    print(f"  Analyzing personality for {display_name}...")

    # Sample their messages (up to 200)
    person_messages = [m for m in messages if m['author'] == username]
    if len(person_messages) > 200:
        person_messages = random.sample(person_messages, 200)

    # Format messages
    message_samples = "\n".join([
        f"[{m.get('channel_name', 'unknown')}] {m['content'][:200]}"
        for m in person_messages
        if m['content']
    ][:100])  # Limit to avoid token limits

    # Build prompt
    prompt = f"""Analyze this Discord user's personality based on their messages.

User: {display_name}
Messages sent: {person_stats['stats']['messages_sent']}
Rank: #{person_stats['stats']['rank']}
Most active: {person_stats['stats']['most_active_weekday']} at {person_stats['stats']['most_active_hour']}:00

Sample messages:
{message_samples}

Provide a personality analysis in JSON format:
{{
    "role": "One clear role this person plays in the server (e.g., 'The Connector', 'The Provocateur', 'The Voice of Reason')",
    "description": "2-3 sentence description of their vibe and communication style",
    "signature_traits": ["3-5 specific personality traits or patterns you notice"],
    "contribution": "How they specifically contribute to the server's dynamic"
}}

Be specific and observational. Use evidence from their messages."""

    try:
        response = client.messages.create(
            model=get_llm_model(),
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON from response
        import re
        response_text = response.content[0].text
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"raw": response_text}

    except Exception as e:
        print(f"    ERROR analyzing {display_name}: {e}")
        return None


def compute_sentiment_awards(client, messages):
    """
    Compute awards that require sentiment analysis.

    Awards:
    - Phoebe Bridgers (emotional swings)
    - Bunny Lebowski (nihilism)
    - Breck Garrett (toxic positivity)
    - Gen Z vs Boomer

    Args:
        client: Anthropic client
        messages: All messages

    Returns:
        dict of awards
    """
    print("\nComputing sentiment-based awards...")

    # Sample messages per person for sentiment analysis
    person_samples = defaultdict(list)
    for msg in messages:
        if len(person_samples[msg['author']]) < 100:
            person_samples[msg['author']].append(msg['content'])

    # Build analysis prompt
    people_text = ""
    for username, samples in person_samples.items():
        display_name = USERNAME_MAP.get(username, username)
        sample_text = "\n".join(samples[:50])
        people_text += f"\n\n=== {display_name} ===\n{sample_text}"

    prompt = f"""Analyze these Discord users and assign awards based on their communication patterns.

Awards to assign:
1. Phoebe Bridgers Award (Emotional Motion Sickness) - Biggest emotional swings, despair to delight
2. Bunny Lebowski Award (Nihilism) - Most nihilistic/cynical person
3. Breck Garrett Award (Toxic Positivity) - Most relentlessly positive, even inappropriately
4. Gen Z Award - Most Gen Z language/references/vibes
5. Boomer Award - Most Boomer language/references/vibes

Messages by person:
{people_text[:8000]}

Return JSON:
{{
    "phoebe_bridgers": {{
        "winner": "Name",
        "reasoning": "Why they won based on message evidence"
    }},
    "bunny_lebowski": {{
        "winner": "Name",
        "reasoning": "Why"
    }},
    "breck_garrett": {{
        "winner": "Name",
        "reasoning": "Why"
    }},
    "gen_z": {{
        "winner": "Name",
        "reasoning": "Why"
    }},
    "boomer": {{
        "winner": "Name",
        "reasoning": "Why"
    }}
}}"""

    try:
        print("  Calling LLM for sentiment awards...")
        response = client.messages.create(
            model=get_llm_model(),
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON
        import re
        response_text = response.content[0].text
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"raw": response_text}

    except Exception as e:
        print(f"  ERROR computing sentiment awards: {e}")
        return None


def generate_message_from_partner(client, messages, from_username, to_username, convo_count):
    """
    Generate a message from someone's #1 conversation partner.

    Args:
        client: Anthropic client
        messages: All messages
        from_username: Who's sending the message
        to_username: Who's receiving it
        convo_count: Number of conversations they had

    Returns:
        str: Generated message
    """
    from_name = USERNAME_MAP.get(from_username, from_username)
    to_name = USERNAME_MAP.get(to_username, to_username)

    print(f"  Generating message: {from_name} → {to_name}...")

    # Sample messages from the sender to capture their voice
    from_messages = [m for m in messages if m['author'] == from_username]
    if len(from_messages) > 100:
        from_messages = random.sample(from_messages, 100)

    voice_samples = "\n".join([
        m['content'][:200] for m in from_messages if m['content']
    ][:50])

    # Sample their actual conversations
    msg_map = {m['id']: m for m in messages}
    convos = []
    for msg in messages:
        if msg['author'] == from_username:
            ref = msg.get('reference')
            if ref and isinstance(ref, dict):
                ref_id = ref.get('message_id')
                if ref_id in msg_map and msg_map[ref_id]['author'] == to_username:
                    convos.append({
                        'them': msg_map[ref_id]['content'][:100],
                        'you': msg['content'][:100]
                    })

    convo_samples = "\n".join([
        f"{to_name}: {c['them']}\n{from_name}: {c['you']}"
        for c in convos[:10]
    ])

    prompt = f"""You are {from_name}, writing a short end-of-year message to {to_name}.

You two had {convo_count} conversations this year on Discord.

Your communication style (from your messages):
{voice_samples}

Example conversations you had:
{convo_samples}

Write a 2-3 sentence message to {to_name} in YOUR voice ({from_name}'s voice).
- Reference the year you had together
- Be specific but warm
- Sound like yourself (use your patterns)
- Keep it under 60 words
- Don't be overly sentimental - match your actual tone

Just the message, no preamble:"""

    try:
        response = client.messages.create(
            model=get_llm_model(),
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    except Exception as e:
        print(f"    ERROR generating message: {e}")
        return None


# === MAIN ===

def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_llm_analysis.py discord_messages.json")
        sys.exit(1)

    if not HAS_ANTHROPIC:
        print("ERROR: anthropic package required")
        sys.exit(1)

    # Initialize Anthropic client
    try:
        client = anthropic.Anthropic()
        print("✓ Anthropic client initialized\n")
    except Exception as e:
        print(f"ERROR initializing Anthropic client: {e}")
        print("Make sure ANTHROPIC_API_KEY is set")
        sys.exit(1)

    filepath = sys.argv[1]

    # Load data
    messages = load_messages(filepath)
    group_data, person_data = load_wrapped_data()

    print("="*60)
    print("LLM ANALYSIS - This will use your API key")
    print("="*60)
    print("Analyses to run:")
    print(f"  - Personality reads: {len(person_data)} people")
    print(f"  - Sentiment awards: 5 awards")
    print(f"  - Messages from partners: {len(person_data)} messages")
    print(f"\nEstimated API calls: ~{len(person_data) * 2 + 6}")
    print("="*60)

    proceed = input("\nProceed? (y/n): ")
    if proceed.lower() != 'y':
        print("Cancelled.")
        return

    print("\n" + "="*60)
    print("RUNNING LLM ANALYSES")
    print("="*60)

    # 1. Personality reads
    print("\n1. Generating personality reads...")
    personality_reads = {}
    for username, stats in person_data.items():
        result = analyze_person_personality(client, messages, username, stats)
        if result:
            personality_reads[username] = result

    # 2. Sentiment awards
    sentiment_awards = compute_sentiment_awards(client, messages)

    # 3. Messages from partners
    print("\n2. Generating 'Message From' texts...")
    partner_assignments = compute_partner_assignments(person_data)
    partner_messages = {}
    for username, stats in person_data.items():
        if username in partner_assignments:
            partner_username = partner_assignments[username]

            # Find the conversation count for this partner
            top_partners = stats['relationships'].get('top_reply_targets', [])
            convo_count = 0
            for partner in top_partners:
                if partner['username'] == partner_username:
                    convo_count = partner['count']
                    break

            if convo_count == 0:
                print(f"Warning: No conversation data found for {username} ↔ {partner_username}")
                continue

            message = generate_message_from_partner(
                client, messages, partner_username, username, convo_count
            )
            if message:
                partner_messages[username] = {
                    'from': partner_username,
                    'from_display_name': USERNAME_MAP.get(partner_username, partner_username),
                    'message': message,
                    'conversation_count': convo_count
                }

    # Compile output
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_file': filepath
        },
        'personality_reads': personality_reads,
        'sentiment_awards': sentiment_awards,
        'partner_messages': partner_messages
    }

    # Save
    output_dir = Path('output')
    output_file = output_dir / 'llm_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    print("\n" + "="*60)
    print("LLM ANALYSIS COMPLETE")
    print("="*60)
    print(f"Personality reads: {len(personality_reads)}")
    print(f"Sentiment awards: {len(sentiment_awards) if sentiment_awards else 0}")
    print(f"Partner messages: {len(partner_messages)}")
    print(f"\nOutput saved: {output_file}")
    print("="*60)


if __name__ == "__main__":
    main()
