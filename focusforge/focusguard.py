#!/usr/bin/env python3
"""
FocusGuard - Anti-Doomscroll Agent for Arch Linux / KDE Plasma
Monitors YouTube media via MPRIS (playerctl), classifies videos with local Ollama LLM,
and enforces hard session and daily time limits.
"""
import os
import sys
import time
import json
import sqlite3
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, date

SESSION_LIMIT_SECONDS = 10 * 60   # 10 minutes per session
DAILY_LIMIT_SECONDS = 20 * 60     # 20 minutes daily total
CHECK_INTERVAL_SECONDS = 5
PAUSE_RESET_THRESHOLD = 120       # 2 minutes of pause resets the session timer

DB_DIR = os.path.expanduser("~/.local/share/focusforge")
DB_PATH = os.path.join(DB_DIR, "focusforge.db")
LOG_PATH = os.path.join(DB_DIR, "focusguard.log")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLOCK_SCRIPT = os.path.join(SCRIPT_DIR, "focusguard-block")
UNBLOCK_SCRIPT = os.path.join(SCRIPT_DIR, "focusguard-unblock")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def send_notification(title, message, urgency="normal"):
    try:
        subprocess.run([
            "notify-send",
            "-a", "FocusGuard",
            "-u", urgency,
            "-i", "dialog-warning" if urgency == "critical" else "preferences-system-time",
            title,
            message
        ], check=False)
    except Exception as e:
        log(f"Notification error: {e}")

