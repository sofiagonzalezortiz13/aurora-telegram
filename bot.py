from asyncio import to_thread
from html import escape
from io import BytesIO
from pathlib import Path
from time import monotonic
import logging
import os

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters,
)

from app.advice import TOPIC_ICONS, recommendations, reply

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 8 * 1024 * 1024
SESSION_SECONDS = 3600
MAX_SESSIONS = 512
MODES = {"femenino": "Femenino", "masculino": "Masculino", "neutro": "Neutro"}
PRIVATE = filters.ChatType.PRIVATE
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
LOGGER = logging.getLogger("aurora")


def keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(label, callback_data=f"modo:{mode}")
        for mode, label in MODES.items()
    ]])


def report(profile, mode):
    lines = [
        "✨ Tu informe de Aurora",
        "",
        f"🪞 Modo · {MODES[mode]}",
        f"🙂 Rostro · {profile['forma']}",
        f"🧴 Piel · {profile['tono']}, subtono {profile['subtono'].lower()}",
        f"🌈 Estación estimada · {profile['estacion'] or 'Sin estimación'}",
    ]
    for label, sample in profile["colores"].items():
        lines.append(f"🔹 {label} · {sample['hex'] if sample else 'Sin muestra suficiente'}")
    if profile["paleta"]:
        lines.append("🎨 Paleta · " + ", ".join(profile["paleta"]))
    lines.append("")
    lines.extend(f"{TOPIC_ICONS[label]} {label} · {text}" for label, text in recommendations(profile, mode).items())
    lines.extend(("", "La luz y los filtros pueden cambiar los colores observados.",
                  "💬 Pregúntame, por ejemplo, ¿qué corte me recomiendas para una entrevista?"))
    return "\n".join(lines)


async def send_report(message, data):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Preparar prompt", callback_data="gemini_prompt"),
            InlineKeyboardButton("🔗 Abrir Gemini", url="https://gemini.google.com/"),
        ],
        [InlineKeyboardButton("🔄 Terminar y empezar de nuevo", callback_data="reset_session")],
    ])
    text = report(data["profile"], data["mode"])
    text += (
        "\n\n📸 ¿Quieres ver cómo te quedaría? Toca «Preparar prompt» y te escribiré "
        "las instrucciones con tus recomendaciones. Cópialas, abre Gemini, "
        "sube la misma selfie y pega el prompt para que Gemini genere la imagen."
    )
    await message.reply_text(text, reply_markup=buttons)


async def gemini_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    if update.effective_chat is None or update.effective_chat.type != "private":
        return
    message = update.effective_message
    if message is None:
        return

    # The original report can still supply its recommendations after a restart.
    style = ""
    masculine = False
    original = getattr(message, "text", None) or ""
    if query and original.removeprefix("✨ ").startswith("Tu informe de Aurora\n"):
        body, separator, _ = original.partition("\n\nLa luz y los filtros")
        sections = body.split("\n\n", 2)
        if separator and len(sections) == 3:
            style = sections[2]
            masculine = "Modo · Masculino" in sections[1].replace("🪞 ", "").splitlines()
    if not style:
        data = session(context, update.effective_user.id)
        if "profile" not in data:
            await message.reply_text("Envíame una selfie o toca «Preparar prompt» debajo de un informe.")
            return
        style = "\n".join(f"{label} · {value}" for label, value in
                          recommendations(data["profile"], data["mode"]).items())
        masculine = data["mode"] == "masculino"
    prompt = (
        "Edita mi selfie para mostrar cómo me vería con las recomendaciones siguientes. "
        "Conserva mis rasgos, expresión y tono de piel. Elige una variante coherente "
        "cuando haya alternativas y genera una sola imagen realista."
    )
    if masculine:
        prompt += " Aplica las sugerencias de barba y aretes solo si ya los llevo en la foto."
    prompt += "\n\n" + style
    await message.reply_html(
        "📋 Copia el bloque, abre Gemini, sube la selfie del informe y pega el prompt."
        f"\n\n<pre>{escape(prompt)}</pre>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔗 Abrir Gemini", url="https://gemini.google.com/"),
        ]]),
    )


def session(context, user_id):
    sessions = context.bot_data["sessions"]
    now = monotonic()
    for key in [key for key, data in sessions.items() if data["expires"] <= now]:
        del sessions[key]
    if user_id not in sessions:
        if len(sessions) >= MAX_SESSIONS:
            del sessions[next(iter(sessions))]
        sessions[user_id] = {"expires": now + SESSION_SECONDS}
    return sessions[user_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "👋 ¡Hola! Soy Aurora, tu asistente de imagen personal. Elige un modo y envíame "
        "una selfie frontal, sin filtros y con luz uniforme.",
        reply_markup=keyboard(),
    )


