#!/usr/bin/env python3
"""
Merge all analysis outputs into final data structure for Discord Wrapped frontend.

Combines:
- group_wrapped.json (basic group stats)
- wrapped_{username}.json (individual stats for 11 people)
- patterns.json (inside jokes, callbacks, locations)
- llm_analysis.json (personalities, sentiment awards, partner messages)
- voice_guide_output.json (narrator voice guide)

Output:
- final_wrapped_data.json (complete merged data for frontend)
"""

import json
from pathlib import Path
from datetime import datetime
from config import get_username_map, get_server_name

OUTPUT_DIR = Path("output")

USERNAME_MAP = get_username_map()


def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def merge_all_data():
    """Merge all analysis outputs into final data structure"""

    print("Loading all data files...")

    # Load all data
    group_data = load_json(OUTPUT_DIR / "group_wrapped.json")
    patterns_data = load_json(OUTPUT_DIR / "patterns.json")
    llm_data = load_json(OUTPUT_DIR / "llm_analysis.json")
    voice_guide_data = load_json("voice_guide_output.json")

    # Load individual wrapped files
    individual_data = {}
    for username in USERNAME_MAP.keys():
        individual_data[username] = load_json(OUTPUT_DIR / f"wrapped_{username}.json")

    print("Merging data...")

    # Build final structure
    final_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "description": f"Discord Wrapped - {get_server_name()}"
        },

        # Group-level data
        "group": {
            "stats": group_data,
            "patterns": patterns_data,
            "voice_guide": voice_guide_data.get("voice_guide", {})
        },

        # Individual data for each person
        "individuals": {},

        # LLM-generated content
        "personalities": llm_data.get("personality_reads", {}),
        "sentiment_awards": llm_data.get("sentiment_awards", {}),
        "partner_messages": llm_data.get("partner_messages", {})
    }

    # Add individual data with display names
    for username, display_name in USERNAME_MAP.items():
        final_data["individuals"][username] = {
            "display_name": display_name,
            "stats": individual_data[username],
            "personality": llm_data.get("personality_reads", {}).get(username, {}),
            "partner_message": llm_data.get("partner_messages", {}).get(username, {})
        }

    # Save final merged data
    output_path = OUTPUT_DIR / "final_wrapped_data.json"
    with open(output_path, 'w') as f:
        json.dump(final_data, f, indent=2)

    print(f"\n✅ Final data merged successfully!")
    print(f"📄 Output: {output_path}")
    print(f"📊 File size: {output_path.stat().st_size / 1024:.1f} KB")

    # Print summary
    print("\n📋 Data Summary:")
    print(f"  - Group stats: {len(group_data)} sections")
    print(f"  - Individual profiles: {len(final_data['individuals'])}")
    print(f"  - Personality reads: {len(final_data['personalities'])}")
    print(f"  - Sentiment awards: {len(final_data['sentiment_awards'])}")
    print(f"  - Partner messages: {len(final_data['partner_messages'])}")
    print(f"  - Inside jokes: {len(patterns_data.get('inside_jokes', {}))}")
    print(f"  - Callbacks: {len(patterns_data.get('callbacks', []))}")
    print(f"  - Locations mentioned: {len(patterns_data.get('locations', []))}")
    print(f"  - 9/11 mentions: {patterns_data.get('nine_eleven', {}).get('total_mentions', 0)}")

    return final_data


if __name__ == "__main__":
    final_data = merge_all_data()
    print("\n🎉 Ready to build the frontend!")
