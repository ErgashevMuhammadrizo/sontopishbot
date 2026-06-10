import asyncio
import logging
import os
import random

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

router = Router()


# ══════════════════════════════════════════════════════════════
#  FSM STATES
# ══════════════════════════════════════════════════════════════

class AdminStates(StatesGroup):
    broadcast    = State()
    search       = State()
    bonus        = State()
    bonus_inline = State()

class GameState(StatesGroup):
    playing = State()

class BattleState(StatesGroup):
    playing = State()


# ══════════════════════════════════════════════════════════════
#  YORDAMCHI FUNKSIYALAR
# ══════════════════════════════════════════════════════════════

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def user_display(u: dict) -> str:
    if u.get("username"):
        return f"@{u['username']}"
    name = u.get("first_name", "")
    if u.get("last_name"):
        name += f" {u['last_name']}"
    return name or str(u["user_id"])

def hint_text(hint: str) -> str:
    if hint == "higher":
        return "⬆️ <b>Tepparoq!</b>"
    if hint == "lower":
        return "⬇️ <b>Pastroq!</b>"
    return "✅ <b>To'g'ri!</b>"


# ══════════════════════════════════════════════════════════════
#  KLAVIATURALAR
# ══════════════════════════════════════════════════════════════

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 O'yin boshlash"),    KeyboardButton(text="⚔️ 1vs1 Battle")],
            [KeyboardButton(text="📊 Mening statistikam"), KeyboardButton(text="🏆 Reyting")],
            [KeyboardButton(text="ℹ️ Qoidalar")],
        ],
        resize_keyboard=True,
    )

def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Foydalanuvchilar"),  KeyboardButton(text="📈 Statistika")],
            [KeyboardButton(text="📅 Kunlik hisobot"),    KeyboardButton(text="🚫 Bloklangan")],
            [KeyboardButton(text="📢 Xabar yuborish"),    KeyboardButton(text="🔍 Qidirish")],
            [KeyboardButton(text="🎁 Bonus berish"),       KeyboardButton(text="🗑 Ma'lumot tozalash")],
            [KeyboardButton(text="⬅️ Asosiy menyu")],
        ],
        resize_keyboard=True,
    )

def confirm_clear_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data="confirm_clear"),
        InlineKeyboardButton(text="❌ Bekor qilish",  callback_data="cancel_clear"),
    ]])

def user_action_inline(user_id: int, is_banned_user: bool) -> InlineKeyboardMarkup:
    ban_text = "✅ Blokdan chiqarish" if is_banned_user else "🚫 Bloklash"
    ban_data = f"unban_{user_id}"     if is_banned_user else f"ban_{user_id}"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=ban_text,          callback_data=ban_data),
        InlineKeyboardButton(text="🎁 Bonus berish", callback_data=f"bonus_{user_id}"),
    ]])

def battle_join_inline(battle_id: str, challenger_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"⚔️ {challenger_name} bilan kurashish!",
            callback_data=f"join_battle_{battle_id}"
        ),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"decline_battle_{battle_id}"),
    ]])


# ══════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    u      = message.from_user
    is_new = db.upsert_user(u.id, u.first_name, u.last_name, u.username)
    await state.clear()
    db.clear_game(u.id)

    if is_new and u.id != ADMIN_ID:
        try:
            uname = f"@{u.username}" if u.username else "—"
            await bot.send_message(
                ADMIN_ID,
                f"🔔 <b>Yangi foydalanuvchi!</b>\n\n"
                f"👤 Ism: <b>{u.first_name}</b>\n"
                f"🔗 Username: {uname}\n"
                f"🆔 ID: <code>{u.id}</code>",
            )
        except Exception:
            pass

    if db.is_banned(u.id):
        await message.answer("🚫 Siz botdan bloklangansiz. Admin bilan bog'laning.")
        return

    await message.answer(
        "🎯 <b>Son Topish O'yiniga Xush Kelibsiz!</b>\n\n"
        "Men 1 dan 100 gacha son o'ylayman.\n"
        "Sizda uni topish uchun <b>5 ta imkoniyat</b> bor.\n\n"
        "Har taxminingizdan keyin yo'nalish beraman:\n"
        "⬆️ <b>Tepparoq</b> — kiritgan son kichik bo'lsa\n"
        "⬇️ <b>Pastroq</b> — kiritgan son katta bo'lsa\n\n"
        "⚔️ <b>1vs1 Battle:</b> Ikkala o'yinchi bir xil yashirin sonni topadi.\n"
        "Navbat bilan o'ynaladi. Birinchi topgan — G'OLIB!\n\n"
        "Quyidagi tugmalardan foydalaning 👇",
        reply_markup=main_keyboard(),
    )


# ══════════════════════════════════════════════════════════════
#  /admin
# ══════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        return
    await state.clear()
    await message.answer(
        "🔐 <b>Admin Paneli</b>\n\nFunksiyani tanlang:",
        reply_markup=admin_keyboard(),
    )