async def choose_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_chat is None or update.effective_chat.type != "private":
        return
    mode = query.data.split(":", 1)[1]
    data = session(context, update.effective_user.id)
    data["mode"] = mode
    if "profile" in data:
        await send_report(query.message, data)
    else:
        await query.message.reply_text(f"Modo {mode}. Ahora envíame tu selfie frontal.")


async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    data = session(context, update.effective_user.id)
    mode = data.get("mode")
    if not mode:
        await message.reply_text("Elige el modo y vuelve a enviar tu selfie.", reply_markup=keyboard())
        return
    if message.document:
        source = message.document
        if Path(source.file_name or "").suffix.lower() not in IMAGE_EXTENSIONS:
            await message.reply_text("Envía una foto JPEG, PNG o WebP.")
            return
    else:
        source = message.photo[-1]
    if source.file_size is None or source.file_size > MAX_BYTES:
        await message.reply_text("Envía una imagen de hasta 8 MB.")
        return

    await message.chat.send_action(ChatAction.TYPING)
    try:
        remote = await source.get_file()
        with BytesIO() as buffer:
            await remote.download_to_memory(buffer)
            if buffer.tell() > MAX_BYTES:
                await message.reply_text("La imagen supera los 8 MB.")
                return
            profile = await to_thread(context.bot_data["analyzer"].analyze, buffer.getvalue())
    except ValueError as error:
        await message.reply_text(str(error))
        return
    except TelegramError:
        await message.reply_text("No pude descargar la foto. Intenta enviarla otra vez.")
        return
    data.update(profile=profile, topics=[], expires=monotonic() + SESSION_SECONDS)
    await send_report(message, data)


async def question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    data = session(context, update.effective_user.id)
    if "profile" not in data:
        if "mode" in data:
            await message.reply_text("Envíame una selfie frontal para preparar tu informe.")
        else:
            await start(update, context)
        return
    answer, topics = reply(data["profile"], data["mode"], message.text[:500], data["topics"])
    data["topics"] = topics
    await message.reply_text(answer)


async def show_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = session(context, update.effective_user.id)
    if "profile" in data:
        await send_report(update.effective_message, data)
    else:
        await start(update, context)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.effective_chat is None or update.effective_chat.type != "private":
            return
    context.bot_data["sessions"].pop(update.effective_user.id, None)
    await update.effective_message.reply_text(
        "🔄 Cerré la conversación y borré tu informe de mi memoria. "
        "Elige un modo para empezar de nuevo.",
        reply_markup=keyboard(),
    )


async def setup(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Empezar con Aurora"),
        BotCommand("modo", "Elegir modo de estilo"),
        BotCommand("informe", "Mostrar mi informe"),
        BotCommand("prompt", "Preparar mi prompt para Gemini"),
        BotCommand("borrar", "Borrar mi sesión"),
    ])


async def log_error(update, context):
    LOGGER.error("Error al atender Telegram (%s).", type(context.error).__name__)


def build_application(token, analyzer):
    application = Application.builder().token(token).post_init(setup).build()
    application.bot_data.update(analyzer=analyzer, sessions={})
    application.add_handler(CommandHandler("start", start, filters=PRIVATE))
    application.add_handler(CommandHandler("modo", start, filters=PRIVATE))
    application.add_handler(CommandHandler("informe", show_report, filters=PRIVATE))
    application.add_handler(CommandHandler("prompt", gemini_prompt, filters=PRIVATE))
    application.add_handler(CommandHandler("borrar", reset, filters=PRIVATE))
    application.add_handler(CallbackQueryHandler(choose_mode, pattern=r"^modo:(femenino|masculino|neutro)$"))
    application.add_handler(CallbackQueryHandler(gemini_prompt, pattern=r"^gemini_prompt$"))
    application.add_handler(CallbackQueryHandler(reset, pattern=r"^reset_session$"))
    application.add_handler(MessageHandler(PRIVATE & (filters.PHOTO | filters.Document.ALL), analyze_photo))
    application.add_handler(MessageHandler(PRIVATE & filters.TEXT & ~filters.COMMAND, question))
    application.add_error_handler(log_error)
    return application


def main():
    load_dotenv(ROOT / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "REEMPLAZA_CON_TU_TOKEN":
        raise SystemExit("Configura TELEGRAM_BOT_TOKEN en .env. Consulta README.md.")
    from app.vision import Analyzer

    logging.basicConfig(level=logging.WARNING)
    analyzer = Analyzer()
    try:
        application = build_application(token, analyzer)
        print("Aurora está iniciando. Abre tu bot en Telegram y envía /start.")
        application.run_polling(allowed_updates=["message", "callback_query"])
    finally:
        analyzer.face.close()
        analyzer.segmenter.close()


if __name__ == "__main__":
    main()
