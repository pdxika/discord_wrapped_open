"""
Discord Wrapped 2025 - Basic Stats Computation
Computes all pure statistical data (no LLM required).
Outputs: group_wrapped.json + individual wrapped_{user}.json files

Usage:
    python compute_basic_stats.py discord_messages.json
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from config import get_username_map, get_inside_jokes, get_server_name


# === CONFIGURATION ===

USERNAME_MAP = get_username_map()

# Reverse lookup
DISPLAY_NAME_TO_USERNAME = {v: k for k, v in USERNAME_MAP.items()}


# === DATA LOADING ===

def load_messages(filepath):
    """Load messages from Discord export JSON."""
    print(f"Loading {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both formats (flat messages or sessions)
    messages = []
    
    if 'messages' in data:
        print("Detected flat message format")
        messages = data['messages']
    elif isinstance(data, list):
        print("Detected session format")
        for s in data:
            for m in s.get('messages', []):
                if 'timestamp' not in m:
                    m['timestamp'] = s.get('start_time')
                messages.append(m)
    else:
        print("Unknown data format")
        return [], data

    print(f"Loaded {len(messages):,} messages")

    # Parse timestamps
    for msg in messages:
        ts_str = msg['timestamp'].replace('+00:00', '')
        msg['_datetime'] = datetime.fromisoformat(ts_str)

    # Sort by timestamp
    messages.sort(key=lambda m: m['_datetime'])

    return messages, data


# === SERVER-WIDE STATS ===

def compute_server_stats(messages):
    """Compute overall server statistics."""
    print("\nComputing server-wide stats...")

    total_messages = len(messages)
    unique_authors = len(set(m['author'] for m in messages))

    # Date range
    start_date = min(m['_datetime'] for m in messages)
    end_date = max(m['_datetime'] for m in messages)

    # Messages per day/hour/weekday
    messages_by_date = Counter(m['_datetime'].date() for m in messages)
    messages_by_hour = Counter(m['_datetime'].hour for m in messages)
    messages_by_weekday = Counter(m['_datetime'].weekday() for m in messages)

    # Peak activity
    peak_date = messages_by_date.most_common(1)[0]
    peak_hour = messages_by_hour.most_common(1)[0]
    peak_weekday = messages_by_weekday.most_common(1)[0]

    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    # Activity heatmap (hour × weekday)
    heatmap = [[0 for _ in range(24)] for _ in range(7)]
    for msg in messages:
        hour = msg['_datetime'].hour
        weekday = msg['_datetime'].weekday()
        heatmap[weekday][hour] += 1

    # Volume by week
    volume_by_week = defaultdict(int)
    for msg in messages:
        # ISO calendar week
        year, week, _ = msg['_datetime'].isocalendar()
        week_key = f"{year}-W{week:02d}"
        volume_by_week[week_key] += 1

    # Channels
    channels = Counter(m.get('channel_name', 'unknown') for m in messages)

    # Reactions
    total_reactions = sum(
        sum(r.get('count', 1) for r in m.get('reactions', []))
        for m in messages
    )

    # Top reaction emojis
    reaction_counter = Counter()
    for msg in messages:
        for reaction in msg.get('reactions', []):
            reaction_counter[reaction['emoji']] += reaction.get('count', 1)

    # Transform volume_by_week to array for Recharts
    weekly_activity = [
        {"week": k, "count": v} 
        for k, v in sorted(volume_by_week.items())
    ]

    return {
        'total_messages': total_messages,
        'active_members_count': unique_authors, # Renamed for frontend
        'unique_authors': unique_authors,
        'date_range': {
            'start': start_date.date().isoformat(),
            'end': end_date.date().isoformat(),
            'days': (end_date.date() - start_date.date()).days
        },
        'active_days_count': len(messages_by_date),
        'busiest_day': { # Renamed/Restructured for frontend
            'date': peak_date[0].isoformat(),
            'count': peak_date[1]
        },
        'most_active_hour': peak_hour[0], # Renamed for frontend
        'peak_activity': {
            'date': peak_date[0].isoformat(),
            'date_message_count': peak_date[1],
            'hour': peak_hour[0],
            'hour_message_count': peak_hour[1],
            'weekday': weekday_names[peak_weekday[0]],
            'weekday_message_count': peak_weekday[1]
        },
        'activity_heatmap': heatmap,
        'weekly_activity': weekly_activity, # New array format
        'volume_by_week': dict(sorted(volume_by_week.items())), # Keep old dict just in case
        'channels': dict(channels.most_common()),
        'total_reactions': total_reactions,
        'top_reaction_emojis': [
            {'emoji': emoji, 'count': count}
            for emoji, count in reaction_counter.most_common(10)
        ]
    }


# === LEADERBOARDS ===

def compute_leaderboards(messages):
    """Compute various leaderboards."""
    print("Computing leaderboards...")

    # Messages sent
    messages_by_author = Counter(m['author'] for m in messages)

    # Reactions received
    reactions_received = defaultdict(int)
    for msg in messages:
        author = msg['author']
        for reaction in msg.get('reactions', []):
            reactions_received[author] += reaction.get('count', 1)

    # Build message ID to author map for reply analysis
    msg_author_map = {m['id']: m['author'] for m in messages}

    # Replies sent (who replies most)
    replies_sent = Counter()
    for msg in messages:
        if msg.get('reference') and isinstance(msg['reference'], dict):
            replies_sent[msg['author']] += 1

    # Replies received (who gets replied to most)
    replies_received = Counter()
    for msg in messages:
        ref = msg.get('reference')
        if ref and isinstance(ref, dict):
            ref_id = ref.get('message_id')
            if ref_id and ref_id in msg_author_map:
                replies_received[msg_author_map[ref_id]] += 1

    # Conversation pairs (bidirectional)
    reply_pairs = defaultdict(lambda: defaultdict(int))
    for msg in messages:
        author = msg['author']
        ref = msg.get('reference')
        if ref and isinstance(ref, dict):
            ref_id = ref.get('message_id')
            if ref_id and ref_id in msg_author_map:
                target = msg_author_map[ref_id]
                if target != author:
                    pair = tuple(sorted([author, target]))
                    reply_pairs[pair]['count'] = reply_pairs[pair].get('count', 0) + 1

    # Format conversation pairs
    conversation_pairs = [
        {
            'person1': pair[0],
            'person2': pair[1],
            'count': data['count']
        }
        for pair, data in sorted(reply_pairs.items(), key=lambda x: x[1]['count'], reverse=True)
    ]

    return {
        'top_talkers': [
            {'username': author, 'display_name': USERNAME_MAP.get(author, author), 'count': count}
            for author, count in messages_by_author.most_common()
        ],
        'top_reactors_received': [
            {'username': author, 'display_name': USERNAME_MAP.get(author, author), 'count': count}
            for author, count in sorted(reactions_received.items(), key=lambda x: x[1], reverse=True)
        ],
        'top_repliers': [
            {'username': author, 'display_name': USERNAME_MAP.get(author, author), 'count': count}
            for author, count in replies_sent.most_common()
        ],
        'most_replied_to': [
            {'username': author, 'display_name': USERNAME_MAP.get(author, author), 'count': count}
            for author, count in replies_received.most_common()
        ],
        'top_conversation_pairs': conversation_pairs[:10]
    }


# === PER-PERSON STATS ===

def compute_person_stats(messages, username, msg_author_map):
    """Compute stats for a specific person."""

    print(f"  Computing stats for {USERNAME_MAP.get(username, username)}...")

    # Filter messages by this person
    person_messages = [m for m in messages if m['author'] == username]

    if not person_messages:
        return None

    total_messages = len(person_messages)

    # Rank (among all authors)
    all_authors = Counter(m['author'] for m in messages)
    sorted_authors = [author for author, count in all_authors.most_common()]
    rank = sorted_authors.index(username) + 1

    # Reactions received
    reactions_received = sum(
        sum(r.get('count', 1) for r in m.get('reactions', []))
        for m in person_messages
    )

    # Time patterns
    hours = [m['_datetime'].hour for m in person_messages]
    weekdays = [m['_datetime'].weekday() for m in person_messages]

    hour_counter = Counter(hours)
    weekday_counter = Counter(weekdays)

    most_active_hour = hour_counter.most_common(1)[0][0]
    most_active_weekday = weekday_counter.most_common(1)[0][0]

    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    # Night owl score (midnight to 5am)
    night_messages = sum(1 for h in hours if 0 <= h < 5)
    night_owl_score = night_messages / total_messages if total_messages > 0 else 0

    # Early bird score (5am to 7am)
    early_messages = sum(1 for h in hours if 5 <= h < 7)
    early_bird_score = early_messages / total_messages if total_messages > 0 else 0

    # Active days
    active_dates = set(m['_datetime'].date() for m in person_messages)
    days_active = len(active_dates)

    # Message length stats
    message_lengths = [len(m['content']) for m in person_messages if m['content']]
    avg_message_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
    longest_message_length = max(message_lengths) if message_lengths else 0

    # Emoji usage
    emoji_count = 0
    for msg in person_messages:
        # Simple emoji detection (Unicode ranges)
        import re
        emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\U00002702-\U000027B0]')
        emoji_count += len(emoji_pattern.findall(msg['content']))

    emoji_rate = emoji_count / total_messages if total_messages > 0 else 0

    # Vocabulary (Top unique words)
    all_text = " ".join(m['content'].lower() for m in person_messages if m['content'])
    # Simple tokenization
    import re
    words = re.findall(r'\b[a-z]{3,}\b', all_text)
    
    # Filter stop words (assuming STOP_WORDS is defined globally now)
    unique_words = [w for w in words if w not in STOP_WORDS]
    word_counts = Counter(unique_words)
    vocabulary = [w for w, c in word_counts.most_common(20)]

    # Questions asked
    questions = sum(1 for m in person_messages if '?' in m['content'])
    question_rate = questions / total_messages if total_messages > 0 else 0

    # All caps messages (longer than 10 chars)
    caps_messages = sum(
        1 for m in person_messages
        if len(m['content']) > 10 and m['content'].isupper()
    )
    caps_rate = caps_messages / total_messages if total_messages > 0 else 0

    # Edited messages
    edited = sum(1 for m in person_messages if m.get('edited_at'))
    edit_rate = edited / total_messages if total_messages > 0 else 0

    # Channels used
    channels_used = Counter(m.get('channel_name', 'unknown') for m in person_messages)
    home_channel = channels_used.most_common(1)[0] if channels_used else ('unknown', 0)

    # Conversation partners (who they reply to)
    # msg_author_map passed in as parameter now

    reply_targets = Counter()
    for msg in person_messages:
        ref = msg.get('reference')
        if ref and isinstance(ref, dict):
            ref_id = ref.get('message_id')
            if ref_id and ref_id in msg_author_map:
                target = msg_author_map[ref_id]
                if target != username:
                    reply_targets[target] += 1

    # Who replies to them
    person_msg_ids = set(m['id'] for m in person_messages)
    replied_by = Counter()
    for msg in messages:
        if msg['author'] == username:
            continue
        ref = msg.get('reference')
        if ref and isinstance(ref, dict):
            ref_id = ref.get('message_id')
            if ref_id in person_msg_ids:
                replied_by[msg['author']] += 1

    # Mutual bestie (bidirectional conversation partner)
    mutual_scores = {}
    for target, sent_count in reply_targets.items():
        received_count = replied_by.get(target, 0)
        # Harmonic mean favors balanced relationships
        if sent_count > 0 and received_count > 0:
            mutual_scores[target] = 2 * (sent_count * received_count) / (sent_count + received_count)

    mutual_bestie = max(mutual_scores.items(), key=lambda x: x[1])[0] if mutual_scores else None

    # Best moment (most reacted message)
    best_message = None
    max_reactions = 0
    for msg in person_messages:
        reaction_count = sum(r.get('count', 1) for r in msg.get('reactions', []))
        if reaction_count > max_reactions:
            max_reactions = reaction_count
            best_message = {
                'content': msg['content'][:500],
                'timestamp': msg['timestamp'],
                'reactions': reaction_count,
                'reaction_types': [r['emoji'] for r in msg.get('reactions', [])]
            }

    # Longest streak (consecutive days)
    sorted_dates = sorted(active_dates)
    longest_streak = 1
    current_streak = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 1

    # Longest absence (gap between messages)
    longest_absence_days = 0
    if len(sorted_dates) > 1:
        for i in range(1, len(sorted_dates)):
            gap = (sorted_dates[i] - sorted_dates[i-1]).days
            longest_absence_days = max(longest_absence_days, gap)

    return {
        'username': username,
        'display_name': USERNAME_MAP.get(username, username),
        'stats': {
            'messages_sent': total_messages,
            'rank': rank,
            'reactions_received': reactions_received,
            'days_active': days_active,
            'most_active_hour': most_active_hour,
            'most_active_weekday': weekday_names[most_active_weekday],
            'night_owl_score': round(night_owl_score, 3),
            'early_bird_score': round(early_bird_score, 3),
            'avg_message_length': round(avg_message_length, 1),
            'longest_message_length': longest_message_length,
            'emoji_rate': round(emoji_rate, 2),
            'question_rate': round(question_rate, 3),
            'caps_rate': round(caps_rate, 3),
            'edit_rate': round(edit_rate, 3),
            'longest_streak_days': longest_streak,
            'longest_absence_days': longest_absence_days,
            'vocabulary': vocabulary
        },
        'channels': {
            'home_channel': home_channel[0],
            'home_channel_messages': home_channel[1],
            'all_channels': dict(channels_used.most_common())
        },
        'relationships': {
            'top_reply_targets': [
                {'username': target, 'display_name': USERNAME_MAP.get(target, target), 'count': count}
                for target, count in reply_targets.most_common(3)
            ],
            'top_replied_by': [
                {'username': person, 'display_name': USERNAME_MAP.get(person, person), 'count': count}
                for person, count in replied_by.most_common(3)
            ],
            'mutual_bestie': {
                'username': mutual_bestie,
                'display_name': USERNAME_MAP.get(mutual_bestie, mutual_bestie) if mutual_bestie else None
            } if mutual_bestie else None
        },
        'best_moment': best_message
    }


# === AWARDS (Stats-based only) ===

def compute_basic_awards(messages, all_person_stats):
    """Compute awards that can be determined from pure stats."""
    print("Computing basic awards...")

    awards = {}

    # Winner Diversity Tracker
    winner_counts = Counter()
    
    def get_diverse_winner(candidates, award_name):
        """
        Selects a winner from a list of (username, score) tuples.
        Penalizes users who have already won too many awards.
        """
        # Sort by score descending
        sorted_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)
        
        for candidate in sorted_candidates:
            username = candidate[0]
            # If user has won less than 2 awards, they are eligible
            limit = 2
            
            if winner_counts[username] < limit:
                winner_counts[username] += 1
                return candidate
        
        # If everyone is capped, just take the top one
        top = sorted_candidates[0]
        winner_counts[top[0]] += 1
        return top

    # Night Owl Award
    night_owls = [(p['username'], p['stats']['night_owl_score'])
                  for p in all_person_stats if p]
    winner = get_diverse_winner(night_owls, 'night_owl')
    awards['night_owl'] = {
        'winner': winner[0],
        'display_name': USERNAME_MAP.get(winner[0], winner[0]),
        'score': winner[1],
        'description': f"{winner[1]*100:.1f}% of messages after midnight"
    }

    # Early Bird Award
    early_birds = [(p['username'], p['stats']['early_bird_score'])
                   for p in all_person_stats if p]
    winner = get_diverse_winner(early_birds, 'early_bird')
    awards['early_bird'] = {
        'winner': winner[0],
        'display_name': USERNAME_MAP.get(winner[0], winner[0]),
        'score': winner[1],
        'description': f"{winner[1]*100:.1f}% of messages 5am-7am"
    }

    # Emoji Champion
    emoji_users = [(p['username'], p['stats']['emoji_rate'])
                   for p in all_person_stats if p]
    winner = get_diverse_winner(emoji_users, 'emoji_champion')
    awards['emoji_champion'] = {
        'winner': winner[0],
        'display_name': USERNAME_MAP.get(winner[0], winner[0]),
        'rate': winner[1],
        'description': f"{winner[1]:.2f} emojis per message"
    }

    # Question Asker
    questioners = [(p['username'], p['stats']['question_rate'])
                   for p in all_person_stats if p]
    winner = get_diverse_winner(questioners, 'question_asker')
    awards['question_asker'] = {
        'winner': winner[0],
        'display_name': USERNAME_MAP.get(winner[0], winner[0]),
        'rate': winner[1],
        'description': f"{winner[1]*100:.1f}% of messages contain '?'"
    }

    # CAPS LOCK ENTHUSIAST
    caps_users = [(p['username'], p['stats']['caps_rate'])
                  for p in all_person_stats if p]
    winner = get_diverse_winner(caps_users, 'caps_lock')
    awards['caps_lock'] = {
        'winner': winner[0],
        'display_name': USERNAME_MAP.get(winner[0], winner[0]),
        'rate': winner[1],
        'description': f"{winner[1]*100:.1f}% of messages in ALL CAPS"
    }

    # Conversation Killer (find message with longest silence after)
    # This requires checking gaps between messages
    longest_gap = 0
    killer_message = None
    for i, msg in enumerate(messages[:-1]):
        gap_seconds = (messages[i+1]['_datetime'] - msg['_datetime']).total_seconds()
        if gap_seconds > longest_gap:
            longest_gap = gap_seconds
            killer_message = msg

    if killer_message:
        gap_hours = round(longest_gap / 3600, 1)
        awards['conversation_killer'] = {
            'winner': killer_message['author'],
            'display_name': USERNAME_MAP.get(killer_message['author'], killer_message['author']),
            'gap_hours': gap_hours,
            'message_preview': killer_message['content'][:200],
            'timestamp': killer_message['timestamp'],
            'description': f"Silenced the chat for {gap_hours} hours with one message."
        }

    # Aproposter Award (Most Random / High Variance)
    # We'll use variance in message length as a proxy for "randomness" or "unpredictability"
    # Users with high variance likely post both short quips and long rants, or images and text mixed.
    variance_scores = []
    for p in all_person_stats:
        if not p: continue
        username = p['username']
        # Calculate variance of message lengths
        user_msgs = [len(m['content']) for m in messages if m['author'] == username]
        if len(user_msgs) > 50:
            mean_len = sum(user_msgs) / len(user_msgs)
            variance = sum((x - mean_len) ** 2 for x in user_msgs) / len(user_msgs)
            variance_scores.append((username, variance))
    
    winner = get_diverse_winner(variance_scores, 'aproposter')
    awards['aproposter'] = {
        'winner': winner[0],
        'display_name': USERNAME_MAP.get(winner[0], winner[0]),
        'score': int(winner[1]),
        'description': "Most unpredictable posting patterns (High Variance)"
    }

    # Katamari Damacy (Conversation Starter)
    # Score = unique responders per post
    katamari_scores = []
    
    # Pre-compute message author map
    msg_id_to_author = {m['id']: m['author'] for m in messages}
    
    for p in all_person_stats:
        if not p: continue
        username = p['username']
        
        my_posts = 0
        unique_responders = set()
        
        # Find all messages by this user
        for m in messages:
            if m['author'] == username:
                my_posts += 1
                
        # Find all replies TO this user
        # This is expensive O(N), let's optimize if needed. 
        # Actually we can iterate messages once.
        pass

    # Optimized Katamari
    author_engagement = defaultdict(lambda: {'posts': 0, 'unique_responders': set()})
    for m in messages:
        author = m['author']
        author_engagement[author]['posts'] += 1
        
        ref = m.get('reference')
        if ref and isinstance(ref, dict):
            ref_id = ref.get('message_id')
            original_author = msg_id_to_author.get(ref_id)
            if original_author and original_author != author:
                author_engagement[original_author]['unique_responders'].add(author)
                
    for username, stats in author_engagement.items():
        if stats['posts'] > 100:
            score = len(stats['unique_responders']) / stats['posts']
            katamari_scores.append((username, score))
            
    if katamari_scores:
        winner = get_diverse_winner(katamari_scores, 'katamari')
        awards['katamari'] = {
            'winner': winner[0],
            'display_name': USERNAME_MAP.get(winner[0], winner[0]),
            'score': winner[1],
            'description': f"Attracted {len(author_engagement[winner[0]]['unique_responders'])} unique responders"
        }

    return awards


# === CONVERSATION SESSIONS ===

def compute_conversation_sessions(messages, gap_minutes=20):
    """
    Group messages into sessions where the gap between messages is less than gap_minutes.
    Returns list of sessions with metadata.
    """
    print(f"Computing conversation sessions (gap={gap_minutes}m)...")
    
    if not messages:
        return []
        
    sessions = []
    current_session = [messages[0]]
    
    for i in range(1, len(messages)):
        prev_msg = messages[i-1]
        curr_msg = messages[i]
        
        gap = (curr_msg['_datetime'] - prev_msg['_datetime']).total_seconds() / 60
        
        if gap <= gap_minutes:
            current_session.append(curr_msg)
        else:
            # Session ended
            sessions.append(_process_session(current_session))
            current_session = [curr_msg]
            
    # Add last session
    if current_session:
        sessions.append(_process_session(current_session))
        
    # Sort by duration
    sessions.sort(key=lambda s: s['duration_minutes'], reverse=True)
    
    return sessions

STOP_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
    'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
    'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
    'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well',
    'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us', 'is', 'are', 'was', 'were', 'has', 'had', 'been'
}

def _process_session(messages):
    """Extract metadata from a list of messages in a session."""
    start = messages[0]['_datetime']
    end = messages[-1]['_datetime']
    duration = (end - start).total_seconds() / 60
    
    authors = Counter(m['author'] for m in messages)
    
    # improved preview: join first few messages until length is decent
    preview_text = ""
    for m in messages[:3]:
        content = m['content']
        if not content: continue
        if len(preview_text) + len(content) > 200:
            preview_text += content[:200-len(preview_text)] + "..."
            break
        preview_text += content + " "
    
    if not preview_text:
        preview_text = "Image/Attachment only"

    # Extract deep link data from first message
    first_msg = messages[0]
    deep_link_data = {
        'channel_id': first_msg.get('channel_id'),
        'message_id': first_msg.get('id')
    }

    # Inside Joke Detection (Simple keyword matching for now)
    # User can expand this list later
    INSIDE_JOKE_TERMS = set(joke.lower() for joke in get_inside_jokes()) | {get_server_name().lower()}
    is_inside_joke = False
    session_text = " ".join(m['content'].lower() for m in messages)
    if any(term in session_text for term in INSIDE_JOKE_TERMS):
        is_inside_joke = True

    return {
        'start_time': start.isoformat(),
        'end_time': end.isoformat(),
        'duration_minutes': round(duration, 1),
        'message_count': len(messages),
        'unique_authors': len(authors),
        'top_participants': [
            {'username': k, 'count': v} 
            for k, v in authors.most_common(3)
        ],
        'preview': preview_text.strip(),
        'deep_link': deep_link_data,
        'channel_name': first_msg.get('channel_name', 'unknown-channel'),
        'is_inside_joke': is_inside_joke
    }


# === MAIN ===

def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_basic_stats.py discord_messages.json")
        sys.exit(1)

    filepath = sys.argv[1]

    # Load data
    messages, raw_data = load_messages(filepath)

    # Compute server-wide stats
    server_stats = compute_server_stats(messages)

    # Compute leaderboards
    leaderboards = compute_leaderboards(messages)

    # Build message ID lookup once (performance optimization)
    print("\nBuilding message ID map...")
    msg_author_map = {m['id']: m['author'] for m in messages}

    # Compute per-person stats
    print("Computing per-person stats...")
    all_person_stats = []
    for username in USERNAME_MAP.keys():
        person_stats = compute_person_stats(messages, username, msg_author_map)
        if person_stats:
            all_person_stats.append(person_stats)

    # Compute basic awards
    awards = compute_basic_awards(messages, all_person_stats)

    # === OUTPUT ===

    # Group wrapped
    guild_info = raw_data.get('guild', {})
    guild_id = guild_info.get('id', 'UNKNOWN_GUILD_ID')
    
    group_output = {
        'metadata': {
            'year': 2025,
            'generated_at': datetime.now().isoformat(),
            'source_file': filepath,
            'guild_id': guild_id,
            'guild_name': guild_info.get('name', 'Unknown Server')
        },
        'server_stats': server_stats,
        'leaderboards': leaderboards,
        'awards': awards
    }

    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    # Save group wrapped
    group_file = output_dir / 'group_wrapped.json'
    with open(group_file, 'w', encoding='utf-8') as f:
        json.dump(group_output, f, indent=2, default=str)
    print(f"\n✅ Saved: {group_file}")

    # Save individual wrapped files
    for person in all_person_stats:
        person_file = output_dir / f"wrapped_{person['username']}.json"
        with open(person_file, 'w', encoding='utf-8') as f:
            json.dump(person, f, indent=2, default=str)
        print(f"✅ Saved: {person_file}")

    # Summary
    print("\n" + "="*60)
    print("BASIC STATS COMPUTATION COMPLETE")
    print("="*60)
    print(f"Total messages analyzed: {len(messages):,}")
    print(f"People: {len(all_person_stats)}")
    print(f"Output files: {len(all_person_stats) + 1}")
    print(f"Location: {output_dir.absolute()}")
    print("="*60)


if __name__ == "__main__":
    main()
