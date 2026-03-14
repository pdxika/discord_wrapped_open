import json
import os
import random
import sys
from datetime import datetime
from collections import defaultdict, Counter
from dotenv import load_dotenv
from config import get_username_map, get_server_name

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed")
    sys.exit(1)

# Load environment variables
load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')

if not api_key:
    print("WARNING: ANTHROPIC_API_KEY not found")
    sys.exit(1)

USERNAME_MAP = get_username_map()

def load_messages():
    print("Loading messages...")
    with open('discord_messages.json', 'r') as f:
        data = json.load(f)
    
    messages = []
    if 'messages' in data:
        messages = data['messages']
    elif isinstance(data, list):
        for s in data:
            for m in s.get('messages', []):
                messages.append(m)
    
    # Sort by timestamp
    messages.sort(key=lambda x: x.get('timestamp', ''))
    print(f"Loaded {len(messages)} messages.")
    return messages

def get_llm_response(client, prompt):
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        
        # Strip markdown code blocks if present
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        print(f"LLM Error: {e}")
        return None

def main():
    messages = load_messages()
    client = anthropic.Anthropic(api_key=api_key)

    # 1. Extract Culture Samples
    print("Sampling conversations for culture analysis...")
    
    # Get a random sample of messages, but biased towards active channels/users
    # Actually, let's just take a random sample of 500 messages to get a vibe check
    sample_msgs = random.sample(messages, min(len(messages), 500))
    sample_text = ""
    for m in sample_msgs:
        author = USERNAME_MAP.get(m.get('author'), m.get('author'))
        content = m.get('content', '')
        if content:
            sample_text += f"{author}: {content}\n"

    # 2. Analyze Persona
    print("Analyzing Server DNA...")
    prompt = f"""You are a cultural anthropologist analyzing a Discord server's chat history.
    
    GOAL: Create a "Persona Profile" for a Chatbot that represents the collective soul of this server.
    
    DATA SAMPLE:
    {sample_text[:15000]} # Limit context
    
    TASK:
    1. Identify the "Vibe": Is it cynical? Wholesome? Chaotic? Tech-focused? Sports-obsessed?
    2. Identify 3-5 specific "Inside Jokes" or recurring themes/slang.
    3. Define the "Voice": How should the bot speak? (e.g. "Like a tired millennial", "Like a hype beast", "Like a grumpy old man").
    4. Write a "System Prompt" that I can feed into the bot to make it act like this server.
    
    Respond in JSON:
    {{
      "vibe_description": "Short description of the server culture...",
      "inside_jokes": ["Joke 1", "Joke 2"],
      "bot_voice_instructions": "Instructions on how to speak...",
      "system_prompt": "You are #{get_server_name()}, the sentient server..."
    }}
    """
    
    persona = get_llm_response(client, prompt)
    
    if persona:
        print("\n=== SERVER PERSONA GENERATED ===\n")
        print(f"Vibe: {persona['vibe_description']}")
        print(f"Voice: {persona['bot_voice_instructions']}")
        print("\nSystem Prompt Preview:")
        print(persona['system_prompt'][:200] + "...")
        
        # Save to file
        output_path = 'output/server_persona.json'
        with open(output_path, 'w') as f:
            json.dump(persona, f, indent=2)
        print(f"\nSaved to {output_path}")
    else:
        print("Failed to generate persona.")

if __name__ == "__main__":
    main()