# ══════════════════════════════════════════════════════════════
#  /cancel
# ══════════════════════════════════════════════════════════════

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    uid = message.from_user.id
    await state.clear()
    db.clear_game(uid)
    bid, _ = db.get_battle_by_user(uid)
    if bid:
        db.delete_battle(bid)
    kb = admin_keyboard() if is_admin(uid) else main_keyboard()
    await message.answer("❌ Bekor qilindi.", reply_markup=kb)


# ══════════════════════════════════════════════════════════════
#  /ban  /unban
# ══════════════════════════════════════════════════════════════

@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()[1:]
    if not args:
        await message.answer("⚠️ Foydalanish: /ban &lt;user_id yoki @username&gt;")
        return
    user = db.find_user(args[0])
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return
    db.ban_user(user["user_id"])
    db.clear_game(user["user_id"])
    try:
        await bot.send_message(user["user_id"], "🚫 Siz administrator tomonidan bloklangansiz.")
    except Exception:
        pass
    await message.answer(
        f"🚫 <b>{user_display(user)}</b> bloklandi!\n🆔 ID: <code>{user['user_id']}</code>",
        reply_markup=admin_keyboard(),
    )

@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()[1:]
    if not args:
        await message.answer("⚠️ Foydalanish: /unban &lt;user_id yoki @username&gt;")
        return
    user = db.find_user(args[0])
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return
    db.unban_user(user["user_id"])
    try:
        await bot.send_message(user["user_id"], "✅ Siz blokdan chiqarildingiz. /start bosing.")
    except Exception:
        pass
    await message.answer(
        f"✅ <b>{user_display(user)}</b> blokdan chiqarildi!",
        reply_markup=admin_keyboard(),
    )


# ══════════════════════════════════════════════════════════════
#  ODDIY O'YIN
# ══════════════════════════════════════════════════════════════

