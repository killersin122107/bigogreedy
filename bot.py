import telegram
from telegram.ext import CommandHandler, ApplicationBuilder, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, constants
import random
import json
import os
import re

# --- Configuration ---
# 🚨 SECURITY NOTE: Reads token from environment variable 'TELEGRAM_BOT_TOKEN' if set, 
# falling back to the hardcoded value for development if needed.
ENV_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
HARDCODED_TOKEN = '8388906103:AAFD95dM56PiTLcciA6daGNLvTqjYA_fPL0'
TOKEN = ENV_TOKEN if ENV_TOKEN else HARDCODED_TOKEN

if not ENV_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN environment variable not set. Using hardcoded token.")

DATA_FILE = 'data_wheel.json'
BUTTON_TEXT = "View External Report"

# --- GAME CONFIGURATION: 8 Food Symbols ---
EIGHT_SYMBOLS = [
    '🥕 Carrot', '🥬 Cabbage', '🌽 Corn',
    '🌭 Hotdog', '🍅 Tomato', '🍢 Barbeque',
    '🥩 Steak', '🍖 Meat'
]
USER_ROLL_STATE = {}

# --- Data Management Functions ---

def load_data():
    """Loads history, counts, and configuration from the JSON file."""
    default_data = {
        "history": [],
        "symbol_counts": {symbol: 0 for symbol in EIGHT_SYMBOLS},
        "config": {
            "analysis_url_base": "https://queenking.ph/game/play/STUDIO-CGM-CGM002-by-we",
            "username": "09925345945",
            "password": "Shiwashi21"
        }
    }
    if not os.path.exists(DATA_FILE):
        return default_data
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            data.setdefault('symbol_counts', default_data['symbol_counts'])
            data.setdefault('config', default_data['config'])
            for symbol in EIGHT_SYMBOLS:
                if symbol not in data['symbol_counts']:
                    data['symbol_counts'][symbol] = 0
            return data
    except json.JSONDecodeError:
        return default_data

def save_data(data):
    """Saves the current data state to the JSON file."""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

def update_data_with_roll(rolled_symbol, data):
    """Updates history and symbol counts after a roll."""
    data['history'].append(rolled_symbol[0])
    data['symbol_counts'][rolled_symbol[0]] += 1
    save_data(data)

# --- ANALYSIS AND PREDICTION FUNCTIONS ---

def find_coldest_symbol(data):
    """Identifies the single symbol that has not appeared for the longest consecutive number of spins."""
    history = data['history']
    if not history:
        return 0, ""

    coldest_streaks = {}
    for symbol in EIGHT_SYMBOLS:
        streak_count = 0
        for spin in reversed(history):
            if symbol == spin:
                break
            else:
                streak_count += 1
        coldest_streaks[symbol] = streak_count

    max_streak = max(coldest_streaks.values())
    coldest_symbols = [symbol for symbol, streak in coldest_streaks.items() if streak == max_streak]

    coldest_symbol = coldest_symbols[0]
    coldest_streak_length = max_streak

    return coldest_streak_length, coldest_symbol

def get_predictions_with_reasoning(data):
    """Generates 3 predictions based on different patterns and provides reasoning."""
    total_spins = len(data['history'])

    if total_spins < 8:
        # Not enough data for meaningful pattern analysis
        return {
            "reasoning": "Need at least 8 spins to start meaningful pattern tracking."
        }

    counts = data['symbol_counts']

    # 1. Primary Bet (Martingale/Cold Streak)
    coldest_streak_length, single_coldest = find_coldest_symbol(data)

    # 2. Sort by Frequency (for Coldest Group and Most Frequent)
    sorted_counts = sorted(counts.items(), key=lambda item: item[1])

    # 2. Secondary Bet (Coldest Group/Low Frequency Spread)
    # The two symbols with the absolute lowest overall hit counts
    coldest_group = [item[0] for item in sorted_counts[:2]]
    coldest_group_str = f"{coldest_group[0]} and {coldest_group[1]}"

    # 3. Tertiary Bet (Most Frequent/Hot Trend)
    most_frequent = sorted_counts[-1][0]


    predictions = {
        "primary": f"**{single_coldest}**",
        "primary_reason": f"Martingale (Longest Missed Streak: {coldest_streak_length} rounds)",

        "secondary": f"**{coldest_group_str}**",
        "secondary_reason": "Spread Bet (Lowest Overall Hit Counts/Due for Long-Term Catch-up)",

        "tertiary": f"**{most_frequent}**",
        "tertiary_reason": "Hot Streak (Highest Overall Count/Following Current Trend)",
    }

    return predictions

# --- Utility and Command Handlers ---

