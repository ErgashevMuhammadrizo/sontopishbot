import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.json")

# ─── Darajalar tizimi ────────────────────────────────────────
RANKS = [
    {"name": "🥉 Yangi boshlovchi", "min_wins": 0},
    {"name": "🥈 O'yinchi",         "min_wins": 5},
    {"name": "🥇 Tajribali",        "min_wins": 15},
    {"name": "💎 Expert",           "min_wins": 30},
    {"name": "👑 Legend",           "min_wins": 50},
]

def get_rank(wins: int) -> str:
    rank = RANKS[0]["name"]
    for r in RANKS:
        if wins >= r["min_wins"]:
            rank = r["name"]
    return rank

def get_next_rank_info(wins: int) -> str | None:
    for r in RANKS:
        if wins < r["min_wins"]:
            needed = r["min_wins"] - wins
            return f"{r['name']} darajasiga {needed} ta g'alaba kerak"
    return None


# ─── Yuklash / saqlash ───────────────────────────────────────
def _load() -> dict:
    if not os.path.exists(DB_PATH):
        _save({"users": {}, "games": {}, "states": {}, "daily": {}})
    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "daily" not in data:
        data["daily"] = {}
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
        }
    else:
        u = db["users"][key]
        u["first_name"] = first_name or u["first_name"]
        u["last_name"]  = last_name  or u["last_name"]
        u["username"]   = username   or u["username"]
    _save(db)
    return is_new

def get_all_users() -> list:
    db = _load()
    return sorted(db["users"].values(), key=lambda u: u["wins"], reverse=True)

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
    db["games"] = {}
    for u in db["users"].values():
        u["total_games"]    = 0
        u["wins"]           = 0
        u["losses"]         = 0
        u["total_attempts"] = 0
        u["best_score"]     = None
        u["bonus_wins"]     = 0
    db["daily"] = {}
    _save(db)


# ─── Statistika ──────────────────────────────────────────────
def get_user_stats(user_id: int) -> dict | None:
    db = _load()
    u  = db["users"].get(str(user_id))
    if not u:
        return None
    avg = round(u["total_attempts"] / u["wins"], 1) if u["wins"] > 0 else None
    return {
        **u,
        "avg_attempts": avg,
        "rank":         get_rank(u["wins"]),
        "next_rank":    get_next_rank_info(u["wins"]),
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
    return {
        "total_users":   len(users),
        "banned_count":  banned_count,
        "total_games":   total_games,
        "total_wins":    total_wins,
        "total_losses":  total_losses,
        "win_rate":      win_rate,
        "avg_attempts":  avg,
        "today_games":   today_data.get("games", 0),
        "today_wins":    today_data.get("wins",  0),
        "today_players": len(today_data.get("players", [])),
    }

def get_leaderboard(limit: int = 10) -> list:
    db    = _load()
    users = [u for u in db["users"].values() if u["wins"] > 0 and not u.get("banned")]
    users.sort(key=lambda u: (
        -u["wins"],
        u["total_attempts"] / u["wins"] if u["wins"] > 0 else 99,
    ))
    result = []
    for u in users[:limit]:
        avg = round(u["total_attempts"] / u["wins"], 1) if u["wins"] > 0 else "—"
        result.append({**u, "avg_attempts": avg, "rank": get_rank(u["wins"])})
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
