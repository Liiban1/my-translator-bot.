import os
import asyncio
import edge_tts
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CommandHandler
import subprocess

# --- HEALTH CHECK ---
app = Flask('')
@app.route('/')
def home(): return "Bot-ka Liibaan waa Live!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = "8666395712:AAHWOsgjApdKsUNFddeWvbQEx7EyBoy6xI4"
ADMIN_USERNAME = "@Liibaantech"

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("✍️ Qoraal Cod u beddel", callback_data='mode_tts')],
                [InlineKeyboardButton("🎥 Muuqaal ii turjum", callback_data='mode_translate')]]
    await update.message.reply_text(f"👋 War dhowow!\nDooro mid:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith('mode_'):
        context.user_data['mode'] = query.data.replace('mode_', '')
        keyboard = [[InlineKeyboardButton("👩‍💼 Ubax", callback_data='v_so-SO-UbaxNeural'), 
                     InlineKeyboardButton("👨‍💼 Muuse", callback_data='v_so-SO-MuuseNeural')]]
        await query.edit_message_text("Dooro Codka:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('v_'):
        context.user_data['voice'] = query.data.replace('v_', '')
        mode = context.user_data.get('mode', 'tts')
        msg = "✍️ Soo dir qoraal:" if mode == 'tts' else "🎥 Soo dir Video gaaban:"
        await query.edit_message_text(f"✅ Diyaar. {msg}")

async def process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mode = context.user_data.get('mode')
    voice = context.user_data.get('voice', 'so-SO-MuuseNeural')
    
    if mode == 'translate' and update.message.video:
        wait = await update.message.reply_text("⏳ Farsamaynta waa la bilaabay...")
        v_in, a_som, v_out = f"i_{user_id}.mp4", f"a_{user_id}.mp3", f"o_{user_id}.mp4"
        try:
            file = await update.message.video.get_file()
            await file.download_to_drive(v_in)
            communicate = edge_tts.Communicate("Muuqaal turjuman ooy diyaarisay Liibaan Tech.", voice)
            await communicate.save(a_som)
            cmd = ['ffmpeg', '-y', '-i', v_in, '-i', a_som, '-filter_complex', '[0:a]volume=0.2[a1];[1:a]volume=1.0[a2];[a1][a2]amix=inputs=2:duration=first[aout]', '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-shortest', v_out]
            subprocess.run(cmd, check=True)
            await update.message.reply_video(video=open(v_out, 'rb'), caption=f"✅ Diyaar waaye!\nBy: {ADMIN_USERNAME}")
        except Exception:
            await update.message.reply_text("❌ Cilad baa dhacday. Video-gu waa inuu aad u yar yahay.")
        finally:
            for f in [v_in, a_som, v_out]:
                if os.path.exists(f): os.remove(f)
            await wait.delete()
    elif mode == 'tts' and update.message.text:
        path = f"t_{user_id}.mp3"
        await edge_tts.Communicate(update.message.text, voice).save(path)
        await update.message.reply_voice(voice=open(path, 'rb'))
        if os.path.exists(path): os.remove(path)

def main():
    keep_alive()
    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(handle_interaction))
    app_bot.add_handler(MessageHandler(filters.TEXT | filters.VIDEO, process))
    app_bot.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

