import os, asyncio, edge_tts, subprocess, requests, logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CommandHandler

# --- HEALTH CHECK ---
app = Flask('')
@app.route('/')
def home(): return "Bot-ka Liibaan waa Live!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = "8666395712:AAHWOsgjApdKsUNFddeWvbQEx7EyBoy6xI4"
GROQ_API_KEY = "Gsk_mcqTsFbIaNys0SmGQbZJWGdyb3FY3vYKvky7uRu51jv05wPdJzwv"

logging.basicConfig(level=logging.INFO)

# Qalabka turjumada (Google Translate Free)
def translate_to_somali(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=so&dt=t&q={text}"
        r = requests.get(url)
        return "".join([s[0] for s in r.json()[0]])
    except:
        return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("👩‍💼 Ubax (Dheddig)", callback_data='v_so-SO-UbaxNeural'), 
                 InlineKeyboardButton("👨‍💼 Muuse (Lab)", callback_data='v_so-SO-MuuseNeural')]]
    await update.message.reply_text("👋 War dhowow! Dooro codka Soomaaliga ah:", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['voice'] = query.data.replace('v_', '')
    await query.edit_message_text("✅ Diyaar! Hadda ii soo dir Video-ga (English). Si automatic ah ayaan u turjumayaa.")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    voice = context.user_data.get('voice', 'so-SO-MuuseNeural')
    wait = await update.message.reply_text("🎧 AI-ga ayaa dhageysanaya hadalka video-ga...")
    
    v_in, a_orig, a_som, v_out = f"i_{user_id}.mp4", f"a_{user_id}.mp3", f"s_{user_id}.mp3", f"o_{user_id}.mp4"

    try:
        # 1. Download Video
        file = await update.message.video.get_file()
        await file.download_to_drive(v_in)

        # 2. Extract Audio
        subprocess.run(['ffmpeg', '-y', '-i', v_in, '-ar', '16000', '-ac', '1', '-map', 'a', a_orig], check=True)

        # 3. Whisper AI (Dhageysi)
        with open(a_orig, "rb") as audio_file:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            files = {"file": audio_file, "model": (None, "whisper-large-v3"), "language": (None, "en")}
            response = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files)
            english_text = response.json().get('text', '')

        if not english_text:
            await update.message.reply_text("⚠️ Wax hadal ah kama maqal video-ga.")
            return

        # 4. Turjumid (English to Somali)
        somali_text = translate_to_somali(english_text)

        # 5. Samee Codka Soomaaliga ah
        communicate = edge_tts.Communicate(somali_text, voice)
        await communicate.save(a_som)

        # 6. FFmpeg: Isku dar Video + Codka Cusub
        cmd = [
            'ffmpeg', '-y', '-i', v_in, '-i', a_som,
            '-map', '0:v:0', '-map', '1:a:0', 
            '-c:v', 'copy', '-c:a', 'aac', '-shortest', v_out
        ]
        subprocess.run(cmd, check=True)

        await update.message.reply_video(video=open(v_out, 'rb'), caption=f"✅ Turjumadii: {somali_text[:100]}...\n\nBy: @Liibaantech")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Cilad: Video-ga ayaa aad u weyn ama koodhka ayaa istaagay.")
    finally:
        for f in [v_in, a_orig, a_som, v_out]:
            if os.path.exists(f): os.remove(f)
        await wait.delete()

def main():
    keep_alive()
    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(set_voice))
    app_bot.add_handler(MessageHandler(filters.VIDEO, process_video))
    app_bot.run_polling()

if __name__ == "__main__":
    main()


