# Discord Bot Setup Guide

## Step-by-Step Instructions to Get a Discord Bot Token

### 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click the **"New Application"** button (top right)
3. Give your application a name (e.g., "NBA Cover Bot")
4. Click **"Create"**

### 2. Create a Bot User

1. In your application, go to the **"Bot"** section in the left sidebar
2. Click **"Add Bot"** or **"Reset Token"** if you already have a bot
3. Click **"Yes, do it!"** to confirm

### 3. Get Your Bot Token

1. In the **"Bot"** section, you'll see a **"Token"** section
2. Click **"Reset Token"** or **"Copy"** to reveal/copy your token
3. **⚠️ IMPORTANT:** Keep this token secret! Never share it publicly or commit it to version control
4. Copy the token

### 4. Configure Bot Permissions

1. Still in the **"Bot"** section, scroll down to **"Privileged Gateway Intents"**
2. Enable **"Message Content Intent"** (required for the bot to read message content)
3. Scroll to **"Bot Permissions"** and select:
   - **Read Messages/View Channels**
   - **Send Messages**
   - **Attach Files** (optional, but useful)

### 5. Invite Bot to Your Server

1. Go to the **"OAuth2"** → **"URL Generator"** section in the left sidebar
2. Under **"Scopes"**, check:
   - ✅ **bot**
   - ✅ **applications.commands** (optional, for slash commands)
3. Under **"Bot Permissions"**, check:
   - ✅ **Read Messages/View Channels**
   - ✅ **Send Messages**
   - ✅ **Attach Files**
4. Copy the generated URL at the bottom
5. Open the URL in your browser
6. Select the Discord server where you want to add the bot
7. Click **"Authorize"**
8. Complete any CAPTCHA if prompted

### 6. Use the Token

Set the token as an environment variable:

```bash
export DISCORD_TOKEN='your-token-here'
```

Or in your deployment script, replace `YOUR_TOKEN_HERE` with your actual token.

### 7. Verify Bot is Online

1. Go to your Discord server
2. Check the member list on the right
3. Your bot should appear with a green "Online" indicator
4. The bot should also print "Bot logged in as [BotName]" in the console

## Security Best Practices

- ✅ **Never commit tokens to git** - use environment variables or secrets management
- ✅ **Use `.env` files locally** (and add `.env` to `.gitignore`)
- ✅ **Rotate tokens** if you suspect they've been compromised
- ✅ **Use Cloud Run secrets** or similar for production deployments

## Troubleshooting

**Bot not responding?**
- Check that the bot is online in your server
- Verify the token is correct
- Make sure "Message Content Intent" is enabled
- Check bot permissions in the server

**"Missing Access" error?**
- The bot needs to be invited with proper permissions
- Re-invite the bot with the correct permissions

**Commands not working?**
- Make sure you're using the `!` prefix (e.g., `!upload_qimen`)
- Check that the bot has "Read Messages" permission
- Verify "Message Content Intent" is enabled in the Developer Portal


