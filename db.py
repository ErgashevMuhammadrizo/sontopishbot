import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.json")

# ─── XP Tizimi ───────────────────────────────────────────────
XP_PER_WIN        = 30   # Oddiy o'yinda 1 g'alaba = 30 XP
XP_BATTLE_WIN     = 20   # 1vs1 battle yutganda +20 XP
XP_BATTLE_LOSE    = 10   # 1vs1 battle yutkazganda -10 XP

# ─── Darajalar tizimi (XP bo'yicha) ─────────────────────────
RANKS = [
    {"name": "🥉 Yangi boshlovchi", "min_xp": 0},
    {"name": "🥈 O'yinchi",         "min_xp": 150},
    {"name": "🥇 Tajribali",        "min_xp": 450},
    {"name": "💎 Expert",           "min_xp": 900},
    {"name": "👑 Legend",           "min_xp": 1500},
]

def get_rank(xp: int) -> str:
    rank = RANKS[0]["name"]
    for r in RANKS:
        if xp >= r["min_xp"]:
            rank = r["name"]
    return rank

def get_next_rank_info(xp: int) -> str | None:
    for r in RANKS:
        if xp < r["min_xp"]:
            needed = r["min_xp"] - xp
            return f"{r['name']} darajasiga {needed} XP kerak"
    return None


# ─── Yuklash / saqlash ───────────────────────────────────────
def _load() -> dict:
    if not os.path.exists(DB_PATH):
        _save({"users": {}, "games": {}, "battles": {}, "states": {}, "daily": {}})
    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "daily"   not in data: data["daily"]   = {}
    if "battles" not in data: data["battles"] = {}
    return data

def _save(data: dict):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ─── Foydalanuvchi ───────────────────────────────────────────
def upsert_user(user_id: int, first_name: str, last_name: str | None, username: str | None) -> bool:
    db  = _load()
    key = str(user_id)
    is_new = key not in db["users"]
    if is_new:
        db["users"][key] = {
            "user_id":        user_id,
            "first_name":     first_name or "",
            "last_name":      last_name  or "",
            "username":       username   or "",
            "joined_at":      datetime.now().strftime("%d.%m.%Y %H:%M"),
            "total_games":    0,
            "wins":           0,
            "losses":         0,
            "total_attempts": 0,
            "best_score":     None,
            "banned":         False,
            "bonus_wins":     0,
            "xp":             0,
            "battle_wins":    0,
            "battle_losses":  0,
        }
    else:
        u = db["users"][key]
        u["first_name"] = first_name or u["first_name"]
        u["last_name"]  = last_name  or u["last_name"]
        u["username"]   = username   or u["username"]
        # Eski foydalanuvchilarda yangi maydonlar bo'lmasa qo'shamiz
        if "xp"            not in u: u["xp"]            = u.get("wins", 0) * XP_PER_WIN
        if "battle_wins"   not in u: u["battle_wins"]   = 0
        if "battle_losses" not in u: u["battle_losses"] = 0
    _save(db)
    return is_new

def get_all_users() -> list:
    db = _load()
    return sorted(db["users"].values(), key=lambda u: u.get("xp", 0), reverse=True)

def find_user(query: str) -> dict | None:
    db = _load()
    q  = query.lstrip("@").lower()
    for u in db["users"].values():
        if (str(u["user_id"]) == q
                or (u.get("username") and u["username"].lower() == q)
                or (u.get("first_name") and q in u["first_name"].lower())):
            return u
    return None

def is_banned(user_id: int) -> bool:
    db = _load()
    u  = db["users"].get(str(user_id))
    return bool(u and u.get("banned"))

def ban_user(user_id: int):
    db  = _load()
    key = str(user_id)
    if key in db["users"]:
        db["users"][key]["banned"] = True
        _save(db)

def unban_user(user_id: int):
    db  = _load()
    key = str(user_id)
    if key in db["users"]:
        db["users"][key]["banned"] = False
        _save(db)

def add_bonus_wins(user_id: int, amount: int) -> bool:
    db  = _load()
    key = str(user_id)
    if key not in db["users"]:
        return False
    db["users"][key]["wins"]        += amount
    db["users"][key]["bonus_wins"]  += amount
    db["users"][key]["total_games"] += amount
    db["users"][key]["xp"]          = db["users"][key].get("xp", 0) + amount * XP_PER_WIN
    _save(db)
    return True


# ─── O'yin ───────────────────────────────────────────────────
def set_game(user_id: int, secret: int, chances: int):
    db = _load()
    db["games"][str(user_id)] = {
        "secret":        secret,
        "chances":       chances,
        "total_chances": chances,
        "guesses":       [],
    }
    _save(db)

def get_game(user_id: int) -> dict | None:
    return _load()["games"].get(str(user_id))

def update_chances(user_id: int, remaining: int):
    db = _load()
    if str(user_id) in db["games"]:
        db["games"][str(user_id)]["chances"] = remaining
    _save(db)

