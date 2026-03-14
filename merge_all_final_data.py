#!/usr/bin/env python3
"""
Final comprehensive merge of ALL Discord Wrapped 2025 data.

Combines:
- Basic stats (group + individuals)
- Patterns (inside jokes, callbacks, locations, 9/11)
- LLM analysis (personalities, original sentiment awards, partner messages)
- New awards (Aproposter, Katamari, 9/11, HER, etc.)
- Bechdel test
- Synesthesia colors & evidence
- Inside joke timelines
- Final LLM awards (Taylor Swift, Space Odyscord) if available
- Voice guide

Output: complete_wrapped_data.json (all-in-one file for frontend)
"""

import json
from pathlib import Path
from datetime import datetime
from config import get_username_map, get_server_name

OUTPUT_DIR = Path("output")

USERNAME_MAP = get_username_map()


def load_json(filepath):
    """Load JSON file, return empty dict if not found."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  {filepath} not found, skipping...")
        return {}


def main():
    print("="*60)
    print("MERGING ALL DISCORD WRAPPED 2025 DATA")
    print("="*60)

    print("\nLoading core data...")
    group_data = load_json(OUTPUT_DIR / "group_wrapped.json")
    patterns_data = load_json(OUTPUT_DIR / "patterns.json")
    llm_data = load_json(OUTPUT_DIR / "llm_analysis.json")
    voice_guide_data = load_json("voice_guide_output.json")

    print("Loading individual stats...")
    individual_data = {}
    for username in USERNAME_MAP.keys():
        individual_data[username] = load_json(OUTPUT_DIR / f"wrapped_{username}.json")

    print("Loading awards...")
    new_awards = load_json(OUTPUT_DIR / "new_awards.json")
    final_llm_awards = load_json(OUTPUT_DIR / "final_llm_awards.json")

    print("Loading special analysis...")
    bechdel = load_json(OUTPUT_DIR / "bechdel_test.json")
    synesthesia_colors = load_json(OUTPUT_DIR / "synesthesia_colors.json")
    synesthesia_evidence = load_json(OUTPUT_DIR / "synesthesia_evidence.json")
    inside_joke_timelines = load_json(OUTPUT_DIR / "inside_joke_timelines.json")

    print("\nMerging data...")

    # Build comprehensive awards section
    all_awards = {}

    # Original sentiment awards
    sentiment_awards = llm_data.get('sentiment_awards', {})
    for award_name, award_data in sentiment_awards.items():
        all_awards[award_name] = {
            'category': 'sentiment',
            **award_data
        }

    # New computed awards
    for award_name, award_data in new_awards.get('awards', {}).items():
        all_awards[award_name] = {
            'category': 'behavioral',
            **award_data
        }

    # Final LLM awards
    for award_name, award_data in final_llm_awards.get('awards', {}).items():
        all_awards[award_name] = {
            'category': 'pattern',
            **award_data
        }

    # Build final structure
    complete_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "2.0-complete",
            "description": f"Discord Wrapped - {get_server_name()} - Complete Dataset",
            "data_sources": [
                f"{len(USERNAME_MAP)} server members analyzed",
                "LLM personality analysis via Claude",
                "Pattern matching, statistical analysis, and behavioral awards"
            ]
        },

        # GROUP-LEVEL DATA
        "group": {
            "stats": group_data,
            "patterns": patterns_data,
            "voice_guide": voice_guide_data.get("voice_guide", {}),
            "bechdel_test": bechdel.get('stats', {}),
            "inside_joke_timelines": inside_joke_timelines.get('timelines', {})
        },

        # INDIVIDUAL DATA
        "individuals": {},

        # AWARDS (ALL)
        "awards": all_awards,

        # SYNESTHESIA
        "synesthesia": {
            "colors": synesthesia_colors.get('colors', {}),
            "evidence": synesthesia_evidence.get('evidence', {})
        },

        # PERSONALITIES & MESSAGES
        "personalities": llm_data.get("personality_reads", {}),
        "partner_messages": llm_data.get("partner_messages", {})
    }

    # Add individual data with display names
    for username, display_name in USERNAME_MAP.items():
        complete_data["individuals"][username] = {
            "display_name": display_name,
            "stats": individual_data.get(username, {}),
            "personality": llm_data.get("personality_reads", {}).get(username, {}),
            "partner_message": llm_data.get("partner_messages", {}).get(username, {}),
            "synesthesia_color": synesthesia_colors.get('colors', {}).get(username, {}),
            "synesthesia_evidence": synesthesia_evidence.get('evidence', {}).get(username, {})
        }

    # Save complete data
    output_path = OUTPUT_DIR / "complete_wrapped_data.json"
    with open(output_path, 'w') as f:
        json.dump(complete_data, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("✅ COMPLETE WRAPPED DATA MERGED")
    print('='*60)
    print(f"\n📄 Output: {output_path}")
    print(f"📊 File size: {output_path.stat().st_size / 1024:.1f} KB")

    print("\n📋 Data Summary:")
    print(f"  - Group stats: {len(group_data)} sections")
    print(f"  - Individual profiles: {len(complete_data['individuals'])}")
    print(f"  - Total awards: {len(all_awards)}")
    print(f"  - Personality reads: {len(complete_data['personalities'])}")
    print(f"  - Partner messages: {len(complete_data['partner_messages'])}")
    print(f"  - Inside jokes: {len(patterns_data.get('inside_jokes', {}))}")
    print(f"  - Synesthesia colors: {len([c for c in synesthesia_colors.get('colors', {}).values() if c.get('color') != 'unknown'])}/11")
    print(f"  - Bechdel test: {bechdel.get('stats', {}).get('bechdel_pass_rate', 0):.1f}% pass rate")

    print("\n🎯 Awards Breakdown:")
    awards_by_category = {}
    for award_name, award_data in all_awards.items():
        category = award_data.get('category', 'other')
        awards_by_category[category] = awards_by_category.get(category, 0) + 1

    for category, count in sorted(awards_by_category.items()):
        print(f"  - {category.capitalize()}: {count} awards")

    print("\n🎉 Ready for frontend development!")
    return complete_data


if __name__ == "__main__":
    main()
