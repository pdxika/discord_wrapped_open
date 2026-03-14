#!/usr/bin/env python3
"""
Compute final LLM-based awards that require sophisticated analysis:
1. Taylor Swift Award - Foreshadowing (hints way before reveals)
2. 2001: Space Odyscord - Growth + Old/Youthful paradox
3. Jeff Toole Award - Most tagged/mentioned (Deterministic + LLM blurb)
4. Die Hard Award - Most like Bruce Willis (Resilient/Sarcastic)
5. Secretary of Holidays - Most holiday mentions (Deterministic + LLM blurb)
"""

import json
import sys
import random
import re
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

import os
from dotenv import load_dotenv
from config import get_username_map, get_llm_model

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("ERROR: anthropic package not installed")
    sys.exit(1)

# Load environment variables
load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')

if not api_key:
    print("WARNING: ANTHROPIC_API_KEY not found")


USERNAME_MAP = get_username_map()

def load_messages():
    """Load messages."""
    with open('discord_messages.json', 'r') as f:
        data = json.load(f)
    
    messages = []
    if 'messages' in data:
        messages = data['messages']
    elif isinstance(data, list):
        for s in data:
            for m in s.get('messages', []):
                messages.append(m)
                
    print(f"Loaded {len(messages)} messages for analysis.")
    return messages

def load_existing_winners():
    """Load winners from basic stats to ensure diversity."""
    try:
        with open('output/group_wrapped.json', 'r') as f:
            data = json.load(f)
            awards = data.get('awards', {})
            winner_counts = {}
            for award in awards.values():
                w = award.get('winner')
                if w:
                    winner_counts[w] = winner_counts.get(w, 0) + 1
            return winner_counts
    except FileNotFoundError:
        return {}