def record_guess(user_id: int, num: int):
    db = _load()
    if str(user_id) in db["games"]:
        db["games"][str(user_id)]["guesses"].append(num)
    _save(db)

def clear_game(user_id: int):
    db = _load()
    db["games"].pop(str(user_id), None)
    _save(db)

def win_game(user_id: int, attempts_used: int):
    db  = _load()
    key = str(user_id)
    if key not in db["users"]:
        return
    u = db["users"][key]
    u["total_games"]    += 1
    u["wins"]           += 1
    u["total_attempts"] += attempts_used
    u["xp"]              = u.get("xp", 0) + XP_PER_WIN
    if u["best_score"] is None or attempts_used < u["best_score"]:
        u["best_score"] = attempts_used
    today = _today()
    if today not in db["daily"]:
        db["daily"][today] = {"games": 0, "wins": 0, "losses": 0, "players": []}
    db["daily"][today]["games"] += 1
    db["daily"][today]["wins"]  += 1
    if user_id not in db["daily"][today]["players"]:
        db["daily"][today]["players"].append(user_id)
    _save(db)

def lose_game(user_id: int):
    db  = _load()
    key = str(user_id)
    if key not in db["users"]:
        return
    db["users"][key]["total_games"] += 1
    db["users"][key]["losses"]      += 1
    today = _today()
    if today not in db["daily"]:
        db["daily"][today] = {"games": 0, "wins": 0, "losses": 0, "players": []}
    db["daily"][today]["games"]  += 1
    db["daily"][today]["losses"] += 1
    if user_id not in db["daily"][today]["players"]:
        db["daily"][today]["players"].append(user_id)
    _save(db)

def clear_all_games():
    db = _load()
    db["games"]   = {}
    db["battles"] = {}
    for u in db["users"].values():
        u["total_games"]    = 0
        u["wins"]           = 0
        u["losses"]         = 0
        u["total_attempts"] = 0
        u["best_score"]     = None
        u["bonus_wins"]     = 0
        u["xp"]             = 0
        u["battle_wins"]    = 0
        u["battle_losses"]  = 0
    db["daily"] = {}
    _save(db)


