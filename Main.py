import os, asyncio, edge_tts, subprocess, requests, logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# --- SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot-ka Liibaan waa Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = "8666395712:AAHWOsgjApdKsUNFddeWvbQEx7EyBoy6xI4"
GROQ_API_KEY = "Gsk_mcqTsFbIaNys0SmGQbZJWGdyb3FY3vYKvky7uRu51jv05wPdJzwv"

def translate_to_somali(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=so&dt=t&q={text}"
        r = requests.get(url)
        return "".join([s[0] for s in r.json()[0]])
    except: return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 War dhowow Liibaan! Iisoo dir Video Ingiriis ah, si automatic ah ayaan ugu turjumayaa Soomaali.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    wait = await update.message.reply_text("⏳ AI-ga ayaa dhageysanaya... (Fadlan sug)")
    
    v_in, a_orig, a_som, v_out = f"i_{user_id}.mp4", f"a_{user_id}.mp3", f"s_{user_id}.mp3", f"o_{user_id}.mp4"

    try:
        # Download
        file = await update.message.video.get_file()
        await file.download_to_drive(v_in)

        # Extract Audio (Tayada ayaan xoojiyay si AI-gu u maqlo)
        subprocess.run(['ffmpeg', '-y', '-i', v_in, '-vn', '-acodec', 'libmp3lame', '-ar', '44100', '-ac', '2', a_orig], check=True)

        # Whisper AI (Dhageysi)
        with open(a_orig, "rb") as audio_file:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            files = {"file": audio_file, "model": (None, "whisper-large-v3"), "language": (None, "en")}
            response = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files)
            english_text = response.json().get('text', '')

        if not english_text or len(english_text) < 2:
            await wait.edit_text("⚠️ Video-ga wax hadal ah oo la fahmi karo lagama helin.")
            return

        # Turjumid & Cod
        await wait.edit_text(f"📝 Ingiriis: {english_text[:50]}...\n🔄 Hadda waxaan u beddelayaa Soomaali.")
        somali_text = translate_to_somali(english_text)
        
        communicate = edge_tts.Communicate(somali_text, "so-SO-MuuseNeural")
        await communicate.save(a_som)

        # Mix
        cmd = ['ffmpeg', '-y', '-i', v_in, '-i', a_som, '-filter_complex', '[0:a]volume=0.1[a1];[1:a]volume=1.5[a2];[a1][a2]amix=inputs=2:duration=first', '-c:v', 'copy', '-c:a', 'aac', '-shortest', v_out]
        subprocess.run(cmd, check=True)

        await update.message.reply_video(video=open(v_out, 'rb'), caption=f"✅ Turjumadii: {somali_text[:100]}...\n\nBy: @Liibaantech")
        
    except Exception as e:
        await update.message.reply_text("❌ Cilad farsamo baa dhacday. Fadlan isku day video ka gaaban.")
    finally:
        for f in [v_in, a_orig, a_som, v_out]:
            if os.path.exists(f): os.remove(f)
        await wait.delete()

def main():
    keep_alive()
    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app_bot.run_polling()

if __name__ == "__main__":
    main()
