import os
import asyncio
import edge_tts
import json
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CommandHandler
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

# --- HEALTH CHECK (Si uusan Koyeb u damin) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot-ka Liibaan Abdi waa Live!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIG ---
# TOKEN-kaaga rasmiga ah
TOKEN = "8666395712:AAHWOsgjApdKsUNFddeWvbQEx7EyBoy6xI4"
ADMIN_USERNAME = "@Liibaantech"

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✍️ Qoraal Cod u beddel", callback_data='mode_tts')],
        [InlineKeyboardButton("🎥 Muuqaal ii turjum (Fast Mode)", callback_data='mode_translate')]
    ]
    await update.message.reply_text(
        f"👋 War dhowow {update.effective_user.first_name}!\n\n"
        f"Kani waa Bot-ka turjumista ee Liibaan Abdi.\n"
        f"Dooro waxaad rabto:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('mode_'):
        context.user_data['mode'] = query.data.replace('mode_', '')
        keyboard = [
            [InlineKeyboardButton("👩‍💼 Ubax (Dumar)", callback_data='v_so-SO-UbaxNeural'), 
             InlineKeyboardButton("👨‍💼 Muuse (Rag)", callback_data='v_so-SO-MuuseNeural')]
        ]
        await query.edit_message_text("Dooro Codka aad rabto:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif query.data.startswith('v_'):
        context.user_data['voice'] = query.data.replace('v_', '')
        mode = context.user_data.get('mode', 'tts')
        msg = "✍️ Soo dir qoraalka aad rabto inaan kuu akhriyo:" if mode == 'tts' else "🎥 Soo dir Video-ga (Ilaa 3 daqiiqo):"
        await query.edit_message_text(f"✅ Codka waa la xushay. {msg}")

async def process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mode = context.user_data.get('mode')
    voice = context.user_data.get('voice', 'so-SO-MuuseNeural')
    
    if not mode:
        return await update.message.reply_text("Fadlan marka hore isticmaal /start")

    # --- VIDEO TRANSLATION MODE ---
    if mode == 'translate' and update.message.video:
        wait = await update.message.reply_text("🚀 Farsamaynta waa la bilaabay... Sug ilaa 60s.")
        v_in, a_in, v_out = f"i_{user_id}.mp4", f"a_{user_id}.mp3", f"o_{user_id}.mp4"
        
        try:
            file = await update.message.video.get_file()
            await file.download_to_drive(v_in)
            
            with VideoFileClip(v_in) as clip:
                # Samee Codka Soomaaliga ah
                communicate = edge_tts.Communicate("Muuqaal turjuman oo uu diyaariyay Liibaan Abdi.", voice)
                await communicate.save(a_in)
                
                audio_somali = AudioFileClip(a_in)
                orig_audio = clip.audio.multiply_volume(0.2) # Codka asalka ah hoos u dhig
                final_audio = CompositeAudioClip([orig_audio, audio_somali.set_start(0.5)])
                
                # Fast Processing (Optimized for Koyeb)
                final_clip = clip.without_audio().set_audio(final_audio)
                final_clip.write_videofile(v_out, codec="libx264", audio_codec="aac", fps=20, preset="ultrafast", logger=None)
                audio_somali.close()

            await update.message.reply_video(video=open(v_out, 'rb'), caption=f"✅ Lagu guuleystay!\nBy: {ADMIN_USERNAME}")
        except Exception as e:
            logging.error(f"Error: {e}")
            await update.message.reply_text("Khalad baa dhacay. Isku day video ka yar 25MB.")
        finally:
            for f in [v_in, a_in, v_out]:
                if os.path.exists(f): os.remove(f)
            await wait.delete()

    # --- TEXT TO SPEECH MODE ---
    elif mode == 'tts' and update.message.text:
        path = f"t_{user_id}.mp3"
        communicate = edge_tts.Communicate(update.message.text, voice)
        await communicate.save(path)
        await update.message.reply_voice(voice=open(path, 'rb'), caption=f"By: {ADMIN_USERNAME}")
        if os.path.exists(path): os.remove(path)

def main():
    # Kici Flask Port 8080
    keep_alive()
    
    # Kici Telegram Bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_interaction))
    app.add_handler(MessageHandler(filters.TEXT | filters.VIDEO, process))
    
    print("Bot-ka Liibaan Abdi waa Online!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