async def reset_history(update, context):
    """Resets all recorded history and counts, and confirms pattern reset."""
    initial_data = load_data()
    initial_data['history'] = []
    initial_data['symbol_counts'] = {symbol: 0 for symbol in EIGHT_SYMBOLS}
    save_data(initial_data)
    await update.message.reply_text(
        "✅ **Spinner History Reset!** All past spins and statistics have been cleared.\n"
        "**NOTE:** All existing patterns have been **RESET**.",
        parse_mode=constants.ParseMode.MARKDOWN
    )

def create_symbol_keyboard(roll_number):
    """Creates the inline keyboard with new food symbol buttons."""
    keyboard = [
        [InlineKeyboardButton("🥕 Carrot", callback_data=f"roll_{roll_number}_Carrot"),
         InlineKeyboardButton("🥬 Cabbage", callback_data=f"roll_{roll_number}_Cabbage")],
        [InlineKeyboardButton("🌽 Corn", callback_data=f"roll_{roll_number}_Corn"),
         InlineKeyboardButton("🌭 Hotdog", callback_data=f"roll_{roll_number}_Hotdog")],
        [InlineKeyboardButton("🍅 Tomato", callback_data=f"roll_{roll_number}_Tomato"),
         InlineKeyboardButton("🍢 Barbeque", callback_data=f"roll_{roll_number}_Barbeque")],
        [InlineKeyboardButton("🥩 Steak", callback_data=f"roll_{roll_number}_Steak"),
         InlineKeyboardButton("🍖 Meat", callback_data=f"roll_{roll_number}_Meat")],
    ]
    return InlineKeyboardMarkup(keyboard)

def format_last_15_spins(data):
    """Formats the last 15 single spins for display."""
    history = data['history']
    if not history: return "History: No spins logged yet."

    recent_history = history[-15:]
    start_index = len(history) - len(recent_history) + 1

    spin_list = []
    for i, symbol in enumerate(recent_history):
        spin_str = f"**#{start_index + i}:** {symbol}"
        spin_list.append(spin_str)

    return f"📜 **Last {len(recent_history)} Logged Spins:**\n" + "\n".join(spin_list)

def analysis_msg_from_counts(data):
    """Helper function to format frequency analysis for the /analyze command."""
    total_spins = len(data['history'])
    if total_spins == 0:
        return ""
    counts = data['symbol_counts']
    sorted_probs = sorted(counts.items(), key=lambda item: item[1])
    least_likely = sorted_probs[0]
    most_likely = sorted_probs[-1]

    # Format all counts for a clearer view
    count_details = "\n".join([f"- {symbol}: {count} hits" for symbol, count in sorted(counts.items())])

    return (
        f"**Symbol Counts:**\n{count_details}\n"
        f"\n*Quick Stats:*\n"
        f"🥇 **Most Frequent:** {most_likely[0]} ({most_likely[1] / total_spins:.2%})\n"
        f"📉 **Least Frequent:** {least_likely[0]} ({least_likely[1] / total_spins:.2%})"
    )

async def start(update, context):
    """Sends a greeting message with a full list of commands."""
    welcome_message = (
        "Welcome! I analyze the **8-Symbol Spinner Wheel** game using statistics.\n\n"
        "### 🕹️ **Game Commands**\n"
        "• **/spin** or **/predict**: Start the button-selection process to log a new result and get the next prediction.\n"
        "• **/analyze**: View the full statistical breakdown, last 15 spins, and all predicted symbols.\n\n"
        "### ⚙️ **Administrative Commands**\n"
        "• **/setbaseurl [url]**: Set the base URL for the external analysis report.\n"
        "• **/setcreds [user] [pass]**: Set the username and password used to access the analysis link.\n"
        "• **/reset**: Clear all logged history and statistics (DANGEROUS!)."
    )
    await update.message.reply_text(welcome_message, parse_mode=constants.ParseMode.MARKDOWN)

async def set_analysis_base_url(update, context):
    if not context.args:
        await update.message.reply_text("⚠️ Please provide the base URL after the command. Example: **/setbaseurl https://your-website.com/report**", parse_mode=constants.ParseMode.MARKDOWN)
        return
    new_base_url = context.args[0]
    data = load_data()
    data['config']['analysis_url_base'] = new_base_url
    save_data(data)
    await update.message.reply_text(f"✅ **Analysis Base URL Updated!**\nThe new base URL is: `{new_base_url}`.", parse_mode=constants.ParseMode.MARKDOWN)

async def set_credentials(update, context):
    if len(context.args) != 2:
        await update.message.reply_text("⚠️ Please provide both your **username** and **password**. Example: **/setcreds user pass**", parse_mode=constants.ParseMode.MARKDOWN)
        return
    username = context.args[0]
    password = context.args[1]
    data = load_data()
    data['config']['username'] = username
    data['config']['password'] = password
    save_data(data)
    await update.message.reply_text(f"✅ **Credentials Saved!**\nUsername: `{username}`", parse_mode=constants.ParseMode.MARKDOWN)

