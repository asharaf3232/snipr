# -*- coding: utf-8 -*-
# =======================================================================================
# --- ❤️‍🩹 ملف المنطق الأساسي (core_logic.py) | بوت كاسحة الألغام v6.6 ❤️‍🩹 ---
# =======================================================================================

import asyncio
import logging
import json
import time
import pandas as pd
import pandas_ta as ta
import httpx
import feedparser
import ccxt
from datetime import datetime
from collections import defaultdict

# --- استيراد الوحدات المخصصة ---
from config import *
from database import (log_trade_to_db, get_active_trades_from_db, close_trade_in_db as db_close_trade,
                      update_trade_sl_in_db, update_trade_peak_price_in_db, save_settings)
from exchanges import bot_state, scan_lock, get_exchange_adapter, get_real_balance
from strategies import SCANNERS, find_col

# استيراد مشروط لمكتبات التحليل
try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# استيراد دوال إرسال الرسائل (سيتم تمرير bot object إليها)
# سيتم تعريف هذه الدالة في telegram_bot.py
from telegram_bot import send_telegram_message

logger = logging.getLogger("MinesweeperBot_v6")

# =======================================================================================
# --- Market Analysis & Sentiment Functions ---
# =======================================================================================

async def get_alpha_vantage_economic_events():
    if ALPHA_VANTAGE_API_KEY == 'YOUR_AV_KEY_HERE': return []
    # ... (Rest of the function code as it was in the original file)
    # This is a placeholder to keep the example brief
    return []

def get_latest_crypto_news(limit=15):
    # ... (Rest of the function code as it was in the original file)
    return []

def analyze_sentiment_of_headlines(headlines):
    if not headlines or not NLTK_AVAILABLE: return 0.0
    sia = SentimentIntensityAnalyzer()
    total_compound_score = sum(sia.polarity_scores(headline)['compound'] for headline in headlines)
    return total_compound_score / len(headlines) if headlines else 0.0

async def get_fundamental_market_mood():
    # ... (Rest of the function code as it was in the original file)
    return "NEUTRAL", 0.0, "تحليل الأخبار معطل مؤقتاً."

async def get_fear_and_greed_index():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.alternative.me/fng/?limit=1", timeout=10)
            response.raise_for_status()
            data = response.json().get('data', [])
            if data:
                return int(data[0]['value'])
    except Exception as e:
        logger.error(f"Could not fetch Fear and Greed Index: {e}")
    return None

async def check_market_regime():
    settings = bot_state.settings
    # ... (Rest of the function code as it was in the refactored v6.5)
    return True, "وضع السوق مناسب."

# =======================================================================================
# --- Core Bot Logic: Scanning, Trading, Tracking ---
# =======================================================================================

async def aggregate_top_movers():
    # ... (All the logic from the original file's aggregate_top_movers)
    logger.info("Aggregating top movers...")
    return [] # Placeholder

async def get_higher_timeframe_trend(exchange, symbol, ma_period):
    # ... (All the logic from the original file's get_higher_timeframe_trend)
    return True, "Bullish" # Placeholder

async def worker(queue, results_list, settings, failure_counter):
    while not queue.empty():
        market_info = await queue.get()
        # ... (All the logic from the original file's worker)
        queue.task_done()

async def place_real_trade(signal):
    # ... (All the logic from the original file's place_real_trade)
    return {'success': False, 'data': "التداول الحقيقي معطل مؤقتاً."} # Placeholder

async def perform_scan(context):
    # ... (All the logic from the original file's perform_scan, but calling our new process_trade_closure)
    logger.info("Performing scan...")
    # Make sure to call save_settings() at the end after updating last_signal_time

async def track_open_trades(context):
    # ... (All the logic from the v6.5 refactored track_open_trades, with batch fetching)
    logger.info("Tracking open trades...")
    
async def check_single_trade(trade, context, prefetched_data):
    # ... (All the logic from the v6.5 refactored check_single_trade)
    # This function will now call `process_trade_closure` instead of `close_trade_in_db` directly
    pass # Placeholder

async def handle_tsl_update(context, trade, new_sl, highest_price, is_activation=False):
    # ... (All the logic from the original file's handle_tsl_update)
    pass # Placeholder

async def update_real_trade_sl(context, trade, new_sl, highest_price, is_activation=False):
    # ... (All the logic from the original file's update_real_trade_sl)
    pass # Placeholder

async def process_trade_closure(context, trade, exit_price, is_win):
    """New refactored function to handle all logic for closing a trade."""
    pnl_usdt = (exit_price - trade['entry_price']) * trade['quantity']
    
    status = ""
    if is_win:
        status = 'ناجحة (تحقيق هدف)'
    else:
        if pnl_usdt > 0:
            status = 'ناجحة (وقف ربح)'
        else:
            status = 'فاشلة (وقف خسارة)'

    # Step 1: Update DB
    db_close_trade(trade['id'], status, exit_price, pnl_usdt)

    # Step 2: Update virtual portfolio
    if trade.get('trade_mode') == 'virtual':
        bot_state.settings['virtual_portfolio_balance_usdt'] += pnl_usdt
        save_settings()

    # Step 3: Send Notification
    start_dt_naive = datetime.strptime(trade['timestamp'], '%Y-%m-%d %H:%M:%S')
    duration = datetime.now(EGYPT_TZ) - start_dt_naive.replace(tzinfo=EGYPT_TZ)
    days, remainder = divmod(duration.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    duration_str = f"{int(days)}d {int(hours)}h {int(minutes)}m" if days > 0 else f"{int(hours)}h {int(minutes)}m"
    
    trade_type_str = "(صفقة حقيقية)" if trade.get('trade_mode') == 'real' else ""
    pnl_percent = (pnl_usdt / trade['entry_value_usdt'] * 100) if trade.get('entry_value_usdt', 0) > 0 else 0
    
    message = ""
    if pnl_usdt >= 0:
        message = (f"**📦 إغلاق صفقة {trade_type_str} | #{trade['id']} {trade['symbol']}**\n\n"
                   f"**الحالة: ✅ {status}**\n"
                   f"💰 **الربح:** `${pnl_usdt:+.2f}` (`{pnl_percent:+.2f}%`)\n\n"
                   f"- **مدة الصفقة:** {duration_str}")
    else: 
        message = (f"**📦 إغلاق صفقة {trade_type_str} | #{trade['id']} {trade['symbol']}**\n\n"
                   f"**الحالة: ❌ {status}**\n"
                   f"💰 **الخسارة:** `${pnl_usdt:.2f}` (`{pnl_percent:.2f}%`)\n\n"
                   f"- **مدة الصفقة:** {duration_str}")

    await send_telegram_message(context.bot, {'custom_message': message, 'target_chat': TELEGRAM_SIGNAL_CHANNEL_ID})

# ... (And so on for all the other core logic functions)