def get_llm_response(client, prompt, model="claude-sonnet-4-5-20250929"):
    """Helper to get JSON response from Claude."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        
        # Debug: Print raw text if it fails
        # print(f"DEBUG LLM RESPONSE:\n{text}\n")
        
        # Strip markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        print(f"LLM Error: {e}")
        # Fallback for testing/error
        return {
            "winner": "Unknown",
            "reasoning": "The AI refused to answer (JSON Error), winner could not be determined.",
            "runner_up": "Unknown",
            "runner_up_reasoning": "Runner up could not be determined."
        }

# === 1. TAYLOR SWIFT AWARD (Foreshadowing) ===
def compute_taylor_swift_award(client, messages):
    print("\nComputing Taylor Swift Award (Foreshadowing)...")
    return {
        "winner": "TBD",
        "display_name": "Pending Analysis",
        "description": "The user is conducting a separate investigation to identify the true prophet of the server.",
        "runner_up": "N/A",
        "runner_up_description": "N/A"
    }

# === 2. 2001: A SPACE ODYSCORD (Growth + Paradox) ===
def compute_space_odyscord_award(client, messages):
    print("\nComputing 2001: A Space Odyscord Award...")
    
    # Sample messages from start and end of year for each person
    samples_text = ""
    for username in USERNAME_MAP.keys():
        user_msgs = [m for m in messages if m.get('author') == username]
        if not user_msgs: continue
        
        # Sort by time
        user_msgs.sort(key=lambda x: x.get('timestamp', ''))
        
        early = user_msgs[:10]
        late = user_msgs[-10:]
        middle = random.sample(user_msgs[10:-10], min(len(user_msgs)-20, 10)) if len(user_msgs) > 20 else []
        
        display_name = USERNAME_MAP[username]
        samples_text += f"\n\n{display_name}:\n"
        for m in early + middle + late:
            samples_text += f"[{m.get('timestamp', '')[:10]}] {m['content'][:150]}\n"

    prompt = f"""Analyze these messages for the "2001: A Space Odyscord" Award.
    CRITERIA: Someone who showed TONS of personal growth and reflection, and was also just very 'old' but also 'youthful' at the same time (The Star Child Paradox).
    
    Look for:
    - Deep philosophical reflection mixed with childish humor.
    - Significant change in tone from start of year to end.
    - "Old soul" energy but "young heart" vibes.
    
    MESSAGES:
    {samples_text}
    
    Respond in JSON:
    {{
      "winner": "Display Name",
      "reasoning": "Explain their growth arc and the 'Old yet Youthful' paradox.",
      "runner_up": "Display Name",
      "runner_up_reasoning": "Reasoning for runner up."
    }}
    """
    return get_llm_response(client, prompt)

# === 3. JEFF TOOLE AWARD (Most Tagged) ===
def compute_jeff_toole_award(client, messages):
    print("\nComputing Jeff Toole Award (Most Tagged)...")
    
    mention_counts = Counter()
    
    for m in messages:
        # The JSON has a 'mentions' array with usernames!
        # e.g. "mentions": ["username1", "username2"]
        mentions = m.get('mentions', [])
        for mentioned_username in mentions:
            # Map username to display name
            if mentioned_username in USERNAME_MAP:
                display_name = USERNAME_MAP[mentioned_username]
                mention_counts[display_name] += 1

    if not mention_counts:
        winner = "Ian"
        count = 0
    else:
        winner, count = mention_counts.most_common(1)[0]
        
    print(f"Winner: {winner} with {count} mentions.")
    
    # Get LLM to write the blurb
    prompt = f"""Write a short, funny award blurb for {winner} who won the "Jeff Toole Award" for never being forgotten.
    They were tagged/mentioned {count} times by other users this year.
    Make it sound like a prestigious but slightly annoying honor.
    
    Respond in JSON:
    {{
      "winner": "{winner}",
      "reasoning": "The blurb text...",
      "runner_up": "N/A", 
      "runner_up_reasoning": "No one else was this unforgettable."
    }}
    """
    return get_llm_response(client, prompt)

# === 4. DIE HARD AWARD (Bruce Willis Vibe) ===
def compute_die_hard_award(client, messages):
    print("\nComputing Die Hard Award...")
    
    # Sample "complaining" or "intense" messages
    keywords = ["tired", "work", "hard", "fix", "broken", "why", "god", "damn", "seriously", "yippee"]
    candidates = defaultdict(list)
    
    for m in messages:
        content = m.get('content', '').lower()
        if any(k in content for k in keywords):
            candidates[m['author']].append(m)
            
    samples_text = ""
    for username, msgs in candidates.items():
        if username not in USERNAME_MAP: continue
        display_name = USERNAME_MAP[username]
        samples_text += f"\n\n{display_name}:\n"
        selected = random.sample(msgs, min(len(msgs), 15))
        for msg in selected:
             samples_text += f"- {msg['content'][:150]}\n"

    prompt = f"""Analyze these messages for the "Die Hard Award".
    CRITERIA: The person most like Bruce Willis in Die Hard.
    - Resilient but constantly complaining.
    - Sarcastic under pressure.
    - Always in the wrong place at the wrong time.
    - "I'm too old for this" energy.
    
    MESSAGES:
    {samples_text}
    
    Respond in JSON:
    {{
      "winner": "Display Name",
      "reasoning": "Explain why they are the John McClane of the server.",
      "runner_up": "Display Name",
      "runner_up_reasoning": "Reasoning for runner up."
    }}
    """
    return get_llm_response(client, prompt)

# === 5. SECRETARY OF HOLIDAYS (Most Holiday Mentions) ===
def compute_secretary_of_holidays_award(client, messages):
    print("\nComputing Secretary of Holidays Award...")
    
    holidays = ["christmas", "xmas", "thanksgiving", "halloween", "easter", "holiday", "new year", "festive", "santa", "turkey", "spooky"]
    counts = Counter()
    
    for m in messages:
        content = m.get('content', '').lower()
        author = m.get('author')
        if author not in USERNAME_MAP: continue
        
        for h in holidays:
            if h in content:
                counts[USERNAME_MAP[author]] += 1
                
    if not counts:
        winner = "Ian"
        count = 0
    else:
        winner, count = counts.most_common(1)[0]
        
    print(f"Winner: {winner} with {count} holiday mentions.")
    
    prompt = f"""Write a short, festive award blurb for {winner} who won the "Secretary of Holidays Award".
    They mentioned holidays {count} times this year.
    Describe them as the server's official party planner / holiday enthusiast.
    
    Respond in JSON:
    {{
      "winner": "{winner}",
      "reasoning": "The blurb text...",
      "runner_up": "N/A",
      "runner_up_reasoning": "The Grinch (everyone else)."
    }}
    """

    return get_llm_response(client, prompt)

# === NEW LLM AWARDS ===

def compute_bunny_lebowski_award(client, messages):
    """Bunny Lebowski Award (Most Nihilistic)."""
    print("\nComputing Bunny Lebowski Award (Nihilism)...")
    prompt = f"""
    Analyze the chat history to find the user who is the most NIHILISTIC.
    Award: "Bunny Lebowski Award"
    
    Look for:
    - "Nothing matters" attitude
    - Existential dread
    - Cynicism about the future
    - "We believe in nothing, Lebowski" energy
    
    Candidates: {list(USERNAME_MAP.values())}
    
    Return JSON:
    {{
      "winner": "Username",
      "reasoning": "Explanation of their nihilism...",
      "runner_up": "Runner Up Username",
      "runner_up_reasoning": "Explanation..."
    }}
    """
    return get_llm_response(client, prompt)

def compute_breck_garrett_award(client, messages):
    """Breck Garrett Award (Toxic Positivity)."""
    print("\nComputing Breck Garrett Award (Toxic Positivity)...")
    prompt = f"""
    Analyze the chat history to find the user with the most TOXIC POSITIVITY.
    Award: "Breck Garrett Award"
    
    Look for:
    - Relentless optimism even when inappropriate
    - "Good vibes only" attitude
    - Dismissing negative feelings
    - Corporate speak / LinkedIn influencer energy
    
    Candidates: {list(USERNAME_MAP.values())}
    
    Return JSON:
    {{
      "winner": "Username",
      "reasoning": "Explanation of their toxic positivity...",
      "runner_up": "Runner Up Username",
      "runner_up_reasoning": "Explanation..."
    }}
    """
    return get_llm_response(client, prompt)

def compute_phoebe_bridgers_award(client, messages):
    """Phoebe Bridgers Award (Emotional Motion Sickness)."""
    print("\nComputing Phoebe Bridgers Award (Sad/Emo)...")
    prompt = f"""
    Analyze the chat history to find the user who is the most "Emo" or "Sad".
    Award: "Phoebe Bridgers Award"
    
    Look for:
    - Crying in the club energy
    - Emotional dumping
    - Melancholy lyrics or vibes
    - "I have emotional motion sickness"
    
    Candidates: {list(USERNAME_MAP.values())}
    
    Return JSON:
    {{
      "winner": "Username",
      "reasoning": "Explanation of their sad girl autumn vibes...",
      "runner_up": "Runner Up Username",
      "runner_up_reasoning": "Explanation..."
    }}
    """
    return get_llm_response(client, prompt)

def compute_her_award(client, messages):
    """HER Award (Digital to Real Life)."""
    print("\nComputing HER Award (Digital -> Real)...")
    prompt = f"""
    Analyze the chat history to find the user who most often turns digital conversations into real-life actions.
    Award: "HER Award" (Like the movie Her, but reverse - digital becoming real)
    
    Look for:
    - "I saw this on discord so I bought it"
    - "We talked about this and now I'm doing it"
    - Meeting up with internet friends
    - Taking advice from the chat
    
    Candidates: {list(USERNAME_MAP.values())}
    
    Return JSON:
    {{
      "winner": "Username",
      "reasoning": "Explanation of their digital-to-real manifestations...",
      "runner_up": "Runner Up Username",
      "runner_up_reasoning": "Explanation..."
    }}
    """
    return get_llm_response(client, prompt)

def compute_aproposter_award(client, messages):
    """
    Find the user with the highest variance in message length (most unpredictable).
    Then ask LLM to describe why they are the "Aproposter".
    """
    print("\nComputing Aproposter Award (High Variance)...")
    
    # 1. Calculate Variance
    variance_scores = []
    
    # Group messages by user
    user_msgs = defaultdict(list)
    for m in messages:
        user_msgs[m['author']].append(len(m.get('content', '')))
        
    for username, lengths in user_msgs.items():
        if len(lengths) > 50: # Minimum sample size
            mean_len = sum(lengths) / len(lengths)
            variance = sum((x - mean_len) ** 2 for x in lengths) / len(lengths)
            variance_scores.append((username, variance))
            
    if not variance_scores:
        return None
        
    # Find winner by highest variance
    variance_scores.sort(key=lambda x: x[1], reverse=True)
    winner_username, score = variance_scores[0]
            
    winner_display = USERNAME_MAP.get(winner_username, winner_username)
    
    print(f"Winner: {winner_display} with variance {int(score)}")
    
    # 2. Get LLM Description
    # Get a sample of their short and long messages to show duality
    winner_msgs = [m for m in messages if m['author'] == winner_username]
    winner_msgs.sort(key=lambda m: len(m.get('content', '')))
    
    shortest = [m['content'] for m in winner_msgs[:3]]
    longest = [m['content'] for m in winner_msgs[-3:]]
    
    prompt = f"""
    The user '{winner_display}' has won the "Aproposter Award" for the most unpredictable posting patterns (highest variance in message length).
    
    They post tiny messages like:
    {json.dumps(shortest, indent=2)}
    
    But also massive walls of text like:
    {json.dumps(longest, indent=2)}
    
    Write a funny, 2-sentence description of why they won this award. Focus on their chaotic range from "one word" to "novel writer".
    
    Respond in JSON format only:
    {{
        "description": "Your funny description here..."
    }}
    """
    
    response = get_llm_response(client, prompt)
    description = "Most unpredictable posting patterns."
    if response and isinstance(response, dict):
        description = response.get('description', response.get('reasoning', description))
    elif response and isinstance(response, str):
        description = response
        
    return {
        'winner': winner_display, # Display name for consistency
        'username': winner_username, # Keep username for ID
        'description': description,
        'score': int(score)
    }

def main():
    print("Awards are frozen. Using existing output/final_awards.json.")
    # To re-enable, revert this file or manually edit the JSON.

if __name__ == "__main__":
    main()
