import os
import discord
import aiohttp
from discord.ext import commands
from google.cloud import storage
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import io

TOKEN = os.getenv("DISCORD_TOKEN")
ASSETS_BUCKET = os.getenv("ASSETS_BUCKET", "nba-cover-assets")  # Bucket for qimen and player images
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")  # Optional GCP project ID

if not TOKEN:
    raise Exception("Missing DISCORD_TOKEN environment variable")

# ----- Cloud Run health check server -----
def start_health_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("", port), Handler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

threading.Thread(target=start_health_server, daemon=True).start()

# ----- Discord bot setup -----
intents = discord.Intents.default()
intents.message_content = True  # Important!

bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize storage client with project if available
storage_client = storage.Client(project=GCP_PROJECT) if GCP_PROJECT else storage.Client()
assets_bucket = storage_client.bucket(ASSETS_BUCKET)

async def upload_to_assets_bucket(content: bytes, path: str, content_type: str) -> str:
    """Upload content to the assets bucket at the specified path"""
    blob = assets_bucket.blob(path)
    blob.upload_from_string(content, content_type=content_type)
    
    # Try to generate signed URL (requires service account with private key)
    # If using application-default credentials (user credentials), fall back to public URL
    try:
        url = blob.generate_signed_url(
            version="v4",
            expiration=3600,  # 1 hour
            method="GET"
        )
        return url
    except Exception as e:
        # If signed URL generation fails (e.g., no private key), use public URL
        # This happens when using application-default user credentials
        if "private key" in str(e).lower() or "credentials" in str(e).lower():
            # Return public URL or GCS path
            return f"gs://{ASSETS_BUCKET}/{path}"
        else:
            # Re-raise if it's a different error
            raise

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

@bot.command(name="upload_qimen")
async def upload_qimen(ctx: commands.Context, filename: str):
    """
    Upload a qimen image to GCS bucket.
    Usage: !upload_qimen <filename>
    Example: !upload_qimen 2025-12-07.jpg
    """
    if not ctx.message.attachments:
        await ctx.reply("❌ Please attach an image to upload.")
        return
    
    # Get the first image attachment
    attachment = ctx.message.attachments[0]
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        await ctx.reply("❌ The attachment must be an image file.")
        return
    
    try:
        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    await ctx.reply(f"❌ Failed to download image. Status: {resp.status}")
                    return
                content = await resp.read()
        
        # Upload to GCS at qimen/filename
        gcs_path = f"qimen/{filename}"
        url = await upload_to_assets_bucket(
            content=content,
            path=gcs_path,
            content_type=attachment.content_type
        )
        
        await ctx.reply(f"✅ **Uploaded qimen image**\n`gs://{ASSETS_BUCKET}/{gcs_path}`\n{url}")
    except Exception as e:
        await ctx.reply(f"❌ Error uploading image: {str(e)}")

@bot.command(name="upload_player")
async def upload_player(ctx: commands.Context, filename: str):
    """
    Upload a player image to GCS bucket.
    Usage: !upload_player <filename>
    Example: !upload_player LAL_Doncic.png
    """
    if not ctx.message.attachments:
        await ctx.reply("❌ Please attach an image to upload.")
        return
    
    # Get the first image attachment
    attachment = ctx.message.attachments[0]
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        await ctx.reply("❌ The attachment must be an image file.")
        return
    
    try:
        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    await ctx.reply(f"❌ Failed to download image. Status: {resp.status}")
                    return
                content = await resp.read()
        
        # Upload to GCS at players/filename
        gcs_path = f"players/{filename}"
        url = await upload_to_assets_bucket(
            content=content,
            path=gcs_path,
            content_type=attachment.content_type
        )
        
        await ctx.reply(f"✅ **Uploaded player image**\n`gs://{ASSETS_BUCKET}/{gcs_path}`\n{url}")
    except Exception as e:
        await ctx.reply(f"❌ Error uploading image: {str(e)}")

@bot.command(name="generate_cover")
async def generate_cover_command(ctx: commands.Context, date: str, away_team: str, home_team: str, *args):
    """
    Generate a cover image by calling the external cover generator service.
    Usage: !generate_cover <date> <away_team> <home_team> <title_line1> <title_line2> [circle_cells...]
    Example: !generate_cover 2025-12-07 HOU GSW "火旺克金形势显" "刺锋遇曜力难前" 2 4
    
    Args:
        date: Date in format YYYY-MM-DD
        away_team: Away team code (e.g., HOU)
        home_team: Home team code (e.g., GSW)
        title_line1: First line of title (use quotes if it contains spaces)
        title_line2: Second line of title (use quotes if it contains spaces)
        circle_cells: Optional cell numbers (1-9) to overlay circles, space-separated
    """
    try:
        # Parse arguments
        if len(args) < 2:
            await ctx.reply("❌ **Usage:** `!generate_cover <date> <away_team> <home_team> <title_line1> <title_line2> [circle_cells...]`\n"
                          "**Example:** `!generate_cover 2025-12-07 HOU GSW \"火旺克金形势显\" \"刺锋遇曜力难前\" 2 4`")
            return
        
        title_lines = list(args[:2])
        circle_cells = [int(x) for x in args[2:]] if len(args) > 2 else []
        
        # Validate date format
        try:
            from datetime import datetime
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            await ctx.reply("❌ Invalid date format. Use YYYY-MM-DD (e.g., 2025-12-07)")
            return
        
        # Send "generating" message
        generating_msg = await ctx.reply("🔄 Generating cover image... This may take a moment.")
        
        # Get the cover generator service URL from environment variable or use default
        COVER_GENERATOR_URL = os.getenv("COVER_GENERATOR_URL", "https://cover-generator-169911608314.us-central1.run.app/generate")
        
        # Prepare request payload
        payload = {
            "date": date,
            "away_team": away_team,
            "home_team": home_team,
            "title": title_lines
        }
        
        # Add circle_cells if provided
        if circle_cells:
            payload["circle_cells"] = circle_cells
        
        # Call the external service
        async with aiohttp.ClientSession() as session:
            async with session.post(
                COVER_GENERATOR_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            ) as resp:
                if resp.status == 200:
                    # Read the image data
                    image_data = await resp.read()
                    
                    # Send the generated file
                    file = discord.File(io.BytesIO(image_data), filename=f"cover_{date}.jpg")
                    await generating_msg.edit(content="✅ **Cover generated!**")
                    await ctx.send(file=file)
                else:
                    error_text = await resp.text()
                    await generating_msg.edit(content=f"❌ **Error from cover generator service (status {resp.status}):**\n```{error_text[:500]}```")
                
    except aiohttp.ClientError as e:
        await ctx.reply(f"❌ **Network error calling cover generator:**\n```{str(e)}```")
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        await ctx.reply(f"❌ **Error generating cover:**\n```{error_msg}```")

# Run the Discord bot
bot.run(TOKEN)
