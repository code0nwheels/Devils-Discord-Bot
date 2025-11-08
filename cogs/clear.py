from datetime import time, datetime, timedelta, timezone
import zoneinfo
import asyncio
import discord
from discord.ext import tasks, commands

eastern = zoneinfo.ZoneInfo("US/Eastern")

class Clear(commands.Cog):
    # Constants
    SKIP_CATEGORY_ID = 589507991674421259
    AUTHOR_IDS = [240267442104827914, 1113953835686305823, 478699518653890560, 364425223388528651]
    SKIP_CHANNELS = {
        240267442104827914: ["pets"],
        1113953835686305823: ["pets", "news-and-articles"],
        478699518653890560: [],
        364425223388528651: ["pets", "admin-chat", "news-and-articles"],
    }
    BULK_DELETE_BATCH_SIZE = 100
    INDIVIDUAL_DELETE_BATCH_SIZE = 25
    BULK_DELETE_DAYS = 14
    MESSAGE_CLEANUP_DAYS = 3
    
    def __init__(self, bot: discord.Bot):
        print('Clear Cog Loaded')
        self.bot = bot
        
        # Setup logging with rotation
        from util.logger import setup_logger
        self.log = setup_logger(__name__, 'log/clear.log')
        
        # Add channel sets to track progress
        self.processed_channels = set()  # Channels that are fully completed
        self.in_progress_channels = set()  # Channels currently being processed
        self.pending_channels = []  # Channels waiting to be processed - using list to maintain order
        
        # Track completion status
        self.is_running = False
        self.start_time = None
        self.total_deleted = 0
        self.deletion_stats = {}  # Author ID -> count
        self.skip_channel_objects = {}
        self.user_names = {}
        
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
            cutoff_time = datetime.now(eastern) - timedelta(days=self.MESSAGE_CLEANUP_DAYS)
            cutoff_time = cutoff_time.replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_time = cutoff_time.astimezone(timezone.utc)
            
            # For bulk deletion cutoff (14 days)
            bulk_cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.BULK_DELETE_DAYS)
            
            # Initialize skip channels and user names if first run
            if not self.skip_channel_objects:
                self.log.info(f"Initializing channel skip lists and user names")
                self._initialize_skip_channels(guild)
                self._initialize_user_names(guild)
            
            # Reset completion tracking
            self.processed_channels.clear()
            self.in_progress_channels.clear()
            self.pending_channels.clear()
            self.total_deleted = 0
            self.deletion_stats = {author_id: 0 for author_id in self.AUTHOR_IDS}
                            
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
                    if hasattr(thread.parent, 'category_id') and thread.parent.category_id == self.SKIP_CATEGORY_ID:
                        self.log.info(f"Skipping thread {thread.name} (parent in excluded category)")
                        continue
                        
                    # Add thread to pending list
                    self.pending_channels.append(thread)
                
                # Then add all text channels
                for channel in guild.text_channels:
                    # Skip channels in the excluded category
                    if channel.category_id == self.SKIP_CATEGORY_ID:
                        self.log.info(f"Skipping channel {channel.name} (in excluded category)")
                        continue
                        
                    # Check if at least one author needs processing in this channel
                    for author_id in self.AUTHOR_IDS:
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
                    cutoff_time = datetime.now(eastern) - timedelta(days=self.MESSAGE_CLEANUP_DAYS)
                    cutoff_time = cutoff_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    cutoff_time = cutoff_time.astimezone(timezone.utc)
                    bulk_cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.BULK_DELETE_DAYS)
                    
                    asyncio.create_task(
                        self.process_channel(
                            channel=channel,
                            cutoff_time=cutoff_time,
                            bulk_cutoff_time=bulk_cutoff_time
                        )
                    )
                    
                    if isinstance(channel, discord.Thread):
                        self.log.info(f"Starting thread: {channel.name} (in #{channel.parent.name})")
                    else:
                        self.log.info(f"Starting channel: {channel.name}")
        except Exception as e:
            self.log.error(f"Error filling slots: {str(e)}", exc_info=True)
    
    def _initialize_skip_channels(self, guild):
        """Initialize skip channel objects."""
        for author_id, channel_names in self.SKIP_CHANNELS.items():
            self.skip_channel_objects[author_id] = []
            for channel_name in channel_names:
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if channel:
                    self.skip_channel_objects[author_id].append(channel)
    
    def _initialize_user_names(self, guild):
        """Initialize user name mapping for logging."""
        for author_id in self.AUTHOR_IDS:
            user = guild.get_member(author_id) or self.bot.get_user(author_id)
            self.user_names[author_id] = user.name if user else f"User:{author_id}"
    
    def _should_delete_message(self, message, channel):
        """Check if a message should be deleted."""
        if message.author.id not in self.AUTHOR_IDS:
            return False
        if channel in self.skip_channel_objects.get(message.author.id, []):
            return False
        return True
    
    def _normalize_message_time(self, message_time):
        """Normalize message time to UTC."""
        if message_time.tzinfo is None:
            return message_time.replace(tzinfo=timezone.utc)
        return message_time
    
    async def _process_bulk_delete_batch(self, channel, bulk_batch, user_counts):
        """Process a batch of messages for bulk deletion."""
        try:
            await channel.delete_messages(bulk_batch)
            for msg in bulk_batch:
                if msg.author.id in user_counts:
                    user_counts[msg.author.id] += 1
            self.log.info(f"  Bulk deleted {len(bulk_batch)} messages in {channel.name}")
            return True
        except Exception as e:
            self.log.error(f"  Error bulk deleting messages in {channel.name}: {str(e)}")
            return False
    
    async def process_channel(self, channel, cutoff_time, bulk_cutoff_time):
        """Process a single channel to delete messages from specified authors"""
        start_time = datetime.now()
        channel_name = f"thread {channel.name} (in #{channel.parent.name})" if isinstance(channel, discord.Thread) else f"channel {channel.name}"
        self.log.info(f"Starting to process {channel_name}")
        
        # Track deletion counts per user
        user_counts = {author_id: 0 for author_id in self.AUTHOR_IDS}
        
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
                
                # Check if message should be deleted
                if not self._should_delete_message(message, channel):
                    continue
                
                # Message needs to be deleted - determine how
                message_time = self._normalize_message_time(message.created_at)
                current_bulk_cutoff = datetime.now(timezone.utc) - timedelta(days=self.BULK_DELETE_DAYS)
                
                if message_time > current_bulk_cutoff:
                    bulk_delete_batch.append(message)
                    
                    # Process bulk deletions in batches
                    if len(bulk_delete_batch) >= self.BULK_DELETE_BATCH_SIZE:
                        success = await self._process_bulk_delete_batch(channel, bulk_delete_batch, user_counts)
                        if not success:
                            # If bulk deletion fails, add to individual deletion
                            for msg in bulk_delete_batch:
                                individual_delete_tasks.append((msg, msg.author.id))
                        bulk_delete_batch = []
                else:
                    # Individual deletion for older messages
                    individual_delete_tasks.append((message, message.author.id))
                    
                    # Process individual deletions in batches
                    if len(individual_delete_tasks) >= self.INDIVIDUAL_DELETE_BATCH_SIZE:
                        deleted_count = await self._process_individual_deletes(individual_delete_tasks, channel.name)
                        # Update user counts
                        for msg, user_id in individual_delete_tasks:
                            if deleted_count > 0 and user_id in user_counts:
                                user_counts[user_id] += 1
                                deleted_count -= 1
                        individual_delete_tasks = []
            
            # Process any remaining bulk deletions
            if bulk_delete_batch:
                current_bulk_cutoff = datetime.now(timezone.utc) - timedelta(days=self.BULK_DELETE_DAYS)
                eligible_for_bulk = all(
                    self._normalize_message_time(msg.created_at) > current_bulk_cutoff
                    for msg in bulk_delete_batch
                )
                
                if eligible_for_bulk:
                    success = await self._process_bulk_delete_batch(channel, bulk_delete_batch, user_counts)
                    if not success:
                        for msg in bulk_delete_batch:
                            individual_delete_tasks.append((msg, msg.author.id))
                else:
                    self.log.info(f"  Some messages too old for bulk deletion, processing {len(bulk_delete_batch)} individually")
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
            
            if total_deleted > 0:
                user_summary = ", ".join([f"{self.user_names[uid]}: {count}" for uid, count in user_counts.items() if count > 0])
                self.log.info(f"Completed {channel_name} in {elapsed_time.total_seconds():.1f}s: {total_deleted} messages deleted ({user_summary})")
            else:
                self.log.info(f"Completed {channel_name} in {elapsed_time.total_seconds():.1f}s: No messages deleted")
            
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