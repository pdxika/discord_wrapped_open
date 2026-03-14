#!/usr/bin/env python3
"""
Discord Wrapped Analysis Pipeline
Runs all analysis scripts in the correct order.

Usage:
    python run_pipeline.py                  # Run everything
    python run_pipeline.py --stats-only     # Skip LLM features
    python run_pipeline.py --skip-embeddings # Skip 3D visualization
"""

import subprocess
import sys
import os
import time
import argparse
from pathlib import Path
from config import load_config, has_anthropic_key, is_feature_enabled


def run_script(name, args=None, required=True):
    """Run a Python script and return success status."""
    cmd = [sys.executable, name]
    if args:
        cmd.extend(args)

    print(f"\n{'='*60}")
    print(f"  Running: {name}")
    print(f"{'='*60}")

    start = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - start

    if result.returncode != 0:
        if required:
            print(f"  FAILED: {name} (exit code {result.returncode})")
            return False
        else:
            print(f"  SKIPPED/FAILED (optional): {name}")
            return True  # Don't block pipeline for optional scripts

    print(f"  Done: {name} ({elapsed:.1f}s)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Discord Wrapped Analysis Pipeline")
    parser.add_argument("--stats-only", action="store_true",
                        help="Skip all LLM-powered features")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="Skip 3D vector space embeddings")
    args = parser.parse_args()

    # Check prerequisites
    config = load_config()

    if not Path("discord_messages.json").exists():
        print("ERROR: discord_messages.json not found!")
        print("Run 'python export.py' first to export your Discord messages.")
        sys.exit(1)

    os.makedirs("output", exist_ok=True)

    use_llm = has_anthropic_key() and not args.stats_only
    use_embeddings = is_feature_enabled("embeddings") and not args.skip_embeddings

    print("\n" + "="*60)
    print("  DISCORD WRAPPED ANALYSIS PIPELINE")
    print("="*60)
    print(f"  LLM features: {'ON' if use_llm else 'OFF'}")
    print(f"  Embeddings:   {'ON' if use_embeddings else 'OFF'}")
    print("="*60)

    # ─── Phase 1: Core stats (no dependencies) ───
    print("\n\n>>> PHASE 1: Core Statistics")

    if not run_script("compute_basic_stats.py"):
        print("\nFATAL: compute_basic_stats.py failed. Cannot continue.")
        sys.exit(1)

    run_script("compute_patterns.py")
    run_script("compute_all_awards.py")

    if is_feature_enabled("bechdel"):
        run_script("compute_bechdel_test.py", required=False)

    # ─── Phase 2: LLM analysis (needs Phase 1 outputs) ───
    if use_llm:
        print("\n\n>>> PHASE 2: LLM Analysis")
        run_script("compute_llm_analysis.py", required=False)
        run_script("compute_final_llm_awards.py", required=False)

        if is_feature_enabled("synesthesia"):
            run_script("compute_synesthesia_colors.py", required=False)

        run_script("vibe_extractor.py", args=["discord_messages.json"], required=False)
        run_script("analyze_server_persona.py", required=False)
    else:
        print("\n\n>>> PHASE 2: Skipping LLM analysis (no API key or --stats-only)")

    # ─── Phase 3: Inside joke timelines (needs patterns.json) ───
    print("\n\n>>> PHASE 3: Inside Joke Timelines")
    if Path("output/patterns.json").exists():
        run_script("compute_inside_joke_timeline.py", required=False)
    else:
        print("  Skipping: patterns.json not found")

    # ─── Phase 4: Embeddings ───
    if use_embeddings:
        print("\n\n>>> PHASE 4: Message Embeddings")
        try:
            import sentence_transformers  # noqa: F401
            run_script("compute_embeddings.py", required=False)
        except ImportError:
            print("  Skipping: sentence-transformers not installed")
            print("  Install with: pip install sentence-transformers scikit-learn")
    else:
        print("\n\n>>> PHASE 4: Skipping embeddings")

    # ─── Phase 5: Merge everything ───
    print("\n\n>>> PHASE 5: Merging Data")
    run_script("merge_final_data.py")
    run_script("merge_all_final_data.py")

    # ─── Copy to frontend ───
    print("\n\n>>> Copying data to frontend...")
    frontend_data_dir = Path("wrapped-frontend/src/data")
    frontend_data_dir.mkdir(parents=True, exist_ok=True)

    complete_data = Path("output/complete_wrapped_data.json")
    if complete_data.exists():
        import shutil
        shutil.copy(complete_data, frontend_data_dir / "wrapped_data.json")
        print(f"  Copied to {frontend_data_dir / 'wrapped_data.json'}")

    vector_data = Path("output/vector_space.json")
    frontend_public = Path("wrapped-frontend/public")
    if vector_data.exists() and frontend_public.exists():
        import shutil
        shutil.copy(vector_data, frontend_public / "vector_data.json")
        print(f"  Copied to {frontend_public / 'vector_data.json'}")

    # ─── Done! ───
    print("\n" + "="*60)
    print("  PIPELINE COMPLETE!")
    print("="*60)
    print("\n  Next steps:")
    print("    1. Start the backend:  python server.py")
    print("    2. Start the frontend: cd wrapped-frontend && npm install && npm run dev")
    print("    3. Open http://localhost:5173")
    print()


if __name__ == "__main__":
    main()
