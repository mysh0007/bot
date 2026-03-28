import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_KEY")

# System prompt — شخصية البوت
SYSTEM_PROMPT = """أنت مساعد ذكي لقناة تيليغرام متخصصة في التقنية والذكاء الاصطناعي.
مهمتك:
- الرد على أسئلة المشتركين بشكل واضح ومفيد
- اللغة العربية الفصحى المبسطة
- الردود موجزة (لا تتجاوز 200 كلمة إلا عند الحاجة)
- أسلوبك ودود ومتحمس للتقنية
- إذا سُئلت عن شيء خارج نطاق التقنية، وجّه المستخدم بلطف"""

# ─── SETUP ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# تخزين سياق المحادثة لكل مستخدم (آخر 10 رسائل)
conversation_history: dict[int, list] = {}

# ─── HANDLERS ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً! أنا مساعد قناة التقنية والذكاء الاصطناعي.\n\n"
        "اسألني عن:\n"
        "• 🤖 أخبار الذكاء الاصطناعي\n"
        "• 🛠️ الأدوات التقنية\n"
        "• 💡 شرح المفاهيم التقنية\n\n"
        "ابدأ بكتابة سؤالك! ⚡"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *الأوامر المتاحة:*\n\n"
        "/start — بداية المحادثة\n"
        "/help — قائمة الأوامر\n"
        "/post — توليد منشور جديد للقناة\n"
        "/ideas — أفكار محتوى\n"
        "/clear — مسح سياق المحادثة",
        parse_mode="Markdown"
    )

async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يولّد منشور جاهز للقناة"""
    topic = " ".join(context.args) if context.args else "آخر أخبار الذكاء الاصطناعي"
    await update.message.reply_text("⏳ جاري توليد المنشور...")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "أنت كاتب محتوى متخصص في التقنية لقناة تيليغرام عربية."},
                {"role": "user", "content": f"اكتب منشور تيليغرام احترافي عن: {topic}\n"
                 "الأسلوب: مثير وجذاب، استخدم إيموجي، أضف هاشتاقات عربية في النهاية، "
                 "الطول: 150-200 كلمة."}
            ],
            max_tokens=500
        )
        await update.message.reply_text(
            f"✅ *منشور جاهز للنشر:*\n\n{response.choices[0].message.content}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

async def ideas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يولّد أفكار محتوى"""
    await update.message.reply_text("💡 جاري توليد الأفكار...")
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content":
                "اقترح 8 أفكار منشورات متنوعة لقناة تيليغرام عربية عن التقنية والذكاء الاصطناعي. "
                "كل فكرة في سطر مع رقم ونوع المنشور بين قوسين مربعين."}],
            max_tokens=400
        )
        await update.message.reply_text(
            f"💡 *أفكار محتوى:*\n\n{response.choices[0].message.content}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_history.pop(user_id, None)
    await update.message.reply_text("🗑️ تم مسح سياق المحادثة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # تهيئة سجل المحادثة
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # إضافة رسالة المستخدم
    conversation_history[user_id].append({"role": "user", "content": user_text})

    # الاحتفاظ بآخر 10 رسائل فقط
    if len(conversation_history[user_id]) > 10:
        conversation_history[user_id] = conversation_history[user_id][-10:]

    # إرسال "يكتب..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history[user_id]

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=600
        )

        reply = response.choices[0].message.content
        conversation_history[user_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await update.message.reply_text("❌ حدث خطأ في الاتصال. حاول مرة أخرى.")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("post", post_cmd))
    app.add_handler(CommandHandler("ideas", ideas_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 البوت يعمل...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