async def start_roll(update, context):
    """Starts the single-symbol selection process via buttons. Used by /spin and /predict."""
    user_id = update.effective_user.id
    USER_ROLL_STATE[user_id] = [None]
    keyboard = create_symbol_keyboard(roll_number=1)
    await update.message.reply_text(
        "🎰 **Spin Result:** Please select the symbol that was hit.",
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def handle_color_callback(update, context):
    """Handles symbol selection button clicks and generates 3 predictions instantly."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data.split('_')

    if len(data) != 3 or user_id not in USER_ROLL_STATE:
        await query.edit_message_text("Error: Spin session timed out or invalid data. Use /spin to start again.")
        return

    roll_number = int(data[1])
    selected_short_name = data[2]

    full_symbol_name = next((s for s in EIGHT_SYMBOLS if selected_short_name in s.split(' ')), None)

    if roll_number == 1 and full_symbol_name:
        USER_ROLL_STATE[user_id][0] = full_symbol_name
        rolled_symbol = USER_ROLL_STATE.pop(user_id)

        game_data = load_data()
        update_data_with_roll(rolled_symbol, game_data)

        # --- GENERATE 3 PREDICTIONS WITH REASONING ---
        predictions = get_predictions_with_reasoning(game_data)

        if "reasoning" in predictions:
              prediction_message = predictions["reasoning"]
        else:
            prediction_message = (
                f"1. **{predictions['primary']}** *({predictions['primary_reason']})*\n"
                f"2. **{predictions['secondary']}** *({predictions['secondary_reason']})*\n"
                f"3. **{predictions['tertiary']}** *({predictions['tertiary_reason']})*"
            )

        # Build the Message to prioritize the next bet
        full_analysis_message = (
            f"✅ **Spin Logged!** Result: **{rolled_symbol[0]}**\n\n"
            f"--- **🎯 PREDICTIONS FOR NEXT SPIN (18s Window) 🎯** ---\n"
            f"{prediction_message}"
        )

        await query.edit_message_text(
            full_analysis_message,
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

async def get_analysis_only(update, context):
    """Allows the user to view the full analysis based on ALL history, and includes an external URL button."""

    data = load_data()

    base_url = data['config'].get('analysis_url_base', "https://www.example.com/report")
    username = data['config'].get('username', '')
    password = data['config'].get('password', '')

    # 1. CONSTRUCT THE AUTHENTICATED URL
    if username and password:
        if '://' in base_url:
            protocol, domain_path = base_url.split('://', 1)
            analysis_url = f"{protocol}://{username}:{password}@{domain_path}"
        else:
            analysis_url = f"https://{username}:{password}@{base_url}"
        url_status = f"🔐 Link generated with saved credentials."
    else:
        analysis_url = base_url
        url_status = f"🔗 Link is using the base URL (credentials not set)."

    # 2. Format and display the recorded history (Last 15 Spins)
    history_display_15 = format_last_15_spins(data)

    # 3. Perform all analyses
    predictions = get_predictions_with_reasoning(data)

    # 4. Consolidate message
    if "reasoning" in predictions:
        prediction_message = predictions["reasoning"]
    else:
        prediction_message = (
            f"1. **{predictions['primary']}** *({predictions['primary_reason']})*\n"
            f"2. **{predictions['secondary']}** *({predictions['secondary_reason']})*\n"
            f"3. **{predictions['tertiary']}** *({predictions['tertiary_reason']})*"
        )

    full_analysis_message = (
        f"{history_display_15}\n"
        f"--- **🎯 FULL PREDICTION BREAKDOWN 🎯** ---\n"
        f"{prediction_message}\n\n"
        f"--- **Statistical Breakdown** ---\n"
        f"Total Spins Logged: **{len(data['history'])}**.\n"
        f"Theoretical Chance per Symbol: **12.5%**\n\n"
        f"{analysis_msg_from_counts(data)}\n"
        f"{url_status}"
    )

    # 6. Create the Inline Keyboard button
    keyboard = [[InlineKeyboardButton(BUTTON_TEXT, url=analysis_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        full_analysis_message,
        reply_markup=reply_markup,
        parse_mode=constants.ParseMode.MARKDOWN
    )

# --- Main Bot Execution ---

def main():
    """Starts the bot."""
    # Ensure data file exists before application starts
    if not os.path.exists(DATA_FILE):
        save_data(load_data())

    # Build the Application using the determined token (from ENV or hardcoded)
    application = ApplicationBuilder().token(TOKEN).build()

    # Register all handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("spin", start_roll))
    application.add_handler(CommandHandler("predict", start_roll))
    application.add_handler(CallbackQueryHandler(handle_color_callback))
    application.add_handler(CommandHandler("analyze", get_analysis_only))
    application.add_handler(CommandHandler("setbaseurl", set_analysis_base_url))
    application.add_handler(CommandHandler("setcreds", set_credentials))
    application.add_handler(CommandHandler("reset", reset_history))

    print("Spinner Wheel Tracker Bot is running... Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == '__main__':
    main()