@router.message(F.text == "🎮 O'yin boshlash")
async def start_game(message: Message, state: FSMContext):
    uid = message.from_user.id
    if db.is_banned(uid):
        await message.answer("🚫 Siz botdan bloklangansiz.")
        return
    bid, _ = db.get_battle_by_user(uid)
    if bid:
        await message.answer("⚔️ Siz hozir battle o'yinidasisiz! Avval uni yakunlang yoki /cancel bosing.")
        return
    secret = random.randint(1, 100)
    db.set_game(uid, secret, 5)
    await state.set_state(GameState.playing)
    await message.answer(
        "🎮 <b>O'yin boshlandi!</b>\n\n"
        "Men 1–100 oralig'ida son o'yladim 🤫\n"
        "Sizda <b>5 ta imkoniyat</b> bor.\n\n"
        "Birinchi taxminingizni yuboring:",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(GameState.playing)
async def process_guess(message: Message, state: FSMContext):
    uid  = message.from_user.id
    text = message.text.strip() if message.text else ""

    try:
        num = int(text)
        if not (1 <= num <= 100):
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Iltimos 1 dan 100 gacha butun son kiriting.")
        return

    game = db.get_game(uid)
    if not game:
        await state.clear()
        await message.answer("O'yin topilmadi. Qaytadan boshlang.", reply_markup=main_keyboard())
        return

    secret    = game["secret"]
    remaining = game["chances"] - 1
    db.record_guess(uid, num)

    if num == secret:
        used = game["total_chances"] - remaining
        db.win_game(uid, used)
        db.clear_game(uid)
        await state.clear()
        stats = db.get_user_stats(uid)
        xp    = stats["xp"] if stats else 0
        rank  = stats["rank"] if stats else ""
        await message.answer(
            f"🏆 <b>BARAKALLA! Topdingiz!</b>\n\n"
            f"🔢 Men o'ylagan son: <b>{secret}</b>\n"
            f"⚡ {used} ta urinishda topdingiz!\n"
            f"✨ <b>+{db.XP_PER_WIN} XP</b> oldiniz!\n"
            f"💰 Jami XP: <b>{xp}</b>\n"
            f"{rank}\n\n"
            f"Yana o'ynamoqchimisiz?",
            reply_markup=main_keyboard(),
        )
        return

    if remaining == 0:
        db.lose_game(uid)
        db.clear_game(uid)
        await state.clear()
        await message.answer(
            f"😔 <b>Afsuski, imkoniyatlar tugadi!</b>\n\n"
            f"🔢 Men o'ylagan son: <b>{secret}</b> edi.\n\n"
            f"Qayta urinib ko'ring!",
            reply_markup=main_keyboard(),
        )
        return

    db.update_chances(uid, remaining)
    hint = "⬆️ <b>Tepparoq!</b>" if num < secret else "⬇️ <b>Pastroq!</b>"
    dots = "🟢" * remaining + "⚫" * (5 - remaining)
    warn = "\n⚠️ <b>Oxirgi imkoniyat!</b>" if remaining == 1 else ""

    await message.answer(
        f"{hint}\n\n"
        f"Kiritdingiz: <b>{num}</b>\n"
        f"Imkoniyatlar: {dots} ({remaining} qoldi){warn}\n\n"
        f"Keyingi taxminingizni yuboring:",
    )


# ══════════════════════════════════════════════════════════════
#  1vs1 BATTLE — YANGI LOGIKA
#
#  Qoidalar:
#  • Battle boshlanganda 1 ta umumiy yashirin son o'ylanadi
#  • Challenger birinchi o'ynaydi, keyin opponent, navbat almashinadi
#  • Har taxmindan so'ng raqibga "U X kiritdi, Y dedi" xabari ketadi
#  • Imkoniyatlar cheksiz — birinchi topgan g'olib
#  • Navbat almashinishi majburiy — navbat bo'lmaganida yozsang ogohlantiriladi
# ══════════════════════════════════════════════════════════════

@router.message(F.text == "⚔️ 1vs1 Battle")
async def battle_menu(message: Message, state: FSMContext):
    uid = message.from_user.id
    if db.is_banned(uid):
        await message.answer("🚫 Siz botdan bloklangansiz.")
        return

    bid, existing = db.get_battle_by_user(uid)
    if bid:
        await message.answer(
            "⚔️ Siz hozir battle o'yinidasisiz!\n"
            "Avval uni yakunlang yoki /cancel bosing."
        )
        return

    waiting = [(b2, b) for b2, b in db.get_waiting_battles() if b["challenger"] != uid]

    if waiting:
        bid2, b = waiting[0]
        challenger = db.find_user(str(b["challenger"]))
        c_name  = user_display(challenger) if challenger else str(b["challenger"])
        c_stats = db.get_user_stats(b["challenger"])
        c_xp    = c_stats["xp"]   if c_stats else 0
        c_rank  = c_stats["rank"] if c_stats else "—"

        await message.answer(
            f"⚔️ <b>Battle topildi!</b>\n\n"
            f"🥊 Raqib: <b>{c_name}</b>\n"
            f"💰 XP: <b>{c_xp}</b>  |  {c_rank}\n\n"
            f"Qabul qilasizmi?",
            reply_markup=battle_join_inline(bid2, c_name),
        )
    else:
        bid2     = db.create_battle(uid)
        my_stats = db.get_user_stats(uid)
        my_xp    = my_stats["xp"] if my_stats else 0

        await message.answer(
            f"⚔️ <b>Battle yaratildi!</b>\n\n"
            f"Raqib kutilmoqda... 🕐\n\n"
            f"💰 Sizning XP: <b>{my_xp}</b>\n"
            f"🏆 Yutganda: <b>+{db.XP_BATTLE_WIN} XP</b>\n"
            f"😔 Yutqazganda: <b>-{db.XP_BATTLE_LOSE} XP</b>\n\n"
            f"<i>Boshqa foydalanuvchi ⚔️ 1vs1 Battle bosganda siz bilan o'ynaydi.</i>\n\n"
            f"/cancel — bekor qilish",
            reply_markup=ReplyKeyboardRemove(),
        )


# ── Battle qabul qilish ───────────────────────────────────────

@router.callback_query(F.data.startswith("join_battle_"))
async def cb_join_battle(call: CallbackQuery, state: FSMContext, bot: Bot):
    uid       = call.from_user.id
    battle_id = call.data[len("join_battle_"):]

    battle = db.get_battle(battle_id)
    if not battle or battle["status"] != "waiting":
        await call.answer("❌ Bu battle artiq mavjud emas yoki boshlangan.", show_alert=True)
        return

    if battle["challenger"] == uid:
        await call.answer("❌ O'z battleingizga qo'shila olmaysiz!", show_alert=True)
        return

    if db.is_banned(uid):
        await call.answer("🚫 Siz bloklangansiz.", show_alert=True)
        return

    # Umumiy bir xil yashirin son
    secret = random.randint(1, 100)
    ok = db.join_battle(battle_id, uid, secret)
    if not ok:
        await call.answer("❌ Battle boshlashda xatolik.", show_alert=True)
        return

    challenger = db.find_user(str(battle["challenger"]))
    c_name     = user_display(challenger) if challenger else str(battle["challenger"])
    o_name     = call.from_user.first_name or str(uid)

    # Challenger ga xabar (u birinchi o'ynaydi)
    try:
        await bot.send_message(
            battle["challenger"],
            f"⚔️ <b>Battle boshlandi!</b>\n\n"
            f"🥊 Raqibingiz: <b>{o_name}</b>\n\n"
            f"Men 1–100 oralig'ida <b>bitta umumiy son</b> o'yladim.\n"
            f"Ikkingiz ham shu sonni topishingiz kerak!\n\n"
            f"🎯 <b>Siz birinchi o'ynaysiz!</b>\n"
            f"Taxminingizni yuboring 👇",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception:
        pass

    await call.answer("✅ Battle qabul qilindi!")
    await call.message.answer(
        f"⚔️ <b>Battle boshlandi!</b>\n\n"
        f"🥊 Raqibingiz: <b>{c_name}</b>\n\n"
        f"Men 1–100 oralig'ida <b>bitta umumiy son</b> o'yladim.\n"
        f"Ikkingiz ham shu sonni topishingiz kerak!\n\n"
        f"⏳ <b>Hozir raqibingiz navbatida.</b> Kutib turing...",
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.set_state(BattleState.playing)
    await state.update_data(battle_id=battle_id)


# ── Battle rad etish ──────────────────────────────────────────

@router.callback_query(F.data.startswith("decline_battle_"))
async def cb_decline_battle(call: CallbackQuery, bot: Bot):
    battle_id = call.data[len("decline_battle_"):]
    battle    = db.get_battle(battle_id)

    await call.answer("❌ Battle rad etildi.")
    await call.message.answer("❌ Battle rad etildi.", reply_markup=main_keyboard())

    if battle:
        try:
            await bot.send_message(
                battle["challenger"],
                "😔 Raqib battle taklifingizni rad etdi.\n\nQaytadan urinib ko'ring!",
                reply_markup=main_keyboard(),
            )
        except Exception:
            pass
        db.delete_battle(battle_id)


# ── Battle o'yini — taxmin ────────────────────────────────────

async def _process_battle_guess(uid: int, num: int, battle_id: str, battle: dict,
                                 message: Message, state: FSMContext, bot: Bot):
    """Battle taxminini qayta ishlash — challenger va opponent uchun umumiy kod."""

    is_challenger = (battle["challenger"] == uid)
    role          = "challenger" if is_challenger else "opponent"
    rival_id      = battle["opponent"] if is_challenger else battle["challenger"]

    # Navbat tekshirish
    turn = db.whose_turn(battle_id)
    my_turn_role = "challenger" if is_challenger else "opponent"
    if turn != my_turn_role:
        await message.answer("⏳ Hozir <b>raqibingiz navbati</b>. Kutib turing...")
        return

    # Taxminni qayta ishlash
    result = db.battle_make_guess(battle_id, uid, num)

    # Raqibga xabar — "U X kiritdi, Y dedi"
    rival_user = db.find_user(str(uid))
    my_name    = user_display(rival_user) if rival_user else str(uid)

    if result["correct"]:
        # Men topdim!
        guess_count = result["guess_count"]

        await message.answer(
            f"🏆 <b>TOPDINGIZ!</b>\n\n"
            f"🔢 Yashirin son: <b>{battle['secret']}</b>\n"
            f"⚡ {guess_count} ta urinishda topdingiz!\n\n"
            f"⏳ Natija hisoblanmoqda..."
        )

        # Raqibga g'alaba xabari
        try:
            await bot.send_message(
                rival_id,
                f"😔 <b>Raqibingiz sonni topdi!</b>\n\n"
                f"🥊 {my_name} — {guess_count} urinishda topdi.\n"
                f"🔢 Yashirin son: <b>{battle['secret']}</b>\n\n"
                f"Natija chiqarilmoqda..."
            )
        except Exception:
            pass

        # Battleni yakunlash
        finished = db.finish_battle(battle_id)
        if finished:
            await _send_battle_result(finished, bot, state)
        return

    # Noto'g'ri taxmin
    h_text       = hint_text(result["hint"])
    guess_count  = result["guess_count"]

    await message.answer(
        f"⚔️ <b>Battle</b> | {h_text}\n\n"
        f"Kiritdingiz: <b>{num}</b>\n"
        f"Jami urinishlaringiz: <b>{guess_count}</b>\n\n"
        f"⏳ Raqibingiz navbati. Kutib turing..."
    )

    # Raqibga: "U X kiritdi, Y dedi — endi sening navbating"
    rival_hint = "tepparoq" if result["hint"] == "higher" else "pastroq"
    try:
        await bot.send_message(
            rival_id,
            f"🎯 <b>Raqibingiz taxmin qildi!</b>\n\n"
            f"🥊 {my_name}: <b>{num}</b> kiritdi\n"
            f"💬 Bot: {rival_hint} dedi\n\n"
            f"🎮 <b>Sening navbating!</b> Taxminingizni yuboring 👇"
        )
    except Exception:
        pass


@router.message(BattleState.playing)
async def battle_guess(message: Message, state: FSMContext, bot: Bot):
    uid  = message.from_user.id
    text = message.text.strip() if message.text else ""

    try:
        num = int(text)
        if not (1 <= num <= 100):
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Battle o'yinidasiz! 1–100 oralig'ida butun son kiriting.")
        return

    data      = await state.get_data()
    battle_id = data.get("battle_id")

    if not battle_id:
        bid, battle = db.get_battle_by_user(uid)
        battle_id   = bid
    else:
        battle = db.get_battle(battle_id)

    if not battle or battle["status"] != "playing":
        await state.clear()
        await message.answer("⚔️ Battle topilmadi.", reply_markup=main_keyboard())
        return

    await _process_battle_guess(uid, num, battle_id, battle, message, state, bot)


# ── Battle natijasini yuborish ────────────────────────────────

async def _send_battle_result(finished: dict, bot: Bot, state: FSMContext):
    c_id   = finished["challenger"]
    o_id   = finished["opponent"]
    winner = finished["winner"]
    cs     = finished["challenger_score"]  # nechta urinishda topdi
    os_    = finished["opponent_score"]

    c_user = db.find_user(str(c_id))
    o_user = db.find_user(str(o_id))
    c_name = user_display(c_user) if c_user else str(c_id)
    o_name = user_display(o_user) if o_user else str(o_id)

    def score_str(s):
        return f"{s} urinishda topdi ✅" if s is not None else "topa olmadi ❌"

    if winner is None:
        result_line = "🤝 <b>Durrang!</b>"
        xp_c = xp_o = "±0"
    elif winner == c_id:
        result_line = f"🏆 <b>G'olib: {c_name}!</b>"
        xp_c = f"+{db.XP_BATTLE_WIN}"
        xp_o = f"-{db.XP_BATTLE_LOSE}"
    else:
        result_line = f"🏆 <b>G'olib: {o_name}!</b>"
        xp_c = f"-{db.XP_BATTLE_LOSE}"
        xp_o = f"+{db.XP_BATTLE_WIN}"

    secret = finished.get("secret", "?")
    result_msg = (
        f"⚔️ <b>Battle Yakunlandi!</b>\n\n"
        f"{result_line}\n\n"
        f"🔢 Yashirin son: <b>{secret}</b>\n\n"
        f"📊 <b>Natijalar:</b>\n"
        f"• {c_name}: {score_str(cs)}  ({xp_c} XP)\n"
        f"• {o_name}: {score_str(os_)}  ({xp_o} XP)\n\n"
        f"🔄 Qayta o'ynash uchun ⚔️ 1vs1 Battle bosing!"
    )

    for uid in (c_id, o_id):
        try:
            await bot.send_message(uid, result_msg, reply_markup=main_keyboard())
        except Exception:
            pass

    await state.clear()


# ══════════════════════════════════════════════════════════════
#  FOYDALANUVCHI MENYU
# ══════════════════════════════════════════════════════════════

@router.message(F.text == "📊 Mening statistikam")
async def my_stats(message: Message):
    uid = message.from_user.id
    s   = db.get_user_stats(uid)
    if not s:
        await message.answer("📊 Hali statistika yo'q. O'yin boshlang!", reply_markup=main_keyboard())
        return
    xp        = s.get("xp", 0)
    win_rate  = round((s["wins"] / s["total_games"]) * 100) if s.get("total_games", 0) > 0 else 0
    avg       = s["avg_attempts"] or "—"
    best      = s["best_score"]   or "—"
    next_rank = s.get("next_rank") or "Maksimal darajaga erishdingiz! 👑"
    bonus_line = f"\n🎁 Bonus g'alabalar: <b>{s.get('bonus_wins', 0)}</b>" if s.get("bonus_wins") else ""

    await message.answer(
        f"📊 <b>Sizning statistikangiz</b>\n\n"
        f"{s['rank']}  |  💰 <b>{xp} XP</b>\n\n"
        f"🎮 Jami o'yinlar: <b>{s['total_games']}</b>\n"
        f"🏆 G'alabalar: <b>{s['wins']}</b>\n"
        f"😔 Mag'lubiyatlar: <b>{s['losses']}</b>\n"
        f"📈 G'alaba foizi: <b>{win_rate}%</b>\n"
        f"⚡ O'rtacha urinish: <b>{avg}</b>\n"
        f"🥇 Eng yaxshi natija: <b>{best} urinish</b>{bonus_line}\n\n"
        f"⚔️ <b>Battle:</b>\n"
        f"🏆 Battle g'alabalar: <b>{s.get('battle_wins', 0)}</b>\n"
        f"😔 Battle mag'lubiyatlar: <b>{s.get('battle_losses', 0)}</b>\n\n"
        f"📌 <i>{next_rank}</i>",
        reply_markup=main_keyboard(),
    )


@router.message(F.text == "🏆 Reyting")
async def leaderboard(message: Message):
    top = db.get_leaderboard(10)
    if not top:
        await message.answer("🏆 Hali reyting yo'q.", reply_markup=main_keyboard())
        return
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines  = []
    for i, u in enumerate(top):
        xp = u.get("xp", 0)
        lines.append(
            f"{medals[i]} {user_display(u)}\n"
            f"   {u['rank']} | 💰 {xp} XP | 🏆 {u['wins']} g'alaba"
        )
    await message.answer(
        "🏆 <b>Top 10 O'yinchilar (XP bo'yicha)</b>\n\n" + "\n\n".join(lines),
        reply_markup=main_keyboard(),
    )


@router.message(F.text == "ℹ️ Qoidalar")
async def rules(message: Message):
    await message.answer(
        "ℹ️ <b>O'yin Qoidalari</b>\n\n"
        "━━━ 🎮 Oddiy O'yin ━━━\n"
        "• Bot 1–100 oralig'ida yashirin son o'ylaydi\n"
        "• Sizga <b>5 ta</b> taxmin qilish imkoni beriladi\n"
        "• Har taxmingizdan keyin: ⬆️ Tepparoq / ⬇️ Pastroq\n\n"
        "━━━ ⚔️ 1vs1 Battle ━━━\n"
        "• Ikkala o'yinchi <b>bir xil yashirin son</b>ni topadi\n"
        "• <b>Navbat bilan</b> taxmin qilinadi\n"
        "• <b>Imkoniyatlar cheksiz</b> — birinchi topgan g'olib!\n"
        "• Har taxmindan so'ng raqibga xabar ketadi\n\n"
        "━━━ 💰 XP Tizimi ━━━\n"
        f"✅ Oddiy o'yin g'alabasi: <b>+{db.XP_PER_WIN} XP</b>\n"
        f"⚔️ Battle g'alabasi: <b>+{db.XP_BATTLE_WIN} XP</b>\n"
        f"😔 Battle mag'lubiyati: <b>-{db.XP_BATTLE_LOSE} XP</b>\n\n"
        "━━━ 🏅 Darajalar ━━━\n"
        "🥉 Yangi boshlovchi — 0+ XP\n"
        "🥈 O'yinchi — 150+ XP\n"
        "🥇 Tajribali — 450+ XP\n"
        "💎 Expert — 900+ XP\n"
        "👑 Legend — 1500+ XP\n\n"
        "<i>Omad tilaymiz!</i> 🍀",
        reply_markup=main_keyboard(),
    )


# ══════════════════════════════════════════════════════════════
#  ADMIN PANEL
# ══════════════════════════════════════════════════════════════

@router.message(F.text == "👥 Foydalanuvchilar")
async def all_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = db.get_all_users()
    if not users:
        await message.answer("👥 Hali foydalanuvchi yo'q.", reply_markup=admin_keyboard())
        return
    chunk = 25
    for i in range(0, len(users), chunk):
        part  = users[i:i + chunk]
        lines = []
        for j, u in enumerate(part):
            icon = "🚫" if u.get("banned") else "✅"
            xp   = u.get("xp", 0)
            lines.append(
                f"{icon} {i+j+1}. {user_display(u)} | <code>{u['user_id']}</code>\n"
                f"   🎮 {u['total_games']} o'yin | 🏆 {u['wins']} g'alaba | 💰 {xp} XP"
            )
        await message.answer(
            f"👥 <b>Foydalanuvchilar ({i+1}–{min(i+chunk, len(users))} / {len(users)})</b>\n\n"
            + "\n\n".join(lines),
            reply_markup=admin_keyboard(),
        )


@router.message(F.text == "📈 Statistika")
async def global_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    s = db.get_global_stats()
    await message.answer(
        f"📈 <b>Umumiy Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{s['total_users']}</b>\n"
        f"🚫 Bloklangan: <b>{s['banned_count']}</b>\n"
        f"✅ Faol: <b>{s['total_users'] - s['banned_count']}</b>\n\n"
        f"🎮 Jami o'yinlar: <b>{s['total_games']}</b>\n"
        f"🏆 G'alabalar: <b>{s['total_wins']}</b>\n"
        f"😔 Mag'lubiyatlar: <b>{s['total_losses']}</b>\n"
        f"📊 G'alaba foizi: <b>{s['win_rate']}%</b>\n"
        f"⚡ O'rtacha urinish: <b>{s['avg_attempts']}</b>\n"
        f"⚔️ Aktiv battle: <b>{s['active_battles']}</b>\n\n"
        f"📅 <b>Bugun:</b>\n"
        f"🎮 O'yinlar: <b>{s['today_games']}</b>\n"
        f"🏆 G'alabalar: <b>{s['today_wins']}</b>\n"
        f"👤 Faol o'yinchilar: <b>{s['today_players']}</b>",
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "📅 Kunlik hisobot")
async def daily_report(message: Message):
    if not is_admin(message.from_user.id):
        return
    data = db.get_daily_stats(7)
    if not data:
        await message.answer("📅 Hali kunlik ma'lumot yo'q.", reply_markup=admin_keyboard())
        return
    lines = []
    for d in data:
        lines.append(
            f"📅 <b>{d['date']}</b>\n"
            f"   🎮 {d['games']} o'yin | 🏆 {d['wins']} g'alaba | 😔 {d['losses']} mag | 👤 {d['players']} o'yinchi"
        )
    await message.answer(
        "📅 <b>So'nggi 7 kunlik hisobot</b>\n\n" + "\n\n".join(lines),
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "🚫 Bloklangan")
async def banned_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    banned = db.get_banned_users()
    if not banned:
        await message.answer("✅ Bloklangan foydalanuvchi yo'q.", reply_markup=admin_keyboard())
        return
    lines = [
        f"🚫 {user_display(u)} | <code>{u['user_id']}</code> | {u['joined_at']}"
        for u in banned
    ]
    await message.answer(
        f"🚫 <b>Bloklangan foydalanuvchilar ({len(banned)} ta)</b>\n\n"
        + "\n".join(lines)
        + "\n\n<i>Blokdan chiqarish: /unban &lt;id&gt;</i>",
        reply_markup=admin_keyboard(),
    )


# ── Broadcast ─────────────────────────────────────────────────

@router.message(F.text == "📢 Xabar yuborish")
async def prompt_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.broadcast)
    await message.answer(
        "📢 <b>Hammaga xabar yuborish</b>\n\n"
        "Xabar matnini yozing.\n"
        "Rasm + matn birgalikda yuborishingiz mumkin.\n\n"
        "/cancel — bekor qilish",
        reply_markup=ReplyKeyboardRemove(),
    )

@router.message(AdminStates.broadcast, F.text | F.photo)
async def do_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    users  = [u for u in db.get_all_users() if not u.get("banned")]
    prefix = "📢 <b>Bot xabari:</b>\n\n"
    await message.answer(f"⏳ {len(users)} ta foydalanuvchiga yuborilmoqda...", reply_markup=admin_keyboard())
    sent = failed = 0
    for u in users:
        try:
            if message.photo:
                photo   = message.photo[-1].file_id
                caption = prefix + (message.caption or "")
                await bot.send_photo(u["user_id"], photo=photo, caption=caption)
            else:
                await bot.send_message(u["user_id"], prefix + (message.text or ""))
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(
        f"✅ Xabar yuborildi!\n📤 Muvaffaqiyatli: <b>{sent}</b>\n❌ Xato: <b>{failed}</b>",
        reply_markup=admin_keyboard(),
    )


# ── Qidirish ──────────────────────────────────────────────────

@router.message(F.text == "🔍 Qidirish")
async def prompt_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.search)
    await message.answer(
        "🔍 Foydalanuvchi ID, @username yoki ism kiriting:\n\n/cancel — bekor qilish",
        reply_markup=ReplyKeyboardRemove(),
    )

@router.message(AdminStates.search)
async def do_search(message: Message, state: FSMContext):
    await state.clear()
    user = db.find_user(message.text.strip())
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.", reply_markup=admin_keyboard())
        return
    s          = db.get_user_stats(user["user_id"]) or {}
    name       = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    uname      = f"@{user['username']}" if user.get("username") else "—"
    ban_status = "🚫 Bloklangan" if user.get("banned") else "✅ Faol"
    win_rate   = round((s["wins"] / s["total_games"]) * 100) if s.get("total_games", 0) > 0 else 0
    xp         = s.get("xp", 0)
    await message.answer(
        f"🔍 <b>Foydalanuvchi topildi</b>\n\n"
        f"👤 Ism: <b>{name}</b>\n"
        f"🔗 Username: {uname}\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"📅 Qo'shilgan: {user['joined_at']}\n"
        f"🔰 Holat: {ban_status}\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"🎮 O'yinlar: <b>{s.get('total_games', 0)}</b>\n"
        f"🏆 G'alabalar: <b>{s.get('wins', 0)}</b>\n"
        f"😔 Mag'lubiyatlar: <b>{s.get('losses', 0)}</b>\n"
        f"📈 G'alaba foizi: <b>{win_rate}%</b>\n"
        f"🥇 Eng yaxshi: <b>{s.get('best_score') or '—'} urinish</b>\n"
        f"💰 XP: <b>{xp}</b>\n"
        f"⚔️ Battle g'alabalar: <b>{s.get('battle_wins', 0)}</b>\n"
        f"{s.get('rank', '')}",
        reply_markup=user_action_inline(user["user_id"], bool(user.get("banned"))),
    )
    await message.answer("Asosiy menyu:", reply_markup=admin_keyboard())


# ── Bonus berish ──────────────────────────────────────────────

@router.message(F.text == "🎁 Bonus berish")
async def prompt_bonus(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.bonus)
    await message.answer(
        "🎁 <b>Bonus berish</b>\n\n"
        "Formatda yozing:\n<code>@username 10</code>  yoki  <code>123456789 5</code>\n\n"
        "<i>(username, bo'sh joy, keyin g'alabalar soni)</i>\n\n"
        "/cancel — bekor qilish",
        reply_markup=ReplyKeyboardRemove(),
    )

@router.message(AdminStates.bonus)
async def do_bonus(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    parts = (message.text or "").strip().split()
    if len(parts) < 2 or not parts[-1].isdigit():
        await message.answer("⚠️ Noto'g'ri format. Masalan: @username 10", reply_markup=admin_keyboard())
        return
    amount = int(parts[-1])
    query  = " ".join(parts[:-1])
    if not (1 <= amount <= 100):
        await message.answer("⚠️ Bonus 1 dan 100 gacha bo'lishi kerak.", reply_markup=admin_keyboard())
        return
    user = db.find_user(query)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.", reply_markup=admin_keyboard())
        return
    db.add_bonus_wins(user["user_id"], amount)
    xp_added = amount * db.XP_PER_WIN
    try:
        await bot.send_message(
            user["user_id"],
            f"🎁 <b>Tabriklaymiz!</b>\n\nAdmin sizga <b>{amount} ta bonus g'alaba</b> va <b>{xp_added} XP</b> berdi! 🏆",
        )
    except Exception:
        pass
    await message.answer(
        f"✅ <b>{user_display(user)}</b> ga <b>{amount}</b> ta bonus ({xp_added} XP) berildi!",
        reply_markup=admin_keyboard(),
    )


# ── Bonus inline (qidiruv orqali) ────────────────────────────

@router.message(AdminStates.bonus_inline)
async def do_bonus_inline(message: Message, state: FSMContext, bot: Bot):
    data      = await state.get_data()
    target_id = data.get("target_id")
    await state.clear()

    text = (message.text or "").strip()
    if not text.isdigit() or not (1 <= int(text) <= 100):
        await message.answer("⚠️ Faqat 1–100 orasida raqam kiriting.", reply_markup=admin_keyboard())
        return

    amount   = int(text)
    xp_added = amount * db.XP_PER_WIN
    user     = db.find_user(str(target_id))
    name     = user_display(user) if user else str(target_id)
    db.add_bonus_wins(target_id, amount)
    try:
        await bot.send_message(
            target_id,
            f"🎁 <b>Tabriklaymiz!</b>\n\nAdmin sizga <b>{amount} ta bonus g'alaba</b> va <b>{xp_added} XP</b> berdi! 🏆",
        )
    except Exception:
        pass
    await message.answer(
        f"✅ <b>{name}</b> ga <b>{amount}</b> ta bonus ({xp_added} XP) berildi!",
        reply_markup=admin_keyboard(),
    )


# ── Tozalash ──────────────────────────────────────────────────

@router.message(F.text == "🗑 Ma'lumot tozalash")
async def confirm_clear_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "⚠️ <b>Haqiqatan ham barcha statistikani o'chirmoqchimisiz?</b>\n\n"
        "Foydalanuvchilar ro'yxati saqlanadi, faqat o'yin natijalari, XP va battle ma'lumotlar o'chadi.",
        reply_markup=confirm_clear_inline(),
    )


@router.message(F.text == "⬅️ Asosiy menyu")
async def back_to_main(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("⬅️ Asosiy menyudasiz.", reply_markup=main_keyboard())


# ══════════════════════════════════════════════════════════════
#  CALLBACK HANDLERLAR
# ══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("ban_"))
async def cb_ban(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q")
        return
    target_id = int(call.data.split("_")[1])
    user      = db.find_user(str(target_id))
    db.ban_user(target_id)
    db.clear_game(target_id)
    try:
        await bot.send_message(target_id, "🚫 Siz administrator tomonidan bloklangansiz.")
    except Exception:
        pass
    name = user_display(user) if user else str(target_id)
    await call.answer("✅ Bloklandi")
    await call.message.answer(f"🚫 <b>{name}</b> bloklandi.", reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith("unban_"))
async def cb_unban(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q")
        return
    target_id = int(call.data.split("_")[1])
    user      = db.find_user(str(target_id))
    db.unban_user(target_id)
    try:
        await bot.send_message(target_id, "✅ Siz blokdan chiqarildingiz. /start bosing.")
    except Exception:
        pass
    name = user_display(user) if user else str(target_id)
    await call.answer("✅ Blokdan chiqarildi")
    await call.message.answer(f"✅ <b>{name}</b> blokdan chiqarildi.", reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith("bonus_"))
async def cb_bonus(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q")
        return
    target_id = int(call.data.split("_")[1])
    user      = db.find_user(str(target_id))
    name      = user_display(user) if user else str(target_id)
    await state.set_state(AdminStates.bonus_inline)
    await state.update_data(target_id=target_id)
    await call.answer()
    await call.message.answer(
        f"🎁 <b>{name}</b> ga nechta bonus g'alaba bermoqchisiz?\n\n"
        f"Faqat raqam yuboring (1–100).\n/cancel — bekor qilish",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.callback_query(F.data == "confirm_clear")
async def cb_confirm_clear(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q")
        return
    db.clear_all_games()
    await call.answer("✅ Tozalandi!")
    await call.message.answer("✅ Barcha statistika va XP tozalandi.", reply_markup=admin_keyboard())


@router.callback_query(F.data == "cancel_clear")
async def cb_cancel_clear(call: CallbackQuery):
    await call.answer("Bekor qilindi")
    await call.message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())


# ── Challenger fallback (FSM state yo'q bo'lganda) ────────────

@router.message(F.text)
async def handle_text_fallback(message: Message, state: FSMContext, bot: Bot):
    uid = message.from_user.id

    if db.is_banned(uid):
        await message.answer("🚫 Siz botdan bloklangansiz.")
        return

    # Aktiv battle bormi?
    bid, battle = db.get_battle_by_user(uid)
    if bid and battle and battle["status"] == "playing":
        text = message.text.strip() if message.text else ""
        try:
            num = int(text)
            if not (1 <= num <= 100):
                raise ValueError
        except ValueError:
            await message.answer("⚠️ Battle o'yinidasiz! 1–100 oralig'ida butun son kiriting.")
            return

        await state.set_state(BattleState.playing)
        await state.update_data(battle_id=bid)
        await _process_battle_guess(uid, num, bid, battle, message, state, bot)
        return

    kb = admin_keyboard() if is_admin(uid) else main_keyboard()
    await message.answer("👇 Quyidagi tugmalardan foydalaning:", reply_markup=kb)


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN topilmadi! .env faylini tekshiring.")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    log.info("🤖 Bot ishga tushdi (aiogram 3.x)...")
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
