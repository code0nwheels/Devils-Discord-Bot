from datetime import time, datetime, timedelta, timezone
import zoneinfo
import asyncio
import discord
from discord.ext import tasks, commands
import logging
from logging.handlers import RotatingFileHandler

eastern = zoneinfo.ZoneInfo("US/Eastern")

class Clear(commands.Cog):
    def __init__(self, bot: discord.Bot):
        print('Clear Cog Loaded')
        self.bot = bot
        
        # Setup logging with rotation
        self.log = logging.getLogger(__name__)
        handler = RotatingFileHandler('log/clear.log', maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        
        # Add channel sets to track progress
        self.processed_channels = set()  # Channels that are fully completed
        self.in_progress_channels = set()  # Channels currently being processed
        self.pending_channels = []  # Channels waiting to be processed - using list to maintain order
        
        # Track completion status
        self.is_running = False
        self.start_time = None
        self.total_deleted = 0
        self.deletion_stats = {}  # Author ID -> count
        
        # Category ID to skip
        self.skip_category_id = 589507991674421259
        
        # Author IDs to target for message deletion
        self.author_ids = [240267442104827914, 1113953835686305823, 478699518653890560, 364425223388528651]
        
        # Channel names to skip for specific authors
        self.skip_channels = {
            240267442104827914: ["pets"],
            1113953835686305823: ["pets", "news-and-articles"],
            478699518653890560: [],
            364425223388528651: ["pets", "admin-chat", "news-and-articles"],
        }
        
        # Start the cleanup task and status check
        self.remove_old_messages.start()
        self.check_completion_status.start()
        self.log.info("Clear Cog Loaded")
        
    def cog_unload(self):
        self.remove_old_messages.cancel()
        self.check_completion_status.cancel()
        self.log.info('Clear Cog Unloaded')
    
    @tasks.loop(time=time(hour=0, minute=0, second=0, tzinfo=eastern))
    async def remove_old_messages(self):
        """Main task to clear messages from specified authors"""
        if datetime.now(eastern).day != 1:
            return
            
        try:
            # Wait until the bot is fully ready
            await self.bot.wait_until_ready()
            
            # Get the main guild - assuming the bot is in one main guild
            if not self.bot.guilds:
                self.log.error("Bot is not in any guilds")
                return
                
            guild = self.bot.guilds[0]
            
            # Calculate cutoff time (3 days ago at midnight Eastern)
            cutoff_time = datetime.now(eastern) - timedelta(days=3)
            cutoff_time = cutoff_time.replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_time = cutoff_time.astimezone(timezone.utc)
            
            # For bulk deletion cutoff (14 days)
            bulk_cutoff_time = datetime.now(timezone.utc) - timedelta(days=14)
            
            # Initialize skip channels and user names if first run
            if not hasattr(self, 'skip_channel_objects'):
                self.log.info(f"Initializing channel skip lists and user names")
                
                # Get channel objects for each skip list
                self.skip_channel_objects = {}
                for author_id, channel_names in self.skip_channels.items():
                    self.skip_channel_objects[author_id] = []
                    for channel_name in channel_names:
                        channel = discord.utils.get(guild.text_channels, name=channel_name)
                        if channel:
                            self.skip_channel_objects[author_id].append(channel)
                
                # Prepare user name mapping for logging
                self.user_names = {}
                for author_id in self.author_ids:
                    user = guild.get_member(author_id) or self.bot.get_user(author_id)
                    self.user_names[author_id] = user.name if user else f"User:{author_id}"
            
            # Reset completion tracking
            self.processed_channels.clear()
            self.in_progress_channels.clear()
            self.pending_channels.clear()
            self.total_deleted = 0
            self.deletion_stats = {author_id: 0 for author_id in self.author_ids}
                            
            # Start new batch of channels if none are in progress
            if not self.is_running:
                self.start_time = datetime.now()
                self.is_running = True
                self.log.info(f"Starting monthly message cleanup for messages before {cutoff_time}")
                
                # Process threads first
                thread_count = len(guild.threads)
                self.log.info(f"Found {thread_count} threads in guild")
                
                # Add all threads first (prioritize threads)
                for thread in guild.threads:
                    # Skip threads whose parent is in the excluded category
                    if hasattr(thread.parent, 'category_id') and thread.parent.category_id == self.skip_category_id:
                        self.log.info(f"Skipping thread {thread.name} (parent in excluded category)")
                        continue
                        
                    # Add thread to pending list
                    self.pending_channels.append(thread)
                
                # Then add all text channels
                for channel in guild.text_channels:
                    # Skip channels in the excluded category
                    if channel.category_id == self.skip_category_id:
                        self.log.info(f"Skipping channel {channel.name} (in excluded category)")
                        continue
                        
                    # Check if at least one author needs processing in this channel
                    for author_id in self.author_ids:
                        if channel not in self.skip_channel_objects.get(author_id, []):
                            self.pending_channels.append(channel)
                            break
                
                # Log how many channels we're processing
                self.log.info(f"Processing {len(self.pending_channels)} channels/threads ({thread_count} threads, {len(self.pending_channels) - thread_count} channels)")
                
                # Start filling slots
                await self.fill_processing_slots()
                
        except Exception as e:
            self.log.error(f"Error in message cleanup task: {str(e)}", exc_info=True)
    
    @tasks.loop(minutes=1)
    async def check_completion_status(self):
        """Check if the cleanup process has completed"""
        try:
            if self.is_running:
                # Check if we need to fill in any slots (should always have 10 running if possible)
                if len(self.in_progress_channels) < 10 and self.pending_channels:
                    self.log.info(f"Currently {len(self.in_progress_channels)} channels processing, filling slots...")
                    await self.fill_processing_slots()
                
                # Otherwise, just log status if there are active or pending channels
                elif self.pending_channels or len(self.in_progress_channels) > 0:
                    self.log.info(f"Status: {len(self.in_progress_channels)} channels in progress, {len(self.pending_channels)} pending, {len(self.processed_channels)} completed")
                
                # If everything is done, log completion
                elif not self.pending_channels and len(self.in_progress_channels) == 0:
                    elapsed_time = datetime.now() - self.start_time
                    hours, remainder = divmod(int(elapsed_time.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    # Format user stats for logging
                    user_stats = []
                    for author_id, count in self.deletion_stats.items():
                        if count > 0:
                            user_name = self.user_names.get(author_id, f"User:{author_id}")
                            user_stats.append(f"{user_name}: {count}")
                    
                    if user_stats:
                        user_summary = ", ".join(user_stats)
                        self.log.info(f"🎉 MONTHLY CLEANUP COMPLETE! 🎉 Processed {len(self.processed_channels)} channels in {hours}h {minutes}m {seconds}s")
                        self.log.info(f"Total messages deleted: {self.total_deleted} ({user_summary})")
                    else:
                        self.log.info(f"🎉 MONTHLY CLEANUP COMPLETE! 🎉 Processed {len(self.processed_channels)} channels in {hours}h {minutes}m {seconds}s")
                        self.log.info(f"No messages were deleted.")
                    
                    # Reset running flag after completion
                    self.is_running = False
                    
        except Exception as e:
            self.log.error(f"Error checking completion status: {str(e)}", exc_info=True)
    
    async def fill_processing_slots(self):
        """Fill available processing slots with pending channels"""
        try:
            # Maximum concurrent channels
            max_concurrent = 10
            
            # Start new tasks up to the concurrency limit
            slots_available = max_concurrent - len(self.in_progress_channels)
            channels_to_start = min(slots_available, len(self.pending_channels))
            
            if channels_to_start > 0:
                self.log.info(f"Starting {channels_to_start} new channel processors ({len(self.in_progress_channels)} already running)")
                
                for _ in range(channels_to_start):
                    if not self.pending_channels:
                        break
                        
                    channel = self.pending_channels.pop(0)
                    self.in_progress_channels.add(channel.id)
                    
                    # Process this channel in the background
                    asyncio.create_task(
                        self.process_channel(
                            channel=channel,
                            author_ids=self.author_ids,
                            skip_channels=self.skip_channel_objects,
                            user_names=self.user_names,
                            cutoff_time=datetime.now(eastern) - timedelta(days=3),  # Fresh cutoff time
                            bulk_cutoff_time=datetime.now(timezone.utc) - timedelta(days=14)  # Fresh bulk cutoff
                        )
                    )
                    
                    if isinstance(channel, discord.Thread):
                        self.log.info(f"Starting thread: {channel.name} (in #{channel.parent.name})")
                    else:
                        self.log.info(f"Starting channel: {channel.name}")
        except Exception as e:
            self.log.error(f"Error filling slots: {str(e)}", exc_info=True)
    
    async def process_channel(self, channel, author_ids, skip_channels, user_names, cutoff_time, bulk_cutoff_time):
        """Process a single channel to delete messages from specified authors"""
        start_time = datetime.now()
        if isinstance(channel, discord.Thread):
            self.log.info(f"Starting to process thread: {channel.name} (in #{channel.parent.name})")
        else:
            self.log.info(f"Starting to process channel: {channel.name}")
        
        # Track deletion counts per user
        user_counts = {author_id: 0 for author_id in author_ids}
        
        try:
            # Get all messages before the cutoff time
            bulk_delete_batch = []
            individual_delete_tasks = []
            messages_processed = 0
            
            # Process history to completion - no limit
            async for message in channel.history(before=cutoff_time, limit=None, oldest_first=False):
                messages_processed += 1
                
                # Log progress for large channels
                if messages_processed % 1000 == 0:
                    elapsed = datetime.now() - start_time
                    if isinstance(channel, discord.Thread):
                        self.log.info(f"  Processed {messages_processed} messages in thread {channel.name} ({elapsed.total_seconds():.1f}s elapsed)")
                    else:
                        self.log.info(f"  Processed {messages_processed} messages in {channel.name} ({elapsed.total_seconds():.1f}s elapsed)")
                
                # Check if message author is in our target list
                if message.author.id not in author_ids:
                    continue
                
                # Skip if this author's messages should be preserved in this channel
                if channel in skip_channels.get(message.author.id, []):
                    continue
                
                # Message needs to be deleted - determine how
                author_id = message.author.id
                message_time = message.created_at
                if message_time.tzinfo is None:
                    message_time = message_time.replace(tzinfo=timezone.utc)
                
                # Use bulk deletion for recent messages (recalculate cutoff time to handle long-running channels)
                current_bulk_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
                
                if message_time > current_bulk_cutoff:
                    bulk_delete_batch.append(message)
                    
                    # Process bulk deletions in batches of 100
                    if len(bulk_delete_batch) >= 100:
                        try:
                            await channel.delete_messages(bulk_delete_batch)
                            # Track which users had messages deleted
                            for msg in bulk_delete_batch:
                                if msg.author.id in user_counts:
                                    user_counts[msg.author.id] += 1
                            
                            self.log.info(f"  Bulk deleted {len(bulk_delete_batch)} messages in {channel.name}")
                        except Exception as e:
                            self.log.error(f"  Error bulk deleting messages in {channel.name}: {str(e)}")
                            
                            # If bulk deletion fails, add to individual deletion
                            for msg in bulk_delete_batch:
                                individual_delete_tasks.append((msg, msg.author.id))
                        
                        bulk_delete_batch = []
                else:
                    # Individual deletion for older messages
                    individual_delete_tasks.append((message, author_id))
                    
                    # Process individual deletions in batches
                    if len(individual_delete_tasks) >= 25:
                        deleted_count = await self._process_individual_deletes(individual_delete_tasks, channel.name)
                        # Update user counts
                        for msg, user_id in individual_delete_tasks:
                            if deleted_count > 0 and user_id in user_counts:
                                user_counts[user_id] += 1
                                deleted_count -= 1  # Distribute deletions among users
                        individual_delete_tasks = []
            
            # Process any remaining bulk deletions
            if bulk_delete_batch:
                try:
                    # Verify all messages are still eligible for bulk deletion
                    current_bulk_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
                    eligible_for_bulk = True
                    
                    for msg in bulk_delete_batch:
                        msg_time = msg.created_at
                        if msg_time.tzinfo is None:
                            msg_time = msg_time.replace(tzinfo=timezone.utc)
                        
                        if msg_time <= current_bulk_cutoff:
                            eligible_for_bulk = False
                            break
                    
                    if eligible_for_bulk:
                        # All messages are recent enough for bulk deletion
                        await channel.delete_messages(bulk_delete_batch)
                        # Track which users had messages deleted
                        for msg in bulk_delete_batch:
                            if msg.author.id in user_counts:
                                user_counts[msg.author.id] += 1
                        
                        self.log.info(f"  Bulk deleted {len(bulk_delete_batch)} messages in {channel.name}")
                    else:
                        # Some messages are too old, process individually
                        self.log.info(f"  Some messages too old for bulk deletion, processing {len(bulk_delete_batch)} individually")
                        for msg in bulk_delete_batch:
                            individual_delete_tasks.append((msg, msg.author.id))
                except Exception as e:
                    self.log.error(f"  Error bulk deleting remaining messages in {channel.name}: {str(e)}")
                    # If bulk deletion fails, add to individual deletion
                    for msg in bulk_delete_batch:
                        individual_delete_tasks.append((msg, msg.author.id))
            
            # Process any remaining individual deletions
            if individual_delete_tasks:
                deleted_count = await self._process_individual_deletes(individual_delete_tasks, channel.name)
                # Update user counts
                for msg, user_id in individual_delete_tasks:
                    if deleted_count > 0 and user_id in user_counts:
                        user_counts[user_id] += 1
                        deleted_count -= 1  # Distribute deletions among users
            
            # Log channel completion
            total_deleted = sum(user_counts.values())
            elapsed_time = datetime.now() - start_time
            
            # Update global deletion stats
            for author_id, count in user_counts.items():
                if count > 0:
                    self.deletion_stats[author_id] = self.deletion_stats.get(author_id, 0) + count
                    self.total_deleted += count
            
            if isinstance(channel, discord.Thread):
                channel_description = f"thread {channel.name} (in #{channel.parent.name})"
            else:
                channel_description = f"channel {channel.name}"
                
            if total_deleted > 0:
                user_summary = ", ".join([f"{user_names[uid]}: {count}" for uid, count in user_counts.items() if count > 0])
                self.log.info(f"Completed {channel_description} in {elapsed_time.total_seconds():.1f}s: {total_deleted} messages deleted ({user_summary})")
            else:
                self.log.info(f"Completed {channel_description} in {elapsed_time.total_seconds():.1f}s: No messages deleted")
            
        except discord.errors.Forbidden:
            self.log.warning(f"No permission to access or delete messages in {channel.name}")
        except Exception as e:
            self.log.error(f"Error processing {channel.name}: {str(e)}", exc_info=True)
        finally:
            # Update channel tracking sets
            self.in_progress_channels.discard(channel.id)
            self.processed_channels.add(channel.id)
            
            # Try to fill slots again
            if self.pending_channels:
                await self.fill_processing_slots()
    
    async def _process_individual_deletes(self, delete_tasks, channel_name):
        """Helper to process a batch of individual message deletions"""
        if not delete_tasks:
            return 0
            
        # Group messages by user for better logging
        user_groups = {}
        for message, user_id in delete_tasks:
            if user_id not in user_groups:
                user_groups[user_id] = []
            user_groups[user_id].append(message)
        
        # Process delete operations concurrently
        all_tasks = []
        for messages in user_groups.values():
            all_tasks.extend([msg.delete() for msg in messages])
        
        if all_tasks:
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            successful_deletes = sum(1 for r in results if not isinstance(r, Exception))
            
            self.log.info(f"  Individually deleted {successful_deletes} messages in {channel_name}")
            return successful_deletes
        
        return 0
    
    @check_completion_status.before_loop
    @remove_old_messages.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()
    
    @check_completion_status.error
    async def status_error(self, error):
        self.log.error(f"Error in status check task: {str(error)}", exc_info=True)
    
    @remove_old_messages.error
    async def cleanup_error(self, error):
        self.log.error(f"Error in cleanup task: {str(error)}", exc_info=True)

def setup(bot: discord.Bot):
    bot.add_cog(Clear(bot))