import json
import logging
import os
from typing import Set

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ChatMemberHandler,
)

# =========================
# إعدادات البوت (من Railway Variables)
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

CHATS_FILE = "chats.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# =========================
# إدارة ملف التخزين
# =========================

def load_chats() -> Set[int]:
    if not os.path.exists(CHATS_FILE):
        return set()
    try:
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("فشل تحميل chats.json: %s", e)
        return set()


def save_chats(chats: Set[int]) -> None:
    try:
        with open(CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(chats), f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error("فشل حفظ chats.json: %s", e)


CHATS_MEMORY: Set[int] = load_chats()


# =========================
# التحقق من المالك
# =========================

def is_admin(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id == ADMIN_ID


# =========================
# تسجيل الأماكن تلقائياً
# =========================

async def track_chats(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    result = update.my_chat_member
    if not result:
        return

    chat = result.chat
    new_status = result.new_chat_member.status
    chat_id = chat.id
    chat_title = chat.title or "بدون اسم"

    if new_status in ("administrator", "creator"):
        if chat_id not in CHATS_MEMORY:
            CHATS_MEMORY.add(chat_id)
            save_chats(CHATS_MEMORY)
            logger.info("➕ إضافة: %s | ID: %s", chat_title, chat_id)

    elif new_status in ("left", "kicked"):
        if chat_id in CHATS_MEMORY:
            CHATS_MEMORY.remove(chat_id)
            save_chats(CHATS_MEMORY)
            logger.info("➖ إزالة: %s | ID: %s", chat_title, chat_id)


# =========================
# أمر إضافة مكان يدوياً
# =========================

async def addchat(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ الاستخدام:\n/addchat -1001234567890"
        )
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال ID رقمي.")
        return

    if chat_id in CHATS_MEMORY:
        await update.message.reply_text("ℹ️ هذا المكان مسجل مسبقاً.")
        return

    CHATS_MEMORY.add(chat_id)
    save_chats(CHATS_MEMORY)
    await update.message.reply_text(
        f"✅ تمت إضافة: `{chat_id}`", parse_mode="Markdown"
    )


# =========================
# أمر GBAN
# =========================

async def gban(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ الاستخدام:\n/gban 123456789\n"
            "أو عدة مستخدمين:\n/gban 111 222 333"
        )
        return

    targets = []
    for arg in context.args:
        try:
            targets.append(int(arg))
        except ValueError:
            await update.message.reply_text(
                f"❌ `{arg}` ليس ID رقمياً صحيحاً.",
                parse_mode="Markdown",
            )
            return

    if not CHATS_MEMORY:
        await update.message.reply_text(
            "⚠️ لا توجد أماكن مسجلة.\n"
            "أضف البوت كمشرف أولاً أو استخدم /addchat."
        )
        return

    status_message = await update.message.reply_text(
        f"⏳ جاري تنفيذ الحظر العام...\n"
        f"👥 المستخدمون: {len(targets)}\n"
        f"📊 الأماكن: {len(CHATS_MEMORY)}"
    )

    total_success = 0
    total_failed = 0
    details = []

    for user_id in targets:
        success = 0
        failed = 0
        for chat_id in list(CHATS_MEMORY):
            try:
                await context.bot.ban_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    revoke_messages=True,
                )
                success += 1
            except Exception as error:
                failed += 1
                error_text = str(error)

                if "not enough rights" in error_text:
                    reason = "صلاحيات غير كافية (مشرف؟)"
                elif "user is an administrator" in error_text:
                    reason = "المستخدم مشرف"
                elif "chat not found" in error_text:
                    reason = "البوت مو موجود"
                elif "bot was kicked" in error_text:
                    reason = "البوت انطرد"
                else:
                    reason = error_text[:80]

                logger.warning(
                    "فشل حظر %s في %s: %s", user_id, chat_id, reason
                )

        total_success += success
        total_failed += failed
        details.append(
            f"👤 `{user_id}` → 🟢 {success} | 🔴 {failed}"
        )

    result_text = (
        "🚫 **تم الانتهاء من الحظر العام**\n\n"
        + "\n".join(details)
        + f"\n\n📊 الإجمالي: 🟢 {total_success} | 🔴 {total_failed}"
    )

    await status_message.edit_text(result_text, parse_mode="Markdown")


# =========================
# أمر UNGBAN (فك الحظر)
# =========================

async def ungban(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text("⚠️ الاستخدام:\n/ungban 123456789")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال ID رقمي.")
        return

    if not CHATS_MEMORY:
        await update.message.reply_text("📭 لا توجد أماكن مسجلة.")
        return

    status_message = await update.message.reply_text(
        f"⏳ جاري فك الحظر...\n👤 `{user_id}`",
        parse_mode="Markdown",
    )

    success = failed = 0
    for chat_id in list(CHATS_MEMORY):
        try:
            await context.bot.unban_chat_member(
                chat_id=chat_id, user_id=user_id
            )
            success += 1
        except Exception as e:
            failed += 1
            logger.warning("فشل فك حظر %s في %s: %s", user_id, chat_id, e)

    await status_message.edit_text(
        f"✅ **تم فك الحظر**\n"
        f"👤 `{user_id}`\n"
        f"🟢 نجح: {success} | 🔴 فشل: {failed}",
        parse_mode="Markdown",
    )


# =========================
# أمر الإحصائيات
# =========================

async def chats(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return

    if not CHATS_MEMORY:
        await update.message.reply_text("📭 لا توجد أماكن مسجلة.")
        return

    text = f"📊 **إحصائيات البوت**\n\n"
    text += f"📌 الأماكن المسجلة: **{len(CHATS_MEMORY)}**\n\n"

    text += "**القائمة:**\n"
    for i, chat_id in enumerate(sorted(CHATS_MEMORY)[:30], 1):
        text += f"{i}. `{chat_id}`\n"

    if len(CHATS_MEMORY) > 30:
        text += f"\n... و {len(CHATS_MEMORY) - 30} مكان آخر"

    await update.message.reply_text(text, parse_mode="Markdown")


# =========================
# أمر حذف مكان
# =========================

async def removechat(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text("⚠️ الاستخدام:\n/removechat -1001234567890")
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال ID رقمي.")
        return

    if chat_id not in CHATS_MEMORY:
        await update.message.reply_text("ℹ️ هذا المكان غير مسجل.")
        return

    CHATS_MEMORY.remove(chat_id)
    save_chats(CHATS_MEMORY)
    await update.message.reply_text(
        f"✅ تمت إزالة: `{chat_id}`", parse_mode="Markdown"
    )


# =========================
# أمر البداية
# =========================

async def start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        await update.message.reply_text(
            "🚫 هذا البوت خاص.\n"
            "غير مصرح لك باستخدامه."
        )
        return

    await update.message.reply_text(
        "🤖 **بوت الحظر العام**\n\n"
        "**الأوامر المتاحة:**\n\n"
        "`/gban <ID>` — حظر مستخدم من كل الأماكن\n"
        "`/gban ID1 ID2 ID3` — حظر عدة مستخدمين\n"
        "`/ungban <ID>` — فك الحظر العام\n"
        "`/chats` — عرض الأماكن المسجلة\n"
        "`/addchat <ID>` — إضافة مكان يدوياً\n"
        "`/removechat <ID>` — حذف مكان من القائمة\n"
        "`/start` — عرض هذه القائمة",
        parse_mode="Markdown",
    )


# =========================
# تشغيل البوت
# =========================

def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN غير موجود في المتغيرات")

    if ADMIN_ID == 0:
        raise SystemExit("❌ ADMIN_ID غير موجود في المتغيرات")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gban", gban))
    app.add_handler(CommandHandler("ungban", ungban))
    app.add_handler(CommandHandler("chats", chats))
    app.add_handler(CommandHandler("addchat", addchat))
    app.add_handler(CommandHandler("removechat", removechat))

    logger.info("🤖 البوت يعمل الآن...")
    logger.info("📊 الأماكن المسجلة: %d", len(CHATS_MEMORY))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
