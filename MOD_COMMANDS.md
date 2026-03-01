# Moderator Commands Documentation

This document provides a comprehensive guide to all moderator commands available in the Devils Discord Bot.

## Table of Contents
- [Game Channel Management](#game-channel-management)
- [Message Management](#message-management)
- [Role Management](#role-management)
- [User Management](#user-management)
- [Incident Reports](#incident-reports)
- [Settings (Admin Only)](#settings-admin-only)
- [System Commands (Admin Only)](#system-commands-admin-only)

---

## Game Channel Management

### `/open`
Opens the game chat channel(s) and starts automatic periodic reminders.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `message` (optional): Custom message to send when opening the channel
  - If not provided, uses the default message "Game chat is now open!"
  - The reminder message is automatically appended to your custom message

**Example Usage:**
```
/open
/open message:"Let's go Devils! Game starts in 30 minutes!"
```

**What This Does:**
1. Changes channel permissions to allow configured roles to send messages
2. Posts your message (or default message) to all configured game channels
3. Appends the community rules reminder to your message
4. Starts an automatic task that posts reminders every 15 minutes
5. Logs the action with your username and timestamp

**Notes:**
- Automatically posts reminders every 15 minutes while channels are open
- Reminders will continue until channels are closed or the bot restarts
- Multiple game channels can be configured in bot settings
- The reminder message helps keep chat civil during games
- Your command response is automatically deleted after 3 seconds

---

### `/close`
Closes the game chat channel(s) and stops automatic reminders.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `message` (optional): Custom message to send when closing the channel
  - If not provided, closes without a message

**Example Usage:**
```
/close
/close message:"Great game everyone! See you next time!"
```

**What This Does:**
1. Changes channel permissions to prevent non-moderators from sending messages
2. Posts your closing message to all configured game channels (if provided)
3. Stops the automatic reminder task immediately
4. Logs the action with your username and timestamp
5. Removes all users from the allowed-to-send-messages list

**Notes:**
- Automatically stops the periodic reminder task
- Your command response is automatically deleted after 3 seconds
- The reminder task will also stop automatically if the bot detects the channel is already closed

---

## Message Management

### `/say`
Send a message as the bot to any channel.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `message` (optional): The message to send
  - If not provided, the bot will prompt you to type the message (5-minute timeout)
  - Supports Discord markdown, mentions, and emojis
- `channel` (optional): The channel to send the message to
  - If not provided, sends to the current channel
- `attachment` (optional): A file to attach to the message
  - Images, videos, documents, etc.

**Example Usage:**
```
/say message:"Welcome to the server!" channel:#general
/say channel:#announcements
/say message:"Check out this image!" attachment:[file]
```

**How It Works:**
1. If `message` is provided: sends immediately to the target channel
2. If `message` is not provided:
   - Bot responds: "Enter the message you want to say (you have 5 minutes):"
   - You type your message as a normal message (not a command)
   - Bot sends your message content to the target channel
   - If you don't respond within 5 minutes: "I don't have all day! Retry if you want."
3. If `attachment` is provided, it's converted to a Discord file and attached
4. Logs the action with your username and target channel

**Notes:**
- Your command confirmation is deleted after 3 seconds to keep channels clean
- The message will appear as if the bot sent it (shows bot's name and avatar)
- Useful for announcements, automated messages, or speaking as the bot
- The bot must have send permissions in the target channel

---

### `/editmsg`
Edit a message that was previously posted by the bot.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `message_id` (required): The ID of the message to edit
  - Right-click on the message → Copy Message ID (Developer Mode must be enabled)
  - Must be a message the bot originally sent

**Example Usage:**
```
/editmsg message_id:1234567890123456789
```

**How It Works:**
1. Retrieves the message by ID using Discord's message converter
2. Checks if the message was sent by the bot (rejects if not)
3. Shows you the current message content in a code block
4. Prompts: "Enter the message you want to say (you have 5 minutes):"
5. You type the new message content
6. Bot updates the message with your new content
7. Confirms: "Message edited!"

**Notes:**
- The bot will show you the current message content in a code block format
- You'll have 5 minutes to type the new message content
- **Can only edit messages posted by the bot** - you'll get an error if you try to edit user messages
- The message's timestamp will show "(edited)" in Discord
- Useful for fixing typos or updating information in announcements
- Attachments cannot be edited, only text content

---

### `/reply`
Reply to a message as the bot.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `message_id` (required): The ID of the message to reply to
- `message` (optional): The reply message content
  - If not provided, the bot will prompt you to type the message (5-minute timeout)
- `attachment` (optional): A file to attach to the reply

**Example Usage:**
```
/reply message_id:1234567890123456789 message:"Thanks for your feedback!"
/reply message_id:1234567890123456789 attachment:[file]
```

---

## Role Management

### `/role`
Add or remove roles from users.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `role` (required): The role to add or remove
- `action` (required): Choose "add" or "remove"
- `user` (required): The user to modify roles for

**Example Usage:**
```
/role role:@Member action:add user:@JohnDoe
/role role:@Verified action:remove user:@JaneDoe
```

**How It Works:**
- **Adding a role:** Checks if user already has it, then adds it if they don't
- **Removing a role:** Removes the role from the user (no error if they don't have it)
- Logs the action to the admin log with your username, the role, and the target user

**Role Hierarchy Protection:**
- You **cannot** add/remove roles equal to or higher than your highest role
- **Exceptions:** Server owner and bot developers bypass this restriction
- This prevents moderators from escalating their own privileges or others'
- If you try to manage a role above your level, you'll get an error message

**Response Messages:**
- **Adding (success):** "{user} has been given a role called: {role}"
- **Adding (already has):** "{user} already has a role called: {role}"
- **Removing:** "{user} has been stripped of a role called: {role}"
- **Permission error:** "You're not allowed to add/remove a role that's equal to or above your highest role!"

---

## User Management

### `/timeout`
Timeout (mute) a user for a specified duration.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `user` (required): The user to timeout
- `duration` (required): How long to timeout the user
  - Formats: "1h", "30m", "2h30m", "1d", etc.
  - Supports combinations: "1d12h", "2h45m"
  - Maximum: 28 days (Discord limitation)
- `reason` (optional): Reason for the timeout
  - If not provided, defaults to "None"

**Example Usage:**
```
/timeout user:@User duration:1h reason:"Spamming in chat"
/timeout user:@User duration:30m
/timeout user:@User duration:2h30m reason:"Inappropriate behavior"
```

**What This Does:**
1. Applies a Discord timeout to the user for the specified duration
2. **If `reason` is provided:** Automatically creates an incident report with:
   - User ID
   - Reason provided
   - Decision: "Timed out for [duration]"
   - Your user ID as the moderator
   - Current timestamp
3. Responds with confirmation message showing user and duration
4. Logs the action to the bot's admin log file

**Important Notes:**
- **⚠️ Automatically creates an incident report ONLY if you provide a `reason`**
  - If no reason is given, the timeout is applied but no incident report is created
  - Best practice: Always include a reason to maintain proper records
- The user will be unable to:
  - Send messages in any channel
  - Add reactions to messages
  - Speak in voice channels
  - Join voice channels
- The timeout is automatically removed after the duration expires
- The incident report (if created) is permanent and can be retrieved with `/get_incident`
- If duration parsing fails, you'll receive an error message

---

## Incident Reports

### `/create_incident`
Create an incident report for a user.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `user` (required): The user the incident is about
- `description` (required): Description of what happened
  - Be specific and detailed
  - Include context and relevant information
- `decision` (required): The moderation decision/action taken
  - Examples: "Verbal warning", "Messages deleted", "Banned for 7 days"

**Example Usage:**
```
/create_incident user:@User description:"User was spamming links" decision:"Warned and messages deleted"
/create_incident user:@User description:"Repeatedly using slurs after warning" decision:"7-day ban issued"
```

**What Gets Stored:**
The incident report permanently stores:
1. **User ID** - The Discord ID of the user (persists even if they leave the server)
2. **Description** - Your description of what happened
3. **Decision** - The action you took
4. **Reported By** - Your user ID (who created the report)
5. **Reported At** - Timestamp when the report was created
6. **Incident ID** - Unique identifier for this incident

**Notes:**
- Automatically logs who created the report and when
- Incidents are **permanently stored in the database** - they cannot be deleted
- Use this to maintain a record of user violations
- **Note:** `/timeout` automatically creates an incident report, so you don't need to create one separately for timeouts
- These reports help track repeat offenders and establish patterns of behavior
- Can be retrieved later even if the user has left the server using `/get_incident user_id:[id]`

---

### `/get_incident`
Retrieve incident reports for a specific user.

**Permissions Required:** Moderator or Administrator

**Parameters:**
- `user` (optional): The Discord user to look up
  - For current server members
- `user_id` (optional): The user ID to look up (useful for users who left the server)
  - Right-click user → Copy User ID
  - Or paste a known user ID

**Example Usage:**
```
/get_incident user:@User
/get_incident user_id:123456789012345678
```

**What This Shows:**
Each incident report displays:
- **Incident ID** - Unique database identifier
- **Description** - What happened (from the report)
- **Decision** - Action taken by moderator
- **Reported By** - Which moderator created the report (shown as user ID)
- **Reported At** - Date and timestamp of the incident

**Navigation:**
- **<<** - Jump to first incident
- **<** - Previous incident
- **Page indicator** - Shows current page number
- **>** - Next incident
- **>>** - Jump to last incident

**Notes:**
- At least one parameter must be provided (either `user` or `user_id`)
- Results are displayed in a paginated embed format if multiple incidents exist
- Shows **all historical incidents** for the user, even very old ones
- If no incidents are found, displays "No incidents found for this user."
- Use `user_id` parameter when the user has left the server but you still need their history
- The command will "defer" briefly while fetching data from the database

---

## Settings (Admin Only)

### `/settings role`
Manage role settings for various bot categories.

**Permissions Required:** Administrator

**Parameters:**
- `category` (required): Choose from:
  - `gamechat` - Roles allowed in game channels
  - `banished` - Roles that are banished/restricted
- `action` (required): "add" or "remove"
- `role` (required): The role to manage

**Example Usage:**
```
/settings role category:gamechat action:add role:@Fan
/settings role category:banished action:add role:@Muted
```

---

### `/settings channel`
Manage channel settings for various bot categories.

**Permissions Required:** Administrator

**Parameters:**
- `category` (required): Choose from:
  - `game` - Game discussion channels (affected by `/open` and `/close`)
  - `meetup` - Meetup/event channels
  - `highlight` - Highlight/clip channels (where highlights are posted)
  - `socialmedia` - Social media announcement channels
  - `fourtwenty` - 4:20 notification channels (for 4:20 PM notifications)
  - `modmail` - Modmail channels (where modmail messages are sent)
- `action` (required): "add" or "remove"
- `channel` (required): The channel to manage

**Example Usage:**
```
/settings channel category:game action:add channel:#game-chat
/settings channel category:modmail action:add channel:#mod-mail
```

**What Each Category Does:**
- **game**: Channels that `/open` and `/close` will affect. When opened, configured roles can chat. When closed, only mods can chat.
- **meetup**: Channels designated for organizing meetups and events
- **highlight**: Channels where game highlights and clips are automatically posted
- **socialmedia**: Channels for social media announcements and updates
- **fourtwenty**: Channels that receive the 4:20 notification (the bot posts at 4:20 PM daily)
- **modmail**: Channels where modmail messages are forwarded to the mod team

**Notes:**
- You can add multiple channels to each category
- Settings are stored in the database and persist across bot restarts
- Use `/getconfig` to view all current channel settings

---

### `/settings reactalert`
Manage messages that trigger reaction alerts.

**Permissions Required:** Administrator

**Parameters:**
- `action` (required): "add" or "remove"
- `message` (required): The message ID to manage

**Example Usage:**
```
/settings reactalert action:add message:1234567890123456789
```

**Notes:**
- React alerts notify moderators when certain messages receive reactions

---

### `/getconfig`
View the current bot configuration.

**Permissions Required:** Administrator

**Parameters:** None

**Example Usage:**
```
/getconfig
```

**What This Shows:**
Displays an embed with all bot settings:
- **Game Channels** - Channels affected by `/open` and `/close`
- **Game Channels Role** - Roles allowed to chat in game channels when open
- **Highlight Channels** - Where highlights are posted
- **ModMail Channel** - Where modmail is sent
- **Social Media Channels** - Social media announcement channels
- **Four Twenty Channels** - Channels for 4:20 notifications
- **Banished Roles** - Roles that are restricted/banned
- **Meetup Channels** - Meetup and event channels

**Notes:**
- Displays all configured channels and roles in a formatted embed
- Channels are shown as clickable mentions (e.g., <#123456>)
- Roles are shown as clickable mentions (e.g., <@&123456>)
- If a setting has no values, displays "None"
- Useful for verifying configuration before making changes
- Shows the command used to retrieve config: `/getconfig`

---

## System Commands (Admin Only)

### `/restart`
Restart the bot.

**Permissions Required:** Administrator

**Parameters:** None

**Example Usage:**
```
/restart
```

**Notes:**
- Use this to apply updates or fix issues
- The bot will reconnect automatically
- Responds with "BRB..." before restarting

---

### `/kill`
Stop the bot completely.

**Permissions Required:** Administrator

**Parameters:** None

**Example Usage:**
```
/kill
```

**Notes:**
- The bot will not restart automatically
- Requires manual intervention to start again
- Use only when necessary (maintenance, emergencies)

---

### `/loadcog`
Load a bot cog/module.

**Permissions Required:** Administrator

**Parameters:**
- `cog` (required): The name of the cog to load (e.g., "devils", "pickems")

**Example Usage:**
```
/loadcog cog:pickems
```

**Notes:**
- Used to enable features without restarting the entire bot
- Cog must exist in the `cogs/` directory

---

### `/unloadcog`
Unload a bot cog/module.

**Permissions Required:** Administrator

**Parameters:**
- `cog` (required): The name of the cog to unload

**Example Usage:**
```
/unloadcog cog:pickems
```

**Notes:**
- Temporarily disables features without restarting
- Useful for debugging or maintenance

---

### `/reloadcog`
Reload a bot cog/module.

**Permissions Required:** Administrator

**Parameters:**
- `cog` (required): The name of the cog to reload

**Example Usage:**
```
/reloadcog cog:devils
```

**Notes:**
- Useful for applying code changes without restarting the bot
- Combines unload and load in one command

---

## Tips for Moderators

1. **Enable Developer Mode** in Discord Settings → Advanced → Developer Mode to easily copy message and user IDs
2. **Incident Reports** should be created for any significant moderation action to maintain a permanent record
3. **Game Channels** automatically post reminders every 15 minutes when open - no need to manually remind users
4. **⚠️ Timeouts automatically create incident reports ONLY if you include a `reason`** - always provide a reason to maintain proper records
5. **Message Management** commands (`/say`, `/editmsg`, `/reply`) are useful for announcements and community management
6. **Check User History** with `/get_incident` before taking action on repeat offenders
7. **Be Specific** in incident reports - include context, what rule was violated, and any relevant message links
8. **Use `user_id` Instead of `user`** in `/get_incident` when looking up users who have left the server
9. **Save Message IDs** for important messages you might need to edit later
10. **Contact an Administrator** if you need to modify bot settings or use system commands
11. **Log Important Actions** - create incident reports even for warnings to track patterns
12. **Duration Formats** for `/timeout`: combine units like "1d12h" or "2h30m" for precise timeouts

---

## Common Workflows

### Opening Game Chat for a Game
```
1. /open message:"Game starts at 7:00 PM! Go Devils!"
2. (Bot automatically posts reminders every 15 minutes)
3. After game ends: /close message:"Great game everyone!"
```

### Handling a Rule Violation with Timeout
```
1. /timeout user:@Offender duration:1h reason:"Violated rule #3"
   ⚠️ Including the reason automatically creates an incident report - no need to create one separately!
2. Optional: /say message:"Reminder to everyone: Please follow rule #3!" channel:#general
3. Optional: Document in mod channel: /say message:"@Offender timed out for 1h - rule #3 violation" channel:#mod-log
```

### Quick Timeout Without Documentation
```
1. /timeout user:@User duration:10m
   Note: No reason provided = no incident report created
2. Use this for very minor/temporary timeouts that don't need permanent records
3. For anything that should be tracked, always include a reason!
```

### Handling a Warning (No Timeout)
```
1. Warn the user in chat or DM
2. /create_incident user:@User description:"User posted NSFW content in #general" decision:"Verbal warning issued, content deleted"
3. Keep a record for future reference
```

### Managing a User with History
```
1. /get_incident user:@User (Check their history)
2. Based on history, decide action
3. /create_incident or /timeout as appropriate
```

### Making an Announcement
```
1. /say message:"Important announcement here!" channel:#announcements
2. If you made a typo:
   - Copy the message ID
   - /editmsg message_id:[paste ID]
   - Type the corrected message
```

---

## Support

If you have questions about these commands or need assistance:
- Contact a bot administrator
- Check the bot logs for error messages
- Review incident reports for precedent on handling similar situations