def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS media_usage (
            date TEXT PRIMARY KEY,
            youtube_seconds INTEGER DEFAULT 0,
            blocked INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS video_cache (
            id_key TEXT PRIMARY KEY,
            title TEXT,
            channel TEXT,
            is_educational INTEGER,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def get_today_usage():
    today_str = date.today().isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT youtube_seconds, blocked FROM media_usage WHERE date = ?", (today_str,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return 0, False
    return row[0], bool(row[1])

def update_today_usage(added_seconds, set_blocked=None):
    today_str = date.today().isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT youtube_seconds, blocked FROM media_usage WHERE date = ?", (today_str,))
    row = cur.fetchone()
    if not row:
        new_secs = added_seconds
        new_blocked = 1 if set_blocked else 0
        cur.execute("INSERT INTO media_usage (date, youtube_seconds, blocked) VALUES (?, ?, ?)",
                    (today_str, new_secs, new_blocked))
    else:
        new_secs = row[0] + added_seconds
        new_blocked = (1 if set_blocked else row[1]) if set_blocked is not None else row[1]
        cur.execute("UPDATE media_usage SET youtube_seconds = ?, blocked = ? WHERE date = ?",
                    (new_secs, new_blocked, today_str))
    conn.commit()
    conn.close()
    return new_secs, bool(new_blocked)

def get_cached_classification(key):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT is_educational, reason FROM video_cache WHERE id_key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row:
        return bool(row[0]), row[1]
    return None

def save_cached_classification(key, title, channel, is_educational, reason):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO video_cache (id_key, title, channel, is_educational, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (key, title, channel, 1 if is_educational else 0, reason))
    conn.commit()
    conn.close()

def classify_video_with_ollama(title, channel):
    prompt = f"""You are a strict anti-doomscroll productivity filter.
Determine if the following YouTube video is productive/educational (e.g. computer science, coding, academic, science, tutorial, professional skill, lecture, documentary) OR entertainment/doomscrolling (e.g. gaming, memes, vlogs, gossip, shorts, reaction, clickbait, comedy).

Video Title: {title}
Channel: {channel}

Respond with ONLY valid JSON with keys:
"is_educational": true or false,
"reason": "short explanation"
"""
    data = json.dumps({
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            parsed = json.loads(body.get("response", "{}"))
            return parsed.get("is_educational", False), parsed.get("reason", "No reason provided")
    except Exception as e:
        log(f"Ollama classification failed: {e}. Defaulting to non-educational for safety.")
        return False, "Ollama query failed"

def get_firefox_media_info():
    """Queries playerctl for Firefox MPRIS player status and metadata."""
    try:
        status_proc = subprocess.run(
            ["playerctl", "--player=firefox", "status"],
            capture_output=True, text=True, check=False
        )
        status = status_proc.stdout.strip()
        if not status:
            return None

        # Fetch metadata
        meta_proc = subprocess.run([
            "playerctl", "--player=firefox", "metadata",
            "--format", "{{xesam:url}}\n{{xesam:title}}\n{{xesam:artist}}"
        ], capture_output=True, text=True, check=False)

        lines = [line.strip() for line in meta_proc.stdout.strip().split("\n")]
        url = lines[0] if len(lines) > 0 else ""
        title = lines[1] if len(lines) > 1 else ""
        channel = lines[2] if len(lines) > 2 else ""

        return {
            "status": status,
            "url": url,
            "title": title,
            "channel": channel,
            "is_youtube": ("youtube.com" in url or "youtu.be" in url)
        }
    except Exception as e:
        return None

def pause_youtube():
    try:
        subprocess.run(["playerctl", "--player=firefox", "pause"], check=False)
    except Exception:
        pass

def enforce_hard_block():
    log("Enforcing hard block on YouTube.")
    pause_youtube()
    try:
        subprocess.run(["sudo", "-n", BLOCK_SCRIPT], check=False)
    except Exception as e:
        log(f"Failed to execute block script: {e}")

def lift_hard_block():
    log("Lifting hard block on YouTube.")
    try:
        subprocess.run(["sudo", "-n", UNBLOCK_SCRIPT], check=False)
    except Exception as e:
        log(f"Failed to execute unblock script: {e}")

def main_loop():
    log("FocusGuard daemon started. Monitoring Firefox media...")
    current_date = date.today()
    session_seconds = 0
    paused_seconds = 0
    last_notified_video = None
    warning_8min_sent = False
    warning_18min_sent = False

    while True:
        try:
            today = date.today()
            if today != current_date:
                log("New day detected! Resetting daily stats.")
                current_date = today
                session_seconds = 0
                paused_seconds = 0
                warning_8min_sent = False
                warning_18min_sent = False
                lift_hard_block()

            daily_seconds, is_blocked = get_today_usage()

            info = get_firefox_media_info()

            if is_blocked:
                if info and info.get("is_youtube") and info.get("status") == "Playing":
                    pause_youtube()
                    send_notification(
                        "🛑 YouTube is Locked!",
                        "You reached your limit for today. YouTube remains blocked.",
                        urgency="critical"
                    )
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue

            if not info or not info.get("is_youtube"):
                paused_seconds += CHECK_INTERVAL_SECONDS
                if paused_seconds >= PAUSE_RESET_THRESHOLD:
                    if session_seconds > 0:
                        log(f"Playback paused for {paused_seconds}s. Resetting session counter.")
                        session_seconds = 0
                        warning_8min_sent = False
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue

            # YouTube media is present
            if info["status"] != "Playing":
                paused_seconds += CHECK_INTERVAL_SECONDS
                if paused_seconds >= PAUSE_RESET_THRESHOLD:
                    if session_seconds > 0:
                        log(f"YouTube paused for {paused_seconds}s. Resetting session counter.")
                        session_seconds = 0
                        warning_8min_sent = False
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue

            # Active YouTube video playing!
            paused_seconds = 0
            video_key = info["url"] if info["url"] else info["title"]

            cached = get_cached_classification(video_key)
            if cached is not None:
                is_educational, reason = cached
            else:
                log(f"Classifying new video: '{info['title']}' by '{info['channel']}'...")
                is_educational, reason = classify_video_with_ollama(info["title"], info["channel"])
                save_cached_classification(video_key, info["title"], info["channel"], is_educational, reason)
                log(f"Result: Educational={is_educational} | Reason: {reason}")

            if is_educational:
                if last_notified_video != video_key:
                    send_notification(
                        "🎓 Educational Video Allowed",
                        f"{info['title'][:40]}...\nReason: {reason}",
                        urgency="low"
                    )
                    last_notified_video = video_key
                # Educational videos do not consume the doomscroll budget!
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue

            # Non-educational / Doomscroll video!
            session_seconds += CHECK_INTERVAL_SECONDS
            daily_seconds, _ = update_today_usage(CHECK_INTERVAL_SECONDS)

            sess_mins = session_seconds // 60
            daily_mins = daily_seconds // 60

            # 8 minute session warning
            if session_seconds >= 8 * 60 and not warning_8min_sent:
                send_notification(
                    "⚠️ Doomscroll Session Warning",
                    f"You have been watching for {sess_mins}m! YouTube locks at 10m.",
                    urgency="normal"
                )
                warning_8min_sent = True

            # 18 minute daily warning
            if daily_seconds >= 18 * 60 and not warning_18min_sent:
                send_notification(
                    "⚠️ Daily YouTube Limit Warning",
                    f"You have used {daily_mins}m of your 20m daily allowance!",
                    urgency="normal"
                )
                warning_18min_sent = True

            # Check limits breach
            if session_seconds >= SESSION_LIMIT_SECONDS or daily_seconds >= DAILY_LIMIT_SECONDS:
                reason_str = "10 min session limit reached" if session_seconds >= SESSION_LIMIT_SECONDS else "20 min daily limit reached"
                log(f"LIMIT BREACH: {reason_str}! Locking YouTube.")
                update_today_usage(0, set_blocked=True)
                enforce_hard_block()
                send_notification(
                    "🛑 DOOMSCROLL DETECTED — YOUTUBE LOCKED",
                    f"{reason_str} on non-educational content.\nGet back to your goals!",
                    urgency="critical"
                )

        except Exception as e:
            log(f"Error in main loop: {e}")

        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()
