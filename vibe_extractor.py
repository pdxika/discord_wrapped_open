"""
Discord Wrapped Vibe Extractor
Analyzes Discord message history to extract the server's voice and tone.
Outputs a Voice Guide for Discord Wrapped narration.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=ANTHROPIC_API_KEY
    python vibe_extractor.py path/to/discord_export.json
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from config import get_username_map, get_server_name, get_llm_model


try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("Warning: anthropic package not installed. LLM analysis will be skipped.")
    print("Install with: pip install anthropic")


# === CONFIGURATION ===

USERNAME_MAP = get_username_map()

# Stop words for phrase analysis
STOP_WORDS = {
    'the', 'a', 'an', 'is', 'it', 'to', 'and', 'of', 'that', 'in', 'for', 'you', 
    'i', 'on', 'was', 'be', 'have', 'are', 'with', 'this', 'but', 'they', 'not', 
    'at', 'or', 'so', 'if', 'my', 'me', 'we', 'do', 'what', 'just', 'can', 'he', 
    'she', 'as', 'there', 'would', 'like', 'all', 'one', 'about', 'out', 'up', 
    'from', 'had', 'has', 'no', 'yeah', 'yes', 'lol', 'its', "it's", 'im', "i'm", 
    'dont', "don't", 'get', 'got', 'how', 'who', 'when', 'been', 'them', 'their',
    'more', 'will', 'really', 'know', 'think', 'going', 'good', 'thing', 'some',
    'still', 'very', 'did', 'https', 'http', 'www', 'com'
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
        msg['_timestamp'] = datetime.fromisoformat(msg['timestamp'].replace('+00:00', ''))

    return messages, data


# === COMPUTED ANALYSIS ===

def analyze_basics(messages):
    """Basic statistics about the server."""
    stats = {
        'total_messages': len(messages),
        'unique_authors': len(set(m['author'] for m in messages)),
        'channels': list(set(m.get('channel_name', 'unknown') for m in messages)),
        'date_range': {
            'start': min(m['timestamp'] for m in messages)[:10],
            'end': max(m['timestamp'] for m in messages)[:10],
        },
        'messages_per_author': Counter(m['author'] for m in messages).most_common(15),
    }
    return stats


def analyze_message_patterns(messages):
    """Analyze message length, timing, and structure patterns."""

    # Message length by author
    author_lengths = defaultdict(list)
    for msg in messages:
        if msg['content']:
            author_lengths[msg['author']].append(len(msg['content']))

    avg_lengths = {
        author: sum(lengths) / len(lengths) 
        for author, lengths in author_lengths.items() 
        if len(lengths) > 50
    }

    # Short vs long message ratio (is this a rapid-fire server?)
    short_messages = sum(1 for m in messages if m['content'] and len(m['content']) < 50)
    medium_messages = sum(1 for m in messages if m['content'] and 50 <= len(m['content']) < 200)
    long_messages = sum(1 for m in messages if m['content'] and len(m['content']) >= 200)

    # Consecutive messages by same author (rapid-fire posting)
    streaks = []
    current_streak = 1
    for i in range(1, len(messages)):
        if messages[i]['author'] == messages[i-1]['author']:
            current_streak += 1
        else:
            if current_streak > 1:
                streaks.append(current_streak)
            current_streak = 1

    return {
        'avg_length_by_author': avg_lengths,
        'message_length_distribution': {
            'short_under_50': short_messages,
            'medium_50_200': medium_messages,
            'long_200_plus': long_messages,
        },
        'rapid_fire_score': len([s for s in streaks if s >= 3]) / max(len(streaks), 1),
        'avg_streak_length': sum(streaks) / max(len(streaks), 1) if streaks else 0,
    }


def analyze_vocabulary(messages):
    """Find signature words and phrases."""

    # Overall word frequency
    all_words = Counter()
    author_words = defaultdict(Counter)

    for msg in messages:
        words = re.findall(r'\b[a-z]{4,}\b', msg['content'].lower())
        filtered = [w for w in words if w not in STOP_WORDS]
        all_words.update(filtered)
        author_words[msg['author']].update(filtered)

    # Find signature words (used more by one person than expected)
    total_words = sum(all_words.values())
    signature_words = {}

    for author, words in author_words.items():
        author_total = sum(words.values())
        if author_total < 500:  # Skip low-volume authors
            continue

        sig = []
        for word, count in words.most_common(300):
            if count < 8:
                continue
            expected = (all_words[word] / total_words) * author_total
            if expected > 0 and count > expected * 1.8:
                sig.append({
                    'word': word,
                    'count': count,
                    'ratio': round(count / expected, 1)
                })

        signature_words[author] = sorted(sig, key=lambda x: x['ratio'], reverse=True)[:10]

    return {
        'top_words': all_words.most_common(50),
        'signature_words_by_author': signature_words,
    }


def analyze_emoji_culture(messages):
    """Analyze emoji usage in messages and reactions."""

    # Emoji pattern (basic)
    emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\U00002702-\U000027B0]')

    message_emojis = Counter()
    reaction_emojis = Counter()
    author_emoji_rate = defaultdict(lambda: {'messages': 0, 'emojis': 0})

    for msg in messages:
        # Emojis in message content
        emojis = emoji_pattern.findall(msg['content'])
        message_emojis.update(emojis)

        author_emoji_rate[msg['author']]['messages'] += 1
        author_emoji_rate[msg['author']]['emojis'] += len(emojis)

        # Reaction emojis
        for reaction in msg.get('reactions', []):
            reaction_emojis[reaction['emoji']] += reaction.get('count', 1)

    # Calculate emoji density per author
    emoji_density = {
        author: data['emojis'] / max(data['messages'], 1)
        for author, data in author_emoji_rate.items()
        if data['messages'] > 50
    }

    return {
        'top_message_emojis': message_emojis.most_common(15),
        'top_reaction_emojis': reaction_emojis.most_common(15),
        'emoji_density_by_author': emoji_density,
        'most_emoji_heavy': max(emoji_density.items(), key=lambda x: x[1]) if emoji_density else None,
        'least_emoji': min(emoji_density.items(), key=lambda x: x[1]) if emoji_density else None,
    }


def analyze_conversation_style(messages):
    """Analyze how conversations flow - replies, mentions, etc."""

    reply_counts = defaultdict(lambda: defaultdict(int))  # who replies to whom
    mention_counts = defaultdict(lambda: defaultdict(int))  # who mentions whom

    # Build message ID to author map
    msg_author_map = {m['id']: m['author'] for m in messages}

    for msg in messages:
        author = msg['author']

        # Track replies
        ref = msg.get('reference')
        if ref and isinstance(ref, dict):
            ref_id = ref.get('message_id')
            if ref_id and ref_id in msg_author_map:
                target = msg_author_map[ref_id]
                if target != author:  # Don't count self-replies
                    reply_counts[author][target] += 1

        # Track mentions
        for mention in msg.get('mentions', []):
            if isinstance(mention, str) and mention != author:
                mention_counts[author][mention] += 1

    # Find top conversation pairs
    pairs = Counter()
    for author, targets in reply_counts.items():
        for target, count in targets.items():
            pair = tuple(sorted([author, target]))
            pairs[pair] += count

    return {
        'top_conversation_pairs': pairs.most_common(10),
        'reply_patterns': {
            author: dict(sorted(targets.items(), key=lambda x: x[1], reverse=True)[:3])
            for author, targets in reply_counts.items()
            if sum(targets.values()) > 10
        },
    }


def find_high_engagement_messages(messages, n=50):
    """Find messages that got lots of reactions - these define what resonates."""

    scored = []
    for msg in messages:
        if not msg['content'] or len(msg['content']) < 10:
            continue

        reaction_count = sum(r.get('count', 1) for r in msg.get('reactions', []))
        if reaction_count >= 2:
            scored.append({
                'content': msg['content'][:500],
                'author': msg['author'],
                'reactions': reaction_count,
                'reaction_types': [r['emoji'] for r in msg.get('reactions', [])],
                'timestamp': msg['timestamp'][:10],
            })

    scored.sort(key=lambda x: x['reactions'], reverse=True)
    return scored[:n]


def find_conversation_samples(messages, n=10):
    """Find complete conversation threads to sample."""

    # Group messages by rough time clusters (within 10 min = same convo)
    conversations = []
    current_convo = []

    for i, msg in enumerate(messages):
        if not current_convo:
            current_convo.append(msg)
            continue

        # Check time gap
        prev_time = current_convo[-1]['_timestamp']
        curr_time = msg['_timestamp']
        gap_minutes = (curr_time - prev_time).total_seconds() / 60

        if gap_minutes > 30 or len(current_convo) > 50:
            if len(current_convo) >= 8:
                conversations.append(current_convo)
            current_convo = [msg]
        else:
            current_convo.append(msg)

    # Score conversations by engagement and participant diversity
    scored_convos = []
    for convo in conversations:
        participants = len(set(m['author'] for m in convo))
        total_reactions = sum(
            sum(r.get('count', 1) for r in m.get('reactions', []))
            for m in convo
        )
        avg_length = sum(len(m['content']) for m in convo) / len(convo)

        # Prefer diverse, reactive, substantive conversations
        score = participants * 2 + total_reactions + (avg_length / 50)

        scored_convos.append({
            'messages': convo,
            'score': score,
            'participants': participants,
            'reactions': total_reactions,
        })

    scored_convos.sort(key=lambda x: x['score'], reverse=True)

    # Format for output
    samples = []
    for convo in scored_convos[:n]:
        formatted = []
        for m in convo['messages']:
            name = USERNAME_MAP.get(m['author'], m['author'])
            formatted.append(f"{name}: {m['content'][:300]}")

        samples.append({
            'thread': '\n'.join(formatted),
            'participants': convo['participants'],
            'reactions': convo['reactions'],
            'date': convo['messages'][0]['timestamp'][:10],
        })

    return samples


def analyze_linguistic_quirks(messages):
    """Find linguistic patterns - caps, punctuation, lol usage, etc."""

    caps_rate = defaultdict(lambda: {'total': 0, 'caps': 0})
    question_rate = defaultdict(lambda: {'total': 0, 'questions': 0})
    lol_variants = defaultdict(Counter)

    for msg in messages:
        content = msg['content']
        author = msg['author']

        if not content or len(content) < 3:
            continue

        caps_rate[author]['total'] += 1
        question_rate[author]['total'] += 1

        # All caps detection (exclude short messages)
        if len(content) > 10 and content.isupper():
            caps_rate[author]['caps'] += 1

        # Question asking
        if '?' in content:
            question_rate[author]['questions'] += 1

        # Laughter variants
        lol_match = re.findall(r'\b(lol|lmao|haha|hahaha|lmfao|😂|💀|ijbol)\b', content.lower())
        lol_variants[author].update(lol_match)

    return {
        'caps_rate_by_author': {
            author: data['caps'] / max(data['total'], 1)
            for author, data in caps_rate.items()
            if data['total'] > 50
        },
        'question_rate_by_author': {
            author: data['questions'] / max(data['total'], 1)
            for author, data in question_rate.items()
            if data['total'] > 50
        },
        'laughter_style_by_author': {
            author: dict(variants.most_common(5))
            for author, variants in lol_variants.items()
            if sum(variants.values()) > 5
        },
    }


# === LLM ANALYSIS ===

def run_llm_analysis(client, conversation_samples, high_engagement, computed_stats):
    """Use Claude to analyze the server's voice and tone."""

    print("\nRunning LLM analysis...")

    # Prepare conversation samples for the prompt
    convo_text = ""
    for i, sample in enumerate(conversation_samples[:6], 1):
        convo_text += f"\n--- Conversation {i} ({sample['date']}, {sample['participants']} people) ---\n"
        convo_text += sample['thread']
        convo_text += "\n"

    # Prepare high engagement messages
    engagement_text = "\n".join([
        f"- \"{m['content'][:200]}\" ({m['author']}, {m['reactions']} reactions)"
        for m in high_engagement[:20]
    ])

    # Build the analysis prompt
    server_name = get_server_name()
    prompt = f"""You are analyzing a Discord server called "{server_name}".

Your task: Extract the SERVER'S VOICE - how this group talks, what makes them them, so we can write a "Discord Wrapped" year-end review that sounds like it was made BY them, FOR them.

## HIGH-ENGAGEMENT MESSAGES (what resonates)
{engagement_text}

## SAMPLE CONVERSATIONS
{convo_text}

## COMPUTED DATA
- Top reaction emojis: {computed_stats['emoji']['top_reaction_emojis'][:8]}
- Message length: {computed_stats['patterns']['message_length_distribution']}
- Rapid-fire score: {computed_stats['patterns']['rapid_fire_score']:.2f}

Based on this data, provide a detailed VOICE GUIDE in the following JSON format:

{{
    "overall_vibe": "2-3 sentence description of the server's personality",

    "tone_spectrum": {{
        "irony_to_sincerity": "where they fall (e.g., 'mostly ironic with genuine moments')",
        "energy_level": "low/medium/high/chaotic",
        "warmth": "how they show affection"
    }},

    "humor_style": {{
        "primary_type": "e.g., absurdist, observational, self-deprecating",
        "how_bits_work": "how jokes build and escalate",
        "references": ["common reference points - movies, shows, etc"]
    }},

    "conversation_dna": {{
        "how_topics_start": "who/how topics get introduced",
        "how_they_build": "how the group riffs together",
        "when_sincerity_happens": "what triggers genuine moments"
    }},

    "linguistic_patterns": {{
        "message_style": "short rapid-fire vs long essays vs mix",
        "punctuation_vibe": "how they use ... vs ! vs nothing",
        "caps_usage": "when and why",
        "signature_phrases": ["phrases that feel very 'them'"]
    }},

    "narrator_voice": {{
        "should_sound_like": "description of ideal narrator tone",
        "sample_lines": [
            "3-5 example lines in the server's voice for Wrapped narration"
        ],
        "things_to_avoid": ["tones or phrases that would feel wrong"]
    }},

    "individual_vibes": {{
        "person_name": "1-2 sentence vibe description for each main person"
    }}
}}

Be specific. Use examples from the conversations. This needs to feel like THEIR voice, not generic."""

    response = client.messages.create(
        model=get_llm_model(),
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract JSON from response
    response_text = response.content[0].text

    # Try to parse JSON from the response
    try:
        # Find JSON block
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            voice_guide = json.loads(json_match.group())
        else:
            voice_guide = {"raw_analysis": response_text}
    except json.JSONDecodeError:
        voice_guide = {"raw_analysis": response_text}

    return voice_guide


# === MAIN ===

def main():
    if len(sys.argv) < 2:
        print("Usage: python vibe_extractor.py path/to/discord_export.json")
        sys.exit(1)

    filepath = sys.argv[1]

    # Load data
    messages, raw_data = load_messages(filepath)

    print("\n" + "="*60)
    print("COMPUTED ANALYSIS")
    print("="*60)

    # Run computed analyses
    basics = analyze_basics(messages)
    print(f"\nBasics: {basics['total_messages']:,} messages from {basics['unique_authors']} authors")
    print(f"Date range: {basics['date_range']['start']} to {basics['date_range']['end']}")
    print(f"Channels: {basics['channels']}")

    patterns = analyze_message_patterns(messages)
    print(f"\nMessage patterns:")
    print(f"  Length distribution: {patterns['message_length_distribution']}")
    print(f"  Rapid-fire score: {patterns['rapid_fire_score']:.2f}")

    vocab = analyze_vocabulary(messages)
    print(f"\nTop words: {[w for w, c in vocab['top_words'][:15]]}")

    emoji = analyze_emoji_culture(messages)
    print(f"\nTop reactions: {emoji['top_reaction_emojis'][:8]}")

    convo_style = analyze_conversation_style(messages)
    print(f"\nTop conversation pairs: {convo_style['top_conversation_pairs'][:5]}")

    quirks = analyze_linguistic_quirks(messages)

    # Find samples
    print("\nFinding high-engagement messages...")
    high_engagement = find_high_engagement_messages(messages, n=50)

    print("Finding conversation samples...")
    conversation_samples = find_conversation_samples(messages, n=10)

    # Compile computed stats
    computed_stats = {
        'basics': basics,
        'patterns': patterns,
        'vocabulary': vocab,
        'emoji': emoji,
        'conversation_style': convo_style,
        'quirks': quirks,
        'high_engagement_samples': high_engagement[:20],
        'conversation_samples': conversation_samples[:5],
    }

    # LLM Analysis
    voice_guide = None
    if HAS_ANTHROPIC:
        import os
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
            voice_guide = run_llm_analysis(
                client, 
                conversation_samples, 
                high_engagement,
                computed_stats
            )
        else:
            print("\nNo ANTHROPIC_API_KEY found. Skipping LLM analysis.")
            print("Set it with: export ANTHROPIC_API_KEY='your-key'")

    # Compile final output
    output = {
        'generated_at': datetime.now().isoformat(),
        'source_file': filepath,
        'computed_analysis': computed_stats,
        'voice_guide': voice_guide,
    }

    # Save output
    output_path = Path('voice_guide_output.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    print("\n" + "="*60)
    print(f"OUTPUT SAVED: {output_path}")
    print("="*60)

    # Also save a readable markdown version
    md_path = Path('voice_guide_output.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {get_server_name()} Voice Guide\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        f.write("## Computed Stats\n\n")
        f.write(f"- **Total messages**: {basics['total_messages']:,}\n")
        f.write(f"- **Authors**: {basics['unique_authors']}\n")
        f.write(f"- **Date range**: {basics['date_range']['start']} to {basics['date_range']['end']}\n")
        f.write(f"- **Top reaction emojis**: {', '.join(e for e, c in emoji['top_reaction_emojis'][:10])}\n\n")

        f.write("### Top Authors\n")
        for author, count in basics['messages_per_author'][:10]:
            name = USERNAME_MAP.get(author, author)
            f.write(f"- {name} ({author}): {count:,}\n")

        f.write("\n### Signature Words by Person\n")
        for author, words in vocab['signature_words_by_author'].items():
            name = USERNAME_MAP.get(author, author)
            word_list = ', '.join(w['word'] for w in words[:5])
            f.write(f"- **{name}**: {word_list}\n")

        if voice_guide and 'overall_vibe' in voice_guide:
            f.write("\n## LLM Voice Analysis\n\n")
            f.write(f"### Overall Vibe\n{voice_guide.get('overall_vibe', 'N/A')}\n\n")

            if 'narrator_voice' in voice_guide:
                f.write("### Narrator Voice\n")
                f.write(f"{voice_guide['narrator_voice'].get('should_sound_like', '')}\n\n")

                f.write("**Sample lines:**\n")
                for line in voice_guide['narrator_voice'].get('sample_lines', []):
                    f.write(f"> {line}\n\n")

        f.write("\n## High Engagement Messages\n\n")
        for msg in high_engagement[:15]:
            name = USERNAME_MAP.get(msg['author'], msg['author'])
            f.write(f"- **{name}** ({msg['reactions']} reactions): \"{msg['content'][:150]}...\"\n")

    print(f"READABLE VERSION: {md_path}")

    if voice_guide:
        print("\n" + "="*60)
        print("VOICE GUIDE PREVIEW")
        print("="*60)
        if 'overall_vibe' in voice_guide:
            print(f"\nOverall vibe: {voice_guide['overall_vibe']}")
        if 'narrator_voice' in voice_guide:
            print(f"\nNarrator should sound like: {voice_guide['narrator_voice'].get('should_sound_like', 'N/A')}")
            print("\nSample lines:")
            for line in voice_guide['narrator_voice'].get('sample_lines', [])[:3]:
                print(f"  > {line}")


if __name__ == "__main__":
    main()
