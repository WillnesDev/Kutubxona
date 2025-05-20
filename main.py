import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token - replace with your bot token from BotFather
BOT_TOKEN = "7768438367:AAHaIwU7Edef6wpfqhoKjH-ZSgcViNsYSak"  # Replace with your bot token
BOOKS_FOLDER = "kitoblar"  # Folder where books are stored
DB_PATH = "kutubxona.db"  # Path to the SQLite database

# Check if database exists
def check_database():
    """Check if the database exists and has books."""
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file {DB_PATH} not found. Run kitoblar.py first.")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM books")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        logger.warning("No books found in the database. Run kitoblar.py to download books.")
        return False
    
    logger.info(f"Found {count} books in the database.")
    return True

# Bot command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Assalomu alaykum, {user.mention_html()}! Kutubxona botiga xush kelibsiz.\n"
        f"Kitob nomini yozing va men sizga PDF faylini yuboraman.\n\n"
        f"Barcha kitoblar @kutubxonaa1 kanalidan olingan."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Kitob nomini yozing va men sizga PDF faylini yuboraman.\n"
        "/search <kitob nomi> - Kitobni qidirish\n"
        "/stats - Kutubxona statistikasi\n"
        "/help - Yordam xabarini ko'rsatish"
    )

async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for books by title."""
    query = update.message.text
    
    # If command is /search, extract the query
    if query.startswith('/search'):
        query = query.replace('/search', '').strip()
    
    if not query:
        await update.message.reply_text("Iltimos, kitob nomini kiriting.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, file_path FROM books WHERE title LIKE ? ORDER BY title", (f"%{query}%",))
    books = cursor.fetchall()
    conn.close()
    
    if not books:
        await update.message.reply_text("Afsuski, bunday kitob topilmadi.")
        return
    
    if len(books) == 1:
        book_id, title, file_path = books[0]
        await update.message.reply_text(f"Kitob topildi: {title}")
        
        # Check if file exists
        if os.path.exists(file_path):
            await update.message.reply_document(document=open(file_path, 'rb'), filename=os.path.basename(file_path))
        else:
            await update.message.reply_text("Afsuski, kitob fayli topilmadi.")
    else:
        keyboard = []
        for book in books[:10]:  # Limit to 10 results
            book_id, title, _ = book
            display_text = title
            if len(display_text) > 60:  # Truncate long titles
                display_text = display_text[:57] + "..."
            keyboard.append([InlineKeyboardButton(display_text, callback_data=f"book_{book_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"{len(books)} ta kitob topildi. Tanlang:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("book_"):
        book_id = int(query.data.split("_")[1])
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT title, file_path FROM books WHERE id = ?", (book_id,))
        book = cursor.fetchone()
        conn.close()
        
        if book:
            title, file_path = book
            await query.message.reply_text(f"Kitob: {title}")
            
            # Check if file exists
            if os.path.exists(file_path):
                await query.message.reply_document(document=open(file_path, 'rb'), filename=os.path.basename(file_path))
            else:
                await query.message.reply_text("Afsuski, kitob fayli topilmadi.")
        else:
            await query.message.reply_text("Afsuski, kitob topilmadi.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show library statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get total books count
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]
    
    # Get total size
    cursor.execute("SELECT SUM(file_size) FROM books")
    total_size = cursor.fetchone()[0] or 0
    total_size_mb = total_size / 1024 / 1024
    
    conn.close()
    
    await update.message.reply_text(
        f"📚 Kutubxona statistikasi:\n\n"
        f"Jami kitoblar soni: {total_books}\n"
        f"Umumiy hajmi: {total_size_mb:.2f} MB\n\n"
        f"Manba: @kutubxonaa1"
    )

def main() -> None:
    """Start the bot."""
    # Check if database exists and has books
    if not check_database():
        logger.warning("Starting bot without books. Run kitoblar.py to download books.")
    
    # Check if bot token is set
    if not BOT_TOKEN:
        logger.error("Bot token not set. Please set your bot token in the script.")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_books))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_books))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot started. Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