# ─── 1vs1 Battle ─────────────────────────────────────────────
def create_battle(challenger_id: int) -> str:
    """Battle yaratish. Battle ID qaytaradi."""
    db = _load()
    battle_id = f"b_{challenger_id}_{int(datetime.now().timestamp())}"
    db["battles"][battle_id] = {
        "challenger":    challenger_id,
        "opponent":      None,
        "status":        "waiting",      # waiting | playing | finished
        "challenger_secret": None,
        "opponent_secret":   None,
        "challenger_score":  None,       # urinishlar soni (yutsa), None = yutqazdi
        "opponent_score":    None,
        "winner":        None,
        "created_at":    datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    _save(db)
    return battle_id

def get_battle(battle_id: str) -> dict | None:
    return _load()["battles"].get(battle_id)

def get_battle_by_user(user_id: int) -> tuple[str, dict] | tuple[None, None]:
    """Foydalanuvchining aktiv battleni topish."""
    db = _load()
    for bid, b in db["battles"].items():
        if b["status"] in ("waiting", "playing"):
            if b["challenger"] == user_id or b["opponent"] == user_id:
                return bid, b
    return None, None

def join_battle(battle_id: str, opponent_id: int, challenger_secret: int, opponent_secret: int) -> bool:
    db = _load()
    if battle_id not in db["battles"]:
        return False
    b = db["battles"][battle_id]
    if b["status"] != "waiting":
        return False
    b["opponent"]         = opponent_id
    b["status"]           = "playing"
    b["challenger_secret"] = challenger_secret
    b["opponent_secret"]   = opponent_secret
    _save(db)
    return True

def set_battle_score(battle_id: str, user_id: int, score: int | None):
    """score = urinishlar soni (yutsa), None = yutqazdi."""
    db = _load()
    if battle_id not in db["battles"]:
        return
    b = db["battles"][battle_id]
    if b["challenger"] == user_id:
        b["challenger_score"] = score
    elif b["opponent"] == user_id:
        b["opponent_score"] = score
    _save(db)

def finish_battle(battle_id: str) -> dict | None:
    """Ikkala natija tayyor bo'lsa battleni yakunlash. Winner dict qaytaradi."""
    db = _load()
    if battle_id not in db["battles"]:
        return None
    b = db["battles"][battle_id]
    if b["challenger_score"] == "pending" or b["opponent_score"] == "pending":
        return None

    cs = b["challenger_score"]
    os_ = b["opponent_score"]

    # Yutuvchini aniqlash: kichik urinish = yaxshiroq; None = yutqazdi
    if cs is None and os_ is None:
        winner_id = None  # Draw (ikkalasi ham yutqazdi)
    elif cs is None:
        winner_id = b["opponent"]
    elif os_ is None:
        winner_id = b["challenger"]
    elif cs < os_:
        winner_id = b["challenger"]
    elif os_ < cs:
        winner_id = b["opponent"]
    else:
        winner_id = None  # Teng natija

    b["winner"] = winner_id
    b["status"] = "finished"

    # XP berish
    c_id = str(b["challenger"])
    o_id = str(b["opponent"])
    if c_id in db["users"] and o_id in db["users"]:
        if winner_id == b["challenger"]:
            db["users"][c_id]["xp"]           = db["users"][c_id].get("xp", 0) + XP_BATTLE_WIN
            db["users"][c_id]["battle_wins"]   = db["users"][c_id].get("battle_wins", 0) + 1
            db["users"][o_id]["xp"]            = max(0, db["users"][o_id].get("xp", 0) - XP_BATTLE_LOSE)
            db["users"][o_id]["battle_losses"] = db["users"][o_id].get("battle_losses", 0) + 1
        elif winner_id == b["opponent"]:
            db["users"][o_id]["xp"]            = db["users"][o_id].get("xp", 0) + XP_BATTLE_WIN
            db["users"][o_id]["battle_wins"]    = db["users"][o_id].get("battle_wins", 0) + 1
            db["users"][c_id]["xp"]             = max(0, db["users"][c_id].get("xp", 0) - XP_BATTLE_LOSE)
            db["users"][c_id]["battle_losses"]  = db["users"][c_id].get("battle_losses", 0) + 1
        else:
            # Draw — XP o'zgarmaydi
            pass

    _save(db)
    return b

def delete_battle(battle_id: str):
    db = _load()
    db["battles"].pop(battle_id, None)
    _save(db)

def get_waiting_battles() -> list[tuple[str, dict]]:
    """Kutayotgan battlelar ro'yxati."""
    db = _load()
    result = []
    for bid, b in db["battles"].items():
        if b["status"] == "waiting":
            result.append((bid, b))
    return result


# ─── Statistika ──────────────────────────────────────────────
def get_user_stats(user_id: int) -> dict | None:
    db = _load()
    u  = db["users"].get(str(user_id))
    if not u:
        return None
    xp  = u.get("xp", u.get("wins", 0) * XP_PER_WIN)
    avg = round(u["total_attempts"] / u["wins"], 1) if u["wins"] > 0 else None
    return {
        **u,
        "xp":           xp,
        "avg_attempts": avg,
        "rank":         get_rank(xp),
        "next_rank":    get_next_rank_info(xp),
    }

def get_global_stats() -> dict:
    db    = _load()
    users = list(db["users"].values())
    total_games  = sum(u["total_games"]    for u in users)
    total_wins   = sum(u["wins"]           for u in users)
    total_losses = sum(u["losses"]         for u in users)
    total_att    = sum(u["total_attempts"] for u in users)
    banned_count = sum(1 for u in users if u.get("banned"))
    win_rate     = round((total_wins / total_games) * 100) if total_games > 0 else 0
    avg          = round(total_att / total_wins, 1) if total_wins > 0 else "—"
    today      = _today()
    today_data = db.get("daily", {}).get(today, {})
    # Faol / bot bloklagan hisob (haqiqiy Telegram API kerak, DB dan approximation)
    active_battles = sum(1 for b in db.get("battles", {}).values() if b["status"] in ("waiting","playing"))
    return {
        "total_users":    len(users),
        "banned_count":   banned_count,
        "total_games":    total_games,
        "total_wins":     total_wins,
        "total_losses":   total_losses,
        "win_rate":       win_rate,
        "avg_attempts":   avg,
        "today_games":    today_data.get("games", 0),
        "today_wins":     today_data.get("wins",  0),
        "today_players":  len(today_data.get("players", [])),
        "active_battles": active_battles,
    }

def get_leaderboard(limit: int = 10) -> list:
    db    = _load()
    users = [u for u in db["users"].values() if not u.get("banned")]
    users.sort(key=lambda u: u.get("xp", 0), reverse=True)
    result = []
    for u in users[:limit]:
        xp  = u.get("xp", 0)
        avg = round(u["total_attempts"] / u["wins"], 1) if u["wins"] > 0 else "—"
        result.append({**u, "avg_attempts": avg, "rank": get_rank(xp), "xp": xp})
    return result

def get_daily_stats(days: int = 7) -> list:
    db     = _load()
    daily  = db.get("daily", {})
    result = []
    for d in sorted(daily.keys(), reverse=True)[:days]:
        info = daily[d]
        result.append({
            "date":    d,
            "games":   info.get("games",   0),
            "wins":    info.get("wins",    0),
            "losses":  info.get("losses",  0),
            "players": len(info.get("players", [])),
        })
    return result

def get_banned_users() -> list:
    db = _load()
    return [u for u in db["users"].values() if u.get("banned")]


# ─── State ───────────────────────────────────────────────────
def set_state(user_id: int, state: str | None):
    db = _load()
    if state is None:
        db["states"].pop(str(user_id), None)
    else:
        db["states"][str(user_id)] = state
    _save(db)

def get_state(user_id: int) -> str | None:
    return _load()["states"].get(str(user_id))
