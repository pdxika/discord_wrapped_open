import discord
from discord.ext import commands
from datetime import datetime, timedelta
import os
import asyncio
import logging
import json
from config import get_channel_ids, get_export_days

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("export.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MessageExporter")

# Configuration
CHANNEL_IDS = get_channel_ids()
DAYS_TO_EXPORT = get_export_days()

class MessageExporter(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        super().__init__(command_prefix='!', intents=intents)
        self.all_messages = []

async def export_messages():
    """Export all messages to JSON"""
    discord_token = os.getenv('DISCORD_BOT_TOKEN')

    if not discord_token:
        logger.error("DISCORD_BOT_TOKEN environment variable not found")
        return

    bot = MessageExporter()

    @bot.event
    async def on_ready():
        logger.info(f'Logged in as {bot.user}')

        cutoff_date = datetime.now() - timedelta(days=DAYS_TO_EXPORT)

        logger.info(f"\n{'='*60}")
        logger.info(f"EXPORTING MESSAGES FROM THE LAST {DAYS_TO_EXPORT} DAYS")
        logger.info(f"Starting from: {cutoff_date.date()}")
        logger.info(f"{'='*60}\n")

        all_messages = []
        total_messages = 0

        for channel_id in CHANNEL_IDS:
            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Could not find channel with ID {channel_id}")
                continue

            logger.info(f"Exporting from channel: {channel.name}")

            message_count = 0
            try:
                async for message in channel.history(limit=None, after=cutoff_date):
                    # Skip bot messages
                    if message.author.bot:
                        continue

                    # Store message data
                    # Get reactions
                    reactions_data = []
                    for reaction in message.reactions:
                        # Get the emoji (handle both unicode and custom emoji)
                        if isinstance(reaction.emoji, str):
                            emoji_str = reaction.emoji
                            emoji_id = None
                        else:
                            emoji_str = reaction.emoji.name
                            emoji_id = str(reaction.emoji.id) if reaction.emoji.id else None

                        reactions_data.append({
                            'emoji': emoji_str,
                            'emoji_id': emoji_id,
                            'count': reaction.count
                        })

                    # Get reply reference (if this message is a reply to another)
                    reference_data = None
                    if message.reference:
                        reference_data = {
                            'message_id': str(message.reference.message_id) if message.reference.message_id else None,
                            'channel_id': str(message.reference.channel_id) if message.reference.channel_id else None,
                        }

                    # Store message data
                    message_data = {
                        'id': str(message.id),
                        'channel_id': str(message.channel.id),
                        'channel_name': message.channel.name,
                        'author': message.author.name,
                        'author_id': str(message.author.id),
                        'content': message.content,
                        'timestamp': message.created_at.isoformat(),
                        'edited_at': message.edited_at.isoformat() if message.edited_at else None,
                        'mentions': [user.name for user in message.mentions],
                        'attachments': [att.url for att in message.attachments] if message.attachments else [],
                        # NEW FIELDS:
                        'reactions': reactions_data,
                        'reference': reference_data,  # Reply data
                        'embeds': [{'url': e.url, 'type': e.type} for e in message.embeds] if message.embeds else [],
                        'stickers': [{'name': s.name, 'id': str(s.id)} for s in message.stickers] if message.stickers else [],
                    }

                    all_messages.append(message_data)
                    message_count += 1
                    total_messages += 1

                    if message_count % 1000 == 0:
                        logger.info(f"  Exported {message_count} messages...")

                logger.info(f"  Total from {channel.name}: {message_count}")
            except Exception as e:
                logger.error(f"Error reading {channel.name}: {e}")

        logger.info(f"\nTotal messages exported: {total_messages}")

        if total_messages == 0:
            logger.error("No messages found to export!")
            await bot.close()
            return

        # Save to JSON
        logger.info("\nSaving to discord_messages.json...")

        output_data = {
            'export_date': datetime.now().isoformat(),
            'days_exported': DAYS_TO_EXPORT,
            'channels': [
                {'id': str(cid), 'name': bot.get_channel(cid).name if bot.get_channel(cid) else 'Unknown'}
                for cid in CHANNEL_IDS
            ],
            'total_messages': total_messages,
            'messages': all_messages
        }

        with open("discord_messages.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info("\n" + "="*60)
        logger.info("✅ EXPORT COMPLETE!")
        logger.info("="*60)
        logger.info(f"Exported {total_messages} messages")
        logger.info("Saved to: discord_messages.json")
        logger.info(f"File size: {os.path.getsize('discord_messages.json') / 1024 / 1024:.2f} MB")
        logger.info("="*60 + "\n")

        await bot.close()

    try:
        await bot.start(discord_token)
    except Exception as e:
        logger.error(f"Error: {e}")

def main():
    logger.info("="*60)
    logger.info("DISCORD MESSAGE EXPORTER")
    logger.info("="*60)
    logger.info(f"Exporting: {DAYS_TO_EXPORT} days of history")
    logger.info(f"Channels: {len(CHANNEL_IDS)}")
    logger.info("="*60 + "\n")

    asyncio.run(export_messages())

if __name__ == "__main__":
    main()