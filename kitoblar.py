import os
import asyncio
import logging
from telethon import TelegramClient
import sqlite3
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def safe_get_attr(obj, attr, default=None):
    """Safely get an attribute from an object."""
    try:
        return getattr(obj, attr) if hasattr(obj, attr) else default
    except:
        return default

# Telegram API credentials - you need to get these from https://my.telegram.org
API_ID = 27739307  # Replace with your API ID
API_HASH = "2a56b55695ba12a5aa71c402de2140ea"  # Replace with your API Hash
CHANNEL_USERNAME = "@kutubxonaa1"
BOOKS_FOLDER = "kitoblar"  # Folder to save downloaded books

async def setup():
    """Setup the necessary folders and database."""
    # Create books folder if it doesn't exist
    if not os.path.exists(BOOKS_FOLDER):
        os.makedirs(BOOKS_FOLDER)
        logger.info(f"Created folder: {BOOKS_FOLDER}")
    
    # Create database
    conn = sqlite3.connect('kutubxona.db')
    cursor = conn.cursor()
    
    # Create books table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        file_path TEXT NOT NULL,
        message_id INTEGER,
        file_size INTEGER,
        download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database setup complete")

async def download_books():
    """Download all PDF books from the Telegram channel."""
    # Check if API credentials are set
    if API_ID == 0 or API_HASH == "":
        logger.error("Please set your API_ID and API_HASH in the script")
        return
    
    # Setup client
    client = TelegramClient('kutubxona_session', API_ID, API_HASH)
    await client.start()
    
    # Get the channel entity
    channel = await client.get_entity(CHANNEL_USERNAME)
    
    # Connect to database
    conn = sqlite3.connect('kutubxona.db')
    cursor = conn.cursor()
    
    # Get existing message IDs to avoid re-downloading
    cursor.execute("SELECT message_id FROM books")
    existing_message_ids = {row[0] for row in cursor.fetchall()}
    
    # Download counter
    downloaded_count = 0
    skipped_count = 0
    total_count = 0
    
    logger.info(f"Starting to download books from {CHANNEL_USERNAME}")
    
    # Get messages from the channel
    try:
        async for message in client.iter_messages(channel, limit=None):
            total_count += 1
            
            # Print progress every 100 messages
            if total_count % 100 == 0:
                logger.info(f"Processed {total_count} messages, Downloaded: {downloaded_count}, Skipped: {skipped_count}")
            
            try:
                # Skip if already downloaded
                if message.id in existing_message_ids:
                    skipped_count += 1
                    continue
                
                # Check if the message has a document and it's a PDF
                document = safe_get_attr(message, 'document')
                if document and safe_get_attr(document, 'mime_type') == 'application/pdf':
                    # Extract title from caption or filename
                    title = None
                    
                    caption = safe_get_attr(message, 'caption')
                    if caption:
                        title = caption
                    
                    # If no caption, use filename
                    if not title:
                        attributes = safe_get_attr(document, 'attributes', [])
                        for attr in attributes:
                            file_name = safe_get_attr(attr, 'file_name')
                            if file_name:
                                title = file_name
                                if title.lower().endswith('.pdf'):
                                    title = title[:-4]  # Remove .pdf extension
                                break
                    
                    # If still no title, use a default
                    if not title:
                        title = f"Kitob_{message.id}"
                    
                    # Clean the title for use as a filename
                    safe_title = "".join([c if c.isalnum() or c in " .-_" else "_" for c in title])
                    safe_title = safe_title[:100]  # Limit length
                    
                    # Create a unique filename
                    file_path = os.path.join(BOOKS_FOLDER, f"{safe_title}_{message.id}.pdf")
                    
                    try:
                        # Download the file
                        await client.download_media(message, file_path)
                        
                        # Get file size
                        file_size = os.path.getsize(file_path)
                        
                        # Save to database
                        cursor.execute(
                            "INSERT INTO books (title, file_path, message_id, file_size) VALUES (?, ?, ?, ?)",
                            (title, file_path, message.id, file_size)
                        )
                        conn.commit()
                        
                        downloaded_count += 1
                        logger.info(f"Downloaded: {title} ({file_size/1024/1024:.2f} MB)")
                        
                    except Exception as e:
                        logger.error(f"Error downloading {title}: {e}")
            except Exception as e:
                logger.error(f"Error processing message {message.id}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error iterating through messages: {e}")
    
    # Final stats
    logger.info(f"Download complete. Total messages: {total_count}")
    logger.info(f"Downloaded: {downloaded_count}, Skipped: {skipped_count}")
    
    # Close connections
    conn.close()
    await client.disconnect()

async def main():
    """Main function to setup and download books."""
    await setup()
    await download_books()

if __name__ == "__main__":
    asyncio.run(main())
