"""
Centralized configuration loader for Discord Wrapped.
All scripts import config from this module instead of hardcoding values.
"""
import yaml
import os
import sys
from pathlib import Path

_config = None


def load_config(config_path=None):
    """Load configuration from YAML file."""
    global _config
    if _config is not None:
        return _config

    if config_path is None:
        config_path = os.environ.get("DISCORD_WRAPPED_CONFIG", "config.yaml")

    path = Path(config_path)
    if not path.exists():
        print(f"ERROR: {config_path} not found.")
        print("Copy config.example.yaml to config.yaml and fill in your settings.")
        sys.exit(1)

    with open(path, 'r') as f:
        _config = yaml.safe_load(f)

    return _config


def get_username_map():
    """Return the Discord username -> display name mapping."""
    cfg = load_config()
    return cfg.get('users', {})


def get_channel_ids():
    """Return the list of channel IDs to export."""
    cfg = load_config()
    return [int(c) for c in cfg.get('channels', [])]


def get_server_name():
    """Return the server display name."""
    cfg = load_config()
    return cfg.get('server', {}).get('name', 'My Server')


def get_guild_id():
    """Return the Discord guild (server) ID."""
    cfg = load_config()
    return str(cfg.get('server', {}).get('guild_id', ''))


def get_inside_jokes():
    """Return the list of inside joke keywords to track."""
    cfg = load_config()
    return cfg.get('inside_jokes', [])


def get_bot_persona_name():
    """Return the chatbot persona name for the Oracle tab."""
    cfg = load_config()
    return cfg.get('bot_persona_name', 'ServerBot')


def get_export_days():
    """Return the number of days of history to export."""
    cfg = load_config()
    return cfg.get('export', {}).get('days', 365)


def get_custom_keyword_trackers():
    """Return custom keyword tracker definitions for awards."""
    cfg = load_config()
    return cfg.get('custom_keyword_trackers', [])


def get_llm_model():
    """Return the LLM model to use for analysis."""
    cfg = load_config()
    return cfg.get('llm', {}).get('model', 'claude-sonnet-4-20250514')


def is_feature_enabled(feature_name):
    """Check if an optional feature is enabled in config."""
    cfg = load_config()
    return cfg.get('features', {}).get(feature_name, True)


def has_anthropic_key():
    """Check if an Anthropic API key is available."""
    return bool(os.getenv('ANTHROPIC_API_KEY'))


def is_llm_enabled():
    """Check if LLM features should be used (enabled in config + key present)."""
    cfg = load_config()
    return cfg.get('llm', {}).get('enabled', True) and has_anthropic_key()
