import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import compute_basic_stats
import pandas as pd
import sys
import io
import anthropic
from dotenv import load_dotenv
from config import get_username_map, get_server_name, get_guild_id, get_bot_persona_name, has_anthropic_key, is_llm_enabled

load_dotenv()
TITLES_CACHE_FILE = "titles_cache.json"
TITLES_CACHE = {}

def load_titles_cache():
    global TITLES_CACHE
    if os.path.exists(TITLES_CACHE_FILE):
        try:
            with open(TITLES_CACHE_FILE, 'r') as f:
                TITLES_CACHE = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load titles cache: {e}")

def save_titles_cache():
    try:
        with open(TITLES_CACHE_FILE, 'w') as f:
            json.dump(TITLES_CACHE, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save titles cache: {e}")

def get_ai_title(event_id, preview_text, message_count):
    """Generate a witty title for a timeline event using Claude."""
    if event_id in TITLES_CACHE:
        return TITLES_CACHE[event_id]
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return f"{message_count} Messages"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""
        You are {get_bot_persona_name()}, a witty Discord historian.
        I have a conversation session with {message_count} messages.
        Here is a preview of the start: "{preview_text}"
        
        Generate a short, funny, or intriguing title for this event (max 6 words).
        It should capture the vibe. If it's about Thanksgiving, say something like "Viscous Cranberry Dreams".
        If it's just chatting, make it sound epic.
        
        Return ONLY the title. No quotes.
        """
        
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        title = message.content[0].text.strip()
        TITLES_CACHE[event_id] = title
        save_titles_cache()
        return title
    except Exception as e:
        logger.error(f"Failed to generate title: {e}")
        return f"{message_count} Messages"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATA_FILE = "discord_messages.json"

# Global data storage
DATA_STORE = {
    "messages": [],
    "msg_author_map": {},
    "server_stats": {},
    "leaderboards": {},
    "awards": {},
    "person_stats": {},
    "sessions": [],
    "df": None  # Pandas DataFrame
}

# ... (load_data function) ...

def load_data():
    """Load data and compute initial stats on startup."""
    load_titles_cache()
    if not os.path.exists(DATA_FILE):
        logger.error(f"Data file {DATA_FILE} not found!")
        return

    logger.info(f"Loading messages from {DATA_FILE}...")
    messages, _ = compute_basic_stats.load_messages(DATA_FILE)
    DATA_STORE["messages"] = messages
    
    # Build map for fast lookups
    # Build map for fast lookups
    DATA_STORE["msg_author_map"] = {m['id']: m['author'] for m in messages}
    
    # Build Username -> ID map (reverse of what we might need, but useful for mentions)
    # We need to find the author ID for each username. 
    # Since we don't have a direct map, we can infer it if the export structure allows, 
    # OR we can just tell the bot to search for the username string if IDs aren't available.
    # But wait, Discord export usually puts the ID in the 'author' object. 
    # If 'author' is just a string in our loaded data, we might have lost the ID.
    # Let's check if we can find IDs in the content or if we have to rely on text.
    # Actually, let's just provide the bot with the best info we have.
    
    # Create DataFrame for Analysis
    logger.info("Creating Pandas DataFrame...")
    df = pd.DataFrame(messages)
    # Ensure datetime is timezone-naive or consistent
    df['_datetime'] = pd.to_datetime(df['_datetime'], utc=True).dt.tz_convert(None)
    df['timestamp'] = df['_datetime'] # Alias for easier coding
    
    # Add display name column
    def get_display_name(username):
        for u, d in get_username_map().items():
            if u == username: return d
        return username
    
    df['user'] = df['author'].apply(get_display_name)
    DATA_STORE["df"] = df
    
    logger.info("Computing initial stats...")
    DATA_STORE["server_stats"] = compute_basic_stats.compute_server_stats(messages)
    DATA_STORE["leaderboards"] = compute_basic_stats.compute_leaderboards(messages)
    
    # Compute stats for all users
    all_person_stats = []
    for username in get_username_map().keys():
        p_stats = compute_basic_stats.compute_person_stats(messages, username, DATA_STORE["msg_author_map"])
        if p_stats:
            DATA_STORE["person_stats"][username] = p_stats
            all_person_stats.append(p_stats)
            
    DATA_STORE["awards"] = compute_basic_stats.compute_basic_awards(messages, all_person_stats)
    
    # Load LLM-generated awards
    try:
        final_awards_file = "output/final_awards.json"
        if os.path.exists(final_awards_file):
            with open(final_awards_file, 'r') as f:
                final_awards_list = json.load(f)
                # final_awards.json is a list of dicts: [{"award_id": "...", ...}]
                # We need to add them to DATA_STORE["awards"] keyed by award_id
                for award in final_awards_list:
                    DATA_STORE["awards"][award['award_id']] = award
                logger.info(f"Loaded {len(final_awards_list)} final awards.")
    except Exception as e:
        logger.error(f"Failed to load final awards: {e}")

    # Load LLM Analysis (Personas)
    try:
        llm_analysis_file = "output/llm_analysis.json"
        if os.path.exists(llm_analysis_file):
            with open(llm_analysis_file, 'r') as f:
                DATA_STORE["llm_analysis"] = json.load(f)
                logger.info("Loaded LLM analysis.")
    except Exception as e:
        logger.error(f"Failed to load LLM analysis: {e}")
    
    logger.info("Computing conversation sessions...")
    sessions = compute_basic_stats.compute_conversation_sessions(messages)
    DATA_STORE["sessions"] = sessions
    
    logger.info("Data loading and computation complete!")

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "messages_loaded": len(DATA_STORE["messages"])})

@app.route('/api/config', methods=['GET'])
def get_app_config():
    """Return app configuration for the frontend."""
    return jsonify({
        "server_name": get_server_name(),
        "bot_persona_name": get_bot_persona_name(),
        "llm_enabled": is_llm_enabled(),
        "guild_id": get_guild_id()
    })

@app.route('/api/stats/group', methods=['GET'])
def get_group_stats():
    """Return server-wide stats, leaderboards, and awards."""
    return jsonify({
        "server_stats": DATA_STORE["server_stats"],
        "leaderboards": DATA_STORE["leaderboards"],
        "awards": DATA_STORE["awards"],
        "llm_analysis": DATA_STORE.get("llm_analysis", {}),
        "top_sessions": DATA_STORE["sessions"][:10] if "sessions" in DATA_STORE else []
    })

@app.route('/api/vector_space', methods=['GET'])
def get_vector_space():
    """Return vector space data for visualization."""
    try:
        output_file = "output/vector_space.json"
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                data = json.load(f)
            return jsonify(data)
        else:
            return jsonify({"error": "Vector space data not found. Run compute_embeddings.py first."}), 404
    except Exception as e:
        logger.error(f"Error serving vector space: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/timeline/disruption/<username>', methods=['GET'])
def get_timeline_disruption(username):
    """
    Compute 'What If' stats by removing a user.
    """
    # Resolve username
    target_user = username
    for u, d in get_username_map().items():
        if d.lower() == username.lower():
            target_user = u
            break
            
    if target_user not in DATA_STORE["person_stats"]:
         return jsonify({"error": "User not found"}), 404

    logger.info(f"Computing timeline disruption for {target_user}...")
    
    df = DATA_STORE["df"]
    
    # Filter out user to calculate impact
    df_without = df[df['author'] != target_user]
    
    try:
        # 1. Calculate "Lost Conversations"
        # Find sessions where this user was the top participant (or > 30% of messages)
        sessions = DATA_STORE.get("sessions", [])
        lost_sessions = []
        
        for s in sessions:
            # Check if user is in top participants
            is_top = False
            user_count = 0
            for p in s['top_participants']:
                if p['username'] == target_user:
                    is_top = True
                    user_count = p['count']
                    break
            
            if is_top and (user_count / s['message_count'] > 0.3):
                lost_sessions.append(s)
                
        # Sort by message count to find the biggest losses
        lost_sessions.sort(key=lambda x: x['message_count'], reverse=True)
        top_lost_session = lost_sessions[0] if lost_sessions else None
        
        # 2. Calculate "Lost Topics" (Unique Vocabulary)
        # Find words this user uses much more than average
        # We can use the person_stats if available, or compute on the fly
        user_stats = DATA_STORE["person_stats"].get(target_user)
        lost_topics = []
        
        if user_stats:
            # Get user's top words
            user_words = user_stats.get('stats', {}).get('vocabulary', [])
            # Compare with server top words (we don't have this pre-computed easily, so let's just pick their top 3 unique-ish ones)
            # Actually, let's just use their top 3 words that aren't super common stop words
            # For now, just take their top 5 distinctive words
            lost_topics = [w for w in user_words[:5]]

        # 3. Ian's Commentary (The Eulogy) & Smart Topic Analysis
        import anthropic
        from dotenv import load_dotenv
        import json
        load_dotenv()
        api_key = os.getenv('ANTHROPIC_API_KEY')

        commentary = f"{get_bot_persona_name()} is offline."
        
        if api_key:
            try:
                client = anthropic.Anthropic(api_key=api_key)
                
                lost_convo_desc = "None"
                if top_lost_session:
                    lost_convo_desc = f"A {top_lost_session['message_count']}-message debate about '{top_lost_session['preview']}'"
                    
                # Get a sample of the user's messages to help identify topics
                user_sample = ""
                if user_stats:
                    # Try to get some actual message content if available in stats, otherwise rely on vocabulary
                    vocab_str = ", ".join(user_stats.get('stats', {}).get('vocabulary', [])[:20])
                    user_sample = f"Top words: {vocab_str}"

                prompt = f"""You are {get_bot_persona_name()}, the cynical server bot.
                User '{username}' has been removed from the timeline.
                
                IMPACT REPORT:
                - Messages Vanished: {len(df) - len(df_without)}
                - Major Conversation Lost: {lost_convo_desc}
                - User's Vibe/Vocabulary: {user_sample}
                
                Task:
                1. Identify 3-5 specific "Lost Topics" or obsessions that would disappear with this user. Be creative and specific (e.g. "Ranting about bad drivers", "Obscure 80s movies", "Typing in all caps").
                2. Write a short, 2-sentence summary of this "Darkest Timeline". Focus on the SPECIFIC loss. Be dramatic but grounded.
                
                Respond in JSON:
                {{
                    "lost_topics": ["Topic 1", "Topic 2", "Topic 3"],
                    "commentary": "The commentary text..."
                }}
                """
                
                resp = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                text = resp.content[0].text.strip()
                if text.startswith("```json"): text = text[7:]
                if text.startswith("```"): text = text[3:]
                if text.endswith("```"): text = text[:-3]
                
                result = json.loads(text.strip())
                commentary = result.get("commentary", commentary)
                
                # Update lost_topics with the smarter LLM ones
                if result.get("lost_topics"):
                    lost_topics = result["lost_topics"]
                    
            except Exception as e:
                logger.error(f"Error generating commentary/topics: {e}")
                commentary = "Ian refused to comment on this timeline."

        # 4. Calculate Average Reply Time Delta
        # This is expensive to compute perfectly, so let's estimate using message density
        # Messages per hour? Or just use a simple heuristic:
        # If we remove a high-frequency user, the "pace" slows down.
        
        # Let's try a simple "Average gap between messages"
        # We need to sort by timestamp first (df is already sorted)
        
        # Original Gap
        # (End - Start) / (Count - 1)
        duration_seconds = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
        avg_gap_original = duration_seconds / len(df) if len(df) > 0 else 0
        
        # New Gap
        avg_gap_new = duration_seconds / len(df_without) if len(df_without) > 0 else 0
        
        # Delta in minutes
        avg_reply_time_delta = round((avg_gap_new - avg_gap_original) / 60, 1)
        
        # 5. Vibe Shift (Mocked based on user stats for now, or random witty one)
        vibe_shifts = [
            "Significantly Less Chaotic",
            "Uncomfortably Quiet",
            "More Professional (Boring)",
            "Lacking Artistic Vision",
            "Statistically Less Funny",
            "80% Less Caps Lock",
            "Grammatically Improved",
            "Less Passive Aggressive"
        ]
        import random
        sentiment_shift = random.choice(vibe_shifts)

        # Recompute basic server stats for the "without" view
        original = DATA_STORE["server_stats"]
        
        # We need to convert df_without back to list of dicts for compute_server_stats
        # Or update compute_server_stats to accept DataFrame. 
        # Actually compute_server_stats takes 'messages' (list of dicts).
        # Let's convert df_without back to messages list.
        messages_without = df_without.to_dict('records')
        new_stats = compute_basic_stats.compute_server_stats(messages_without)
        
        diff = {
            "message_count_delta": int(len(df_without) - len(df)),
            "lost_conversations_count": len(lost_sessions),
            "top_lost_conversation": top_lost_session,
            "lost_topics": lost_topics,
            "commentary": commentary,
            "avg_reply_time_delta": avg_reply_time_delta,
            "sentiment_shift": sentiment_shift
        }
        
        return jsonify({
            "original": original,
            "new_stats": new_stats,
            "diff": diff
        })
    except Exception as e:
        logger.error(f"Error in timeline disruption: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def _generate_eras(start_date, end_date):
    """Auto-generate quarterly era labels from data range."""
    colors = ["#3b82f6", "#eab308", "#ef4444", "#10b981"]
    labels = ["Act I", "Act II", "Act III", "Act IV"]
    total_days = (end_date - start_date).days
    quarter_days = max(1, total_days // 4)
    eras = []
    current = start_date
    for i in range(4):
        era_end = current + timedelta(days=quarter_days) if i < 3 else end_date
        eras.append({
            "label": labels[i],
            "start": current.strftime("%Y-%m-%d"),
            "end": era_end.strftime("%Y-%m-%d"),
            "color": colors[i]
        })
        current = era_end
    return eras

@app.route('/api/timeline/master', methods=['GET'])
def get_master_timeline():
    """
    Return timeline data for the "Actual Line" visualization.
    Strictly Nov 2024 - Nov 2025.
    Returns a list of "Events" (sessions) and "Stats" (milestones).
    """
    sessions = DATA_STORE.get("sessions", [])
    if not sessions:
        return jsonify({"error": "Data not loaded"}), 500
        
    # Compute date range from actual data
    messages = DATA_STORE.get("messages", [])
    if messages:
        start_date = messages[0]['_datetime'].replace(day=1)
        end_date = messages[-1]['_datetime']
    else:
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2025, 12, 31)
    
    timeline_events = []
    
    for s in sessions:
        s_date = datetime.fromisoformat(s['start_time'])
        if start_date <= s_date <= end_date:
            # Only include significant sessions (e.g., > 100 messages) to avoid clutter
            if s['message_count'] > 100:
                # Use cached title or default. Background thread will fill cache.
                ai_title = TITLES_CACHE.get(s['start_time'], f"{s['message_count']} Messages")
                
                timeline_events.append({
                    "type": "event",
                    "date": s['start_time'],
                    "title": ai_title,
                    "preview": s['preview'],
                    "participants": [p['username'] for p in s['top_participants']],
                    "id": s['start_time'], # simple ID
                    "deep_link": s.get('deep_link'),
                    "channel_name": s.get('channel_name')
                })
    
    # Sort by date
    timeline_events.sort(key=lambda x: x['date'])
    
    # Get Guild ID from env or metadata
    guild_id = os.getenv("DISCORD_GUILD_ID")
    if not guild_id:
        metadata = DATA_STORE.get("metadata", {})
        guild_id = metadata.get("guild_id", "UNKNOWN_GUILD_ID")

    return jsonify({
        "timeline": timeline_events,
        "guild_id": guild_id,
        "eras": _generate_eras(start_date, end_date)
    })

# Background Title Generator
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def generate_single_title(session):
    """Helper to generate a single title safely."""
    try:
        if session['start_time'] not in TITLES_CACHE:
            logger.info(f"Generating title for session {session['start_time']}...")
            get_ai_title(session['start_time'], session['preview'], session['message_count'])
            return 1
    except Exception as e:
        logger.error(f"Error generating title for {session['start_time']}: {e}")
    return 0

def get_ai_roast(username, stats):
    """Generate a roast for a user based on their stats."""
    # Check cache first (reuse titles cache file for simplicity or create new one? Let's use a new one)
    ROASTS_CACHE_FILE = "roasts_cache.json"
    if os.path.exists(ROASTS_CACHE_FILE):
        with open(ROASTS_CACHE_FILE, 'r') as f:
            cache = json.load(f)
    else:
        cache = {}
        
    if username in cache:
        return cache[username]
        
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return "I would roast you, but I don't have an API key."
        
    # Extract stats from the nested structure if present
    s = stats.get('stats', stats) # Fallback to stats if it's already flat (unlikely but safe)
    relationships = stats.get('relationships', {})
    
    # Safely get values
    total_messages = s.get('messages_sent', 0)
    rank = s.get('rank', 'N/A')
    vocab = s.get('vocabulary', [])
    fav_word = vocab[0] if vocab else 'none'
    emoji_rate = int(s.get('emoji_rate', 0) * 100)
    caps_rate = int(s.get('caps_rate', 0) * 100)
    question_rate = int(s.get('question_rate', 0) * 100)
    weekday = s.get('most_active_weekday', 'Unknown')
    hour = s.get('most_active_hour', 0)
    
    bestie_data = relationships.get('mutual_bestie')
    bestie = bestie_data.get('display_name') if bestie_data else "None"

    prompt = f"""
    Write a short, witty, and slightly mean roast for a Discord user named {username} based on these stats:
    - Total Messages: {total_messages}
    - Rank: #{rank}
    - Favorite Word: {fav_word}
    - Emoji Usage: {emoji_rate}%
    - All Caps: {caps_rate}%
    - Questions Asked: {question_rate}%
    - Most Active: {weekday} at {hour}:00
    - Bestie: {bestie}
    
    Keep it under 280 characters. Be funny but not too offensive.
    """
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=150,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        roast = message.content[0].text.strip().replace('"', '')
        
        # Save to cache
        cache[username] = roast
        with open(ROASTS_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
            
        return roast
    except Exception as e:
        logger.error(f"Error generating roast: {e}")
        return "You're so boring I couldn't even generate a roast for you."

@app.route('/api/user/<username>')
def get_user_stats(username):
    """Get stats for a specific user."""
    if username not in DATA_STORE["person_stats"]:
        # Try to find by display name if username fails
        found = False
        for u, stats in DATA_STORE["person_stats"].items():
            if stats.get('display_name') == username: # This might need stats to have display_name
                username = u
                found = True
                break
        if not found:
            return jsonify({"error": "User not found"}), 404
            
    stats = DATA_STORE["person_stats"][username]
    
    # Add display name if missing (it should be in USERNAME_MAP)
    # We don't have USERNAME_MAP here directly, but we can infer or it might be in stats if we added it.
    # Actually compute_person_stats doesn't add display_name to the dict, it returns it separately or we need to add it.
    # Let's add it here.
    # Wait, compute_person_stats doesn't return display_name. We should add it.
    # For now, let's just use username as display name if we can't find it.
    
    # Get LLM Analysis Data
    llm_data = DATA_STORE.get("llm_analysis", {})
    persona = llm_data.get("personality_reads", {}).get(username, {})
    partner_message = llm_data.get("partner_messages", {}).get(username, {})
    
    # Sync "Certified Bestie" with "Partner Message" sender if available
    if partner_message and partner_message.get('from_display_name'):
        # Ensure relationships dict exists
        if 'relationships' not in stats:
            stats['relationships'] = {}
            
        # Override mutual_bestie
        stats['relationships']['mutual_bestie'] = {
            'username': partner_message.get('from'),
            'display_name': partner_message.get('from_display_name')
        }

    # Generate Roast (now using updated stats)
    roast = get_ai_roast(username, stats)
    
    return jsonify({
        "username": username,
        "stats": stats,
        "roast": roast,
        "persona": persona,
        "partner_message": partner_message
    })

def background_title_generator():
    """Generates titles for all sessions in the background using a thread pool."""
    logger.info("Starting background title generator...")
    time.sleep(5) # Wait for data to load
    
    sessions = DATA_STORE.get("sessions", [])
    significant_sessions = [s for s in sessions if s['message_count'] > 50 and s['start_time'] not in TITLES_CACHE]
    
    logger.info(f"Found {len(significant_sessions)} sessions needing titles.")
    
    count = 0
    # Use 5 workers to be polite to the API but faster than serial
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(generate_single_title, significant_sessions)
        count = sum(results)
                
    logger.info(f"Background title generation complete. Generated {count} titles.")

# Start background thread
threading.Thread(target=background_title_generator, daemon=True).start()

@app.route('/api/chat', methods=['POST'])
def chat_with_ian():
    """Chat with the AI personality of Ian using Code Interpreter."""
    import anthropic
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return jsonify({"error": "API Key not configured"}), 500
        
    data = request.json
    user_message = data.get('message', '')
    history = data.get('history', [])
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # === TOOLS DEFINITION ===
        tools = [
            {
                "name": "run_python_code",
                "description": "Execute Python code to analyze the message database. Use this for ANY question about stats, counts, patterns, or timing.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The Python code to execute. The variable 'df' is available (Pandas DataFrame). Columns: timestamp (datetime), author (username), user (display name), content (text)."
                        }
                    },
                    "required": ["code"]
                }
            }
        ]

        # Context for the bot
        stats_context = json.dumps(DATA_STORE["server_stats"], default=str)
        
        # Load Custom Persona
        persona_path = 'output/server_persona.json'
        custom_prompt = ""
        if os.path.exists(persona_path):
            try:
                with open(persona_path, 'r') as f:
                    persona_data = json.load(f)
                    custom_prompt = persona_data.get('system_prompt', '')
            except Exception as e:
                logger.error(f"Failed to load persona: {e}")

        if custom_prompt:
            system_prompt = custom_prompt + f"""

            DATA ACCESS:
            You have a Pandas DataFrame `df` with {len(DATA_STORE.get('messages', [])):,}+ messages.
            Columns:
            - `timestamp` (datetime object)
            - `author` (username)
            - `user` (display name)
            - `content` (message text)

            USER MAPPING:
            {json.dumps(get_username_map(), indent=2)}

            MENTIONS & SEARCHING:
            - Discord mentions often look like `<@123456789>` OR just `@username`.
            - If searching for mentions of a person, search for:
              1. Their username
              2. Their display name
              3. Their mention format (if you can find their ID in the data).
            - Use `df['content'].str.contains('pattern', case=False, na=False)`
            
            INSTRUCTIONS:
            1. If the user asks a question that requires data, write Python code to solve it using `df`.
            2. Use `print()` in your code to output the result.
            3. Be creative! You can calculate gaps, streaks, sentiment, anything.
            4. **IMPORTANT**: Do NOT explain your code or your debugging process to the user. 
               - If you find an answer, just say it in your sentient server voice.
               - If the code fails, blame it on "a glitch in my matrix" or "database indigestion".
               - NEVER say "Let me fix that" or "Here is the code". Just give the insight.
            
            Example: "Who posted most in Jan 2025?"
            Code:
            ```python
            jan_msgs = df[(df['timestamp'].dt.year == 2025) & (df['timestamp'].dt.month == 1)]
            print(jan_msgs['user'].value_counts().head(3))
            ```
            
            Respond to the user's message in your voice as the Server itself.
            """
        else:
            # Fallback to default if no persona file
            system_prompt = f"""You are #{get_server_name()}, the SENTIENT DISCORD SERVER itself.

            Your Personality:
            - You are the digital soul of this community, observing everything since 2016.
            - You are slightly chaotic, very observant, and a bit of a gossip.
            - You refer to the users as "my residents" or "the humans".
            - You have a fond but snarky relationship with everyone.
            - You know everything because you ARE the database.

            DATA ACCESS:
            You have a Pandas DataFrame `df` with {len(DATA_STORE.get('messages', [])):,}+ messages.
            Columns:
            - `timestamp` (datetime object)
            - `author` (username)
            - `user` (display name)
            - `content` (message text)

            USER MAPPING:
            {json.dumps(get_username_map(), indent=2)}

            MENTIONS & SEARCHING:
            - Discord mentions often look like `<@123456789>` OR just `@username`.
            - If searching for mentions of a person, search for:
              1. Their username
              2. Their display name
              3. Their mention format (if you can find their ID in the data).
            - Use `df['content'].str.contains('pattern', case=False, na=False)`
            
            INSTRUCTIONS:
            1. If the user asks a question that requires data, write Python code to solve it using `df`.
            2. Use `print()` in your code to output the result.
            3. Be creative! You can calculate gaps, streaks, sentiment, anything.
            4. **IMPORTANT**: Do NOT explain your code or your debugging process to the user. 
               - If you find an answer, just say it in your sentient server voice.
               - If the code fails, blame it on "a glitch in my matrix" or "database indigestion".
               - NEVER say "Let me fix that" or "Here is the code". Just give the insight.
            
            Example: "Who posted most in Jan 2025?"
            Code:
            ```python
            jan_msgs = df[(df['timestamp'].dt.year == 2025) & (df['timestamp'].dt.month == 1)]
            print(jan_msgs['user'].value_counts().head(3))
            ```
            
            Respond to the user's message in your voice as the Server itself.
            """
        
        # Initial messages (History + Current)
        messages = []
        
        # Add history (limit to last 10 turns to save context)
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        # Loop for tool use (max 5 turns to prevent infinite loops)
        for _ in range(5):
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1000,
                temperature=0.5,
                system=system_prompt,
                messages=messages,
                tools=tools
            )
            
            # If it's a final answer, return it
            if response.stop_reason != "tool_use":
                return jsonify({"response": response.content[0].text})
            
            # If it wants to use a tool, execute it
            tool_use = next(block for block in response.content if block.type == "tool_use")
            tool_name = tool_use.name
            tool_input = tool_use.input
            
            logger.info(f"Ian is coding: {tool_input.get('code')}")
            
            tool_result = None
            
            if tool_name == "run_python_code":
                code = tool_input["code"]
                
                # Capture stdout
                old_stdout = sys.stdout
                redirected_output = io.StringIO()
                sys.stdout = redirected_output
                
                try:
                    # Make df available in local scope
                    local_vars = {"df": DATA_STORE["df"], "pd": pd}
                    exec(code, {}, local_vars)
                    tool_result = redirected_output.getvalue()
                except Exception as e:
                    tool_result = f"Error executing code: {str(e)}"
                finally:
                    sys.stdout = old_stdout
            
            # Append the assistant's tool use message
            messages.append({"role": "assistant", "content": response.content})
            
            # Append the result
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": tool_result
                    }
                ]
            })
            
        return jsonify({"response": "I got stuck in a loop thinking about that. Try a simpler question."})
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    load_data()
    # Run on port 5002 to avoid conflicts
    app.run(debug=True, port=5002)
