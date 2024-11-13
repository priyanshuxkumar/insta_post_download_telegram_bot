import os
import  instaloader
import aiohttp
import asyncio
from  telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

L = instaloader.Instaloader()

username = os.environ['LOGIN_USERNAME']
password = os.environ['LOGIN_PASSWORD']

L.login(username, password)

async def download_file(url, filename):
    """Download a file from a URL and save it to the specified filename."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(filename, 'wb') as f:
                        f.write(await response.read())
                    print(f"Downloaded: {filename}")
                    return filename
                else:
                    print(f"Failed to download {url}: Status {response.status}")
                    return None
    except Exception as e:
        print(f"Error in download_file: {e}")
        return None

async def download_instagram_media(url):
    """Fetches Instagram media URLs and downloads them."""
    video_url = None
    image_url = None
    try:
        # Extract the shortcode from the URL and fetch the post
        shortcode = url.split('/')[-2]
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        downloaded_media_paths = []

        # Check if the post is a carousel (multiple images or videos)
        if post.typename == "GraphSidecar":
            print("Carousel post detected!")
            tasks = []
            for index, node in enumerate(post.get_sidecar_nodes()):
                if node.is_video:
                    video_url = node.video_url
                    filename = os.path.join("downloads/video", f"{shortcode}_{index}.mp4")
                else:
                    image_url = node.display_url
                    filename = os.path.join("downloads/photo", f"{shortcode}_{index}.jpg")
                tasks.append(download_file(video_url if node.is_video else image_url, filename))
            downloaded_media_paths = await asyncio.gather(*tasks)

        elif post.is_video:
            print("Reel or Video detected!")
            video_url = post.video_url
            filename = os.path.join("downloads/video", f"{shortcode}.mp4")
            path = await download_file(video_url, filename)
            if path:
                downloaded_media_paths.append(path)

        else:
            print("Single image post detected!")
            image_url = post.url
            filename = os.path.join("downloads/photo", f"{shortcode}.jpg")
            path = await download_file(image_url, filename)
            if path:
                downloaded_media_paths.append(path)

        return downloaded_media_paths
    except Exception as e:
        print(f"Error downloading media: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello, I'm a bot! I can download Instagram posts and reels for you.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text
    if "instagram.com" in url:
        await update.message.reply_text("Fetching your media, please wait...")

        # Download media and get the list of paths
        media_paths = await download_instagram_media(url)

        if media_paths:
            for media_path in media_paths:
                try:
                    if media_path.endswith(".mp4"):
                        await update.message.reply_video(video=open(media_path, 'rb'))
                    elif media_path.endswith(".jpg"):
                        await update.message.reply_photo(photo=open(media_path, 'rb'))
                except Exception as e:
                    print(f"Error sending media: {e}")
                    await update.message.reply_text(f"Error sending media: {e}")
                finally:
                    if os.path.exists(media_path):
                        os.remove(media_path)
        else:
            await update.message.reply_text("Could not retrieve media. Please check the link or try again later.")
    else:
        await update.message.reply_text("Please send a valid Instagram post or reel link.")



def main():
    telegram_token = os.environ['TELEGRAM_TOKEN']

    # Initialize the Application
    app = Application.builder().token(telegram_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("Starting bot...")
    app.run_polling()

if __name__ == '__main__':
    os.makedirs("downloads/photo", exist_ok=True)
    os.makedirs("downloads/video", exist_ok=True)
    main()