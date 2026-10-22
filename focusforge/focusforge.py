#!/usr/bin/env python3
"""
FocusForge - Personal Productivity & Task Tracking Dashboard
"""
import os
import sys
import re
import sqlite3
import argparse
import subprocess
from datetime import datetime, date, timedelta

DB_DIR = os.path.expanduser("~/.local/share/focusforge")
DB_PATH = os.path.join(DB_DIR, "focusforge.db")

# Colors for terminal output
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"

def disp_len(s):
    clean = re.sub(r"\033\[[0-9;]*m", "", s)
    length = 0
    for ch in clean:
        if ch in ("\ufe0f", "\ufe0e"):
            continue
        if ord(ch) > 0x2000 and (ord(ch) >= 0x1f300 or ord(ch) in (0x26a1, 0x2705)):
            length += 2
        else:
            length += 1
    return length

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_date TEXT,
            due_date TEXT,
            goal_tag TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Check if start_date column exists (schema migration)
    cur.execute("PRAGMA table_info(tasks)")
    cols = [r[1] for r in cur.fetchall()]
    if "start_date" not in cols:
        cur.execute("ALTER TABLE tasks ADD COLUMN start_date TEXT")
        cur.execute("UPDATE tasks SET start_date = date(created_at) WHERE start_date IS NULL")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            period TEXT DEFAULT 'weekly',
            target_count INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS media_usage (
            date TEXT PRIMARY KEY,
            youtube_seconds INTEGER DEFAULT 0,
            blocked INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_connection():
    init_db()
    return sqlite3.connect(DB_PATH)

def notify_widget_reload():
    """Signals conky to refresh immediately upon database modifications."""
    try:
        subprocess.run(["pkill", "-USR1", "-x", "conky"], check=False)
    except Exception:
        pass

def parse_date_arg(val):
    if not val:
        return None
    today = date.today()
    lower = val.strip().lower()
    if lower in ("today", "t"):
        return today.isoformat()
    elif lower in ("tomorrow", "tom"):
        return (today + timedelta(days=1)).isoformat()
    elif lower in ("yesterday", "yest"):
        return (today - timedelta(days=1)).isoformat()
    else:
        try:
            return datetime.strptime(val, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return val

def add_task(title, due=None, start=None, goal=None):
    today_str = date.today().isoformat()
    parsed_start = parse_date_arg(start) or today_str
    parsed_due = parse_date_arg(due)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks (title, start_date, due_date, goal_tag) VALUES (?, ?, ?, ?)",
                (title, parsed_start, parsed_due, goal))
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    notify_widget_reload()
    
    msg = f"{GREEN}✓ Task #{task_id} added:{RESET} {BOLD}{title}{RESET}"
    msg += f" {DIM}(Started: {parsed_start}){RESET}"
    if parsed_due:
        msg += f" {YELLOW}(Due: {parsed_due}){RESET}"
    print(msg)

def edit_task(task_id, title=None, due=None, start=None, goal=None):
    parsed_due = parse_date_arg(due) if due is not None else None
    parsed_start = parse_date_arg(start) if start is not None else None

    conn = get_connection()
    cur = conn.cursor()
    updates = []
    params = []
    if title:
        updates.append("title = ?")
        params.append(title)
    if start is not None:
        updates.append("start_date = ?")
        params.append(parsed_start)
    if due is not None:
        updates.append("due_date = ?")
        params.append(parsed_due)
    if goal is not None:
        updates.append("goal_tag = ?")
        params.append(goal)

    if not updates:
        print(f"{YELLOW}No updates specified. Use --title, --start, --due, or --goal.{RESET}")
        conn.close()
        return

    params.append(task_id)
    cur.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
    if cur.rowcount > 0:
        conn.commit()
        notify_widget_reload()
        print(f"{GREEN}✓ Task #{task_id} updated successfully!{RESET}")
    else:
        print(f"{RED}Task #{task_id} not found.{RESET}")
    conn.close()

def complete_task(task_id):
    conn = get_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?", (now_iso, task_id))
    if cur.rowcount > 0:
        conn.commit()
        notify_widget_reload()
        print(f"{GREEN}✓ Task #{task_id} marked as completed!{RESET}")
    else:
        print(f"{RED}Task #{task_id} not found.{RESET}")
    conn.close()

def delete_task(task_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    if cur.rowcount > 0:
        conn.commit()
        notify_widget_reload()
        print(f"{YELLOW}Task #{task_id} deleted.{RESET}")
    else:
        print(f"{RED}Task #{task_id} not found.{RESET}")
    conn.close()

def add_goal(title, period="weekly"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO goals (title, period) VALUES (?, ?)", (title, period))
    goal_id = cur.lastrowid
    conn.commit()
    conn.close()
    notify_widget_reload()
    print(f"{GREEN}✓ Goal #{goal_id} added:{RESET} {BOLD}{title}{RESET} ({period})")

def list_goals():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, period FROM goals ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print(f"{DIM}No active goals set. Use `focusforge goal add \"Your goal\"`{RESET}")
        return
    print(f"{BOLD}{MAGENTA}🎯 Active Goals:{RESET}")
    for gid, title, period in rows:
        print(f"  {CYAN}#{gid}{RESET} [{period}] {BOLD}{title}{RESET}")

def get_today_youtube_usage():
    today_str = date.today().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT youtube_seconds, blocked FROM media_usage WHERE date = ?", (today_str,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return 0, False
    return row[0], bool(row[1])

def format_timing_badge(start_d, due_d, today_obj):
    parts = []
    if due_d:
        try:
            d_obj = datetime.strptime(due_d, "%Y-%m-%d").date()
            diff = (d_obj - today_obj).days
            if diff < 0:
                parts.append(f"{RED}{BOLD}OVERDUE {abs(diff)}d!{RESET}")
            elif diff == 0:
                parts.append(f"{RED}Due: Today{RESET}")
            elif diff == 1:
                parts.append(f"{YELLOW}Due: Tomorrow{RESET}")
            else:
                parts.append(f"{YELLOW}Due: {d_obj.strftime('%b %d')}{RESET}")
        except Exception:
            parts.append(f"{YELLOW}Due: {due_d}{RESET}")

    if start_d:
        try:
            s_obj = datetime.strptime(start_d, "%Y-%m-%d").date()
            parts.append(f"{DIM}Started: {s_obj.strftime('%b %d')}{RESET}")
        except Exception:
            parts.append(f"{DIM}Started: {start_d}{RESET}")

    return f" ({' | '.join(parts)})" if parts else ""

def format_conky_badge(start_d, due_d, today_obj):
    parts = []
    if due_d:
        try:
            d_obj = datetime.strptime(due_d, "%Y-%m-%d").date()
            diff = (d_obj - today_obj).days
            if diff < 0:
                parts.append(f"${{color #ff5555}}OVERDUE {abs(diff)}d!${{color}}")
            elif diff == 0:
                parts.append(f"${{color #ff5555}}Due Today${{color}}")
            elif diff == 1:
                parts.append(f"${{color #f1fa8c}}Due Tomorrow${{color}}")
            else:
                parts.append(f"${{color #f1fa8c}}Due {d_obj.strftime('%b %d')}${{color}}")
        except Exception:
            parts.append(f"${{color #f1fa8c}}Due {due_d}${{color}}")

    if start_d:
        try:
            s_obj = datetime.strptime(start_d, "%Y-%m-%d").date()
            parts.append(f"${{color #6272a4}}Start: {s_obj.strftime('%b %d')}${{color}}")
        except Exception:
            parts.append(f"${{color #6272a4}}Start: {start_d}${{color}}")

    return f" ({' | '.join(parts)})" if parts else ""

def show_dashboard():
    today = date.today()
    today_str = today.isoformat()
    now_formatted = datetime.now().strftime("%a, %b %d, %Y")

    conn = get_connection()
    cur = conn.cursor()

    # Active pending tasks (ordered by urgency: overdue -> today -> future -> ongoing)
    cur.execute("""
        SELECT id, title, start_date, due_date, goal_tag FROM tasks
        WHERE completed = 0
        ORDER BY 
            CASE 
                WHEN due_date IS NOT NULL AND due_date < ? THEN 0
                WHEN due_date = ? THEN 1
                WHEN due_date IS NOT NULL THEN 2
                ELSE 3 
            END,
            due_date ASC,
            start_date ASC
    """, (today_str, today_str))
    pending = cur.fetchall()

    # Completed today
    cur.execute("""
        SELECT count(*) FROM tasks
        WHERE completed = 1 AND date(completed_at) = ?
    """, (today_str,))
    completed_today_count = cur.fetchone()[0]

    # Goals
    cur.execute("SELECT id, title, period FROM goals ORDER BY id ASC")
    goals = cur.fetchall()

    conn.close()

    yt_secs, yt_blocked = get_today_youtube_usage()
    yt_mins = yt_secs // 60

    width = 56
    line = "─" * width

    def print_box_row(content, style=""):
        dlen = disp_len(content)
        pad = max(0, width - 2 - dlen)
        print(f"{BOLD}{CYAN}│{RESET} {style}{content}{RESET}" + " " * pad + f"{BOLD}{CYAN}│{RESET}")

    print(f"\n{BOLD}{CYAN}┌{line}┐{RESET}")
    header_text = f"🎯 FOCUSFORGE • {now_formatted}"
    header_dlen = disp_len(header_text)
    left_pad = max(0, (width - header_dlen) // 2)
    right_pad = max(0, width - header_dlen - left_pad)
    print(f"{BOLD}{CYAN}│{RESET}" + " " * left_pad + f"{BOLD}{header_text}{RESET}" + " " * right_pad + f"{BOLD}{CYAN}│{RESET}")
    print(f"{BOLD}{CYAN}├{line}┤{RESET}")

    # Goals section
    if goals:
        print_box_row(f"{BOLD}{MAGENTA}🌟 KEY GOALS{RESET}")
        for _, gtitle, period in goals[:3]:
            g_disp = f" • ({period}) {gtitle}"
            if len(g_disp) > width - 4:
                g_disp = g_disp[:width - 7] + "..."
            print_box_row(g_disp, DIM)
        print_box_row("")

    # Tasks section
    print_box_row(f"{BOLD}{YELLOW}📋 TASKS & DEADLINES{RESET}")
    if not pending:
        print_box_row(' No pending tasks! Add with: focusforge add "..."', GREEN)
    else:
        for tid, title, start_d, due_d, goal in pending:
            status_box = "[ ]"
            timing_badge = format_timing_badge(start_d, due_d, today)
            
            clean_prefix = f" #{tid} {status_box} "
            clean_title = title
            # Calculate visible length
            row_raw_len = len(clean_prefix) + len(clean_title) + disp_len(timing_badge)
            if row_raw_len > width - 4:
                avail = width - 4 - len(clean_prefix) - disp_len(timing_badge)
                clean_title = clean_title[:max(8, avail)] + "…"

            task_line = f" {CYAN}#{tid}{RESET} [ ] {BOLD}{clean_title}{RESET}{timing_badge}"
            print_box_row(task_line)

    print(f"{BOLD}{CYAN}├{line}┤{RESET}")

    # Quick Commands section
    print_box_row(f"{BOLD}{MAGENTA}⚡ QUICK COMMANDS{RESET}")
    cmds = [
        ('focusforge add "task" -d today -s today', 'Add task'),
        ('focusforge edit <id> -t "..."', 'Edit task'),
        ('focusforge done <id>', 'Complete'),
    ]
    for c, _ in cmds:
        print_box_row(f" • {c}", DIM)

    print(f"{BOLD}{CYAN}├{line}┤{RESET}")

    # YouTube usage summary
    yt_color = GREEN if yt_mins < 10 else (YELLOW if yt_mins < 20 else RED)
    yt_status = f"{yt_color}{yt_mins}/20 mins used{RESET}"
    if yt_blocked:
        yt_status += f" {RED}{BOLD}[LOCKED]{RESET}"

    status_line = f"⏱️  YouTube: {yt_status}  |  ✓ Done Today: {GREEN}{completed_today_count}{RESET}"
    print_box_row(status_line)

    print(f"{BOLD}{CYAN}└{line}┘{RESET}\n")

def show_conky():
    today = date.today()
    today_str = today.isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, start_date, due_date FROM tasks
        WHERE completed = 0
        ORDER BY 
            CASE 
                WHEN due_date IS NOT NULL AND due_date < ? THEN 0
                WHEN due_date = ? THEN 1
                WHEN due_date IS NOT NULL THEN 2
                ELSE 3 
            END,
            due_date ASC,
            start_date ASC
        LIMIT 8
    """, (today_str, today_str))
    pending = cur.fetchall()

    cur.execute("SELECT title, period FROM goals ORDER BY id ASC LIMIT 3")
    goals = cur.fetchall()
    conn.close()

    yt_secs, yt_blocked = get_today_youtube_usage()
    yt_mins = yt_secs // 60

    print("${color #00ffff}${font :bold:size=14}🎯 FOCUSFORGE${font}${color}")
    print("${color #50fa7b}${font :bold:size=10}▶ Click widget to launch Konsole${font}${color}")
    print("${hr 1}")
    if goals:
        print("${color #ff79c6}${font :bold:size=11}🌟 KEY GOALS:${font}${color}")
        for gtitle, period in goals:
            print(f" • {gtitle} ({period})")
        print("")

    print("${color #f1fa8c}${font :bold:size=11}📋 TASKS & DEADLINES:${font}${color}")
    if not pending:
        print(" ${color #50fa7b}All tasks completed!${color}")
    else:
        for tid, title, start_d, due_d in pending:
            conky_badge = format_conky_badge(start_d, due_d, today)
            print(f" [ ] #{tid} {title[:30]}" + conky_badge)

    print("${hr 1}")
    yt_status = f"{yt_mins}/20 min" + (" ${color #ff5555}[LOCKED]${color}" if yt_blocked else "")
    print(f"⏱️ YouTube: {yt_status}")
    print("${hr 1}")
    print("${color #bd93f9}${font :bold:size=10}⚡ QUICK COMMANDS:${font}${color}")
    print("${color #8be9fd}• Add:${color} focusforge add \"task\" -d today")
    print("${color #8be9fd}• Edit:${color} focusforge edit <id> -t \"new name\"")
    print("${color #8be9fd}• Done:${color} focusforge done <id>")

def main():
    parser = argparse.ArgumentParser(description="FocusForge - Task & Habit Guardian")
    subparsers = parser.add_subparsers(dest="command")

    # add
    p_add = subparsers.add_parser("add", help="Add a task")
    p_add.add_argument("title", type=str, help="Task description")
    p_add.add_argument("--due", "-d", type=str, default=None, help="Due date (today, tomorrow, YYYY-MM-DD)")
    p_add.add_argument("--start", "-s", type=str, default=None, help="Start date (defaults to today, YYYY-MM-DD)")
    p_add.add_argument("--goal", "-g", type=str, default=None, help="Goal category or tag")

    # edit
    p_edit = subparsers.add_parser("edit", help="Edit an existing task")
    p_edit.add_argument("id", type=int, help="Task ID")
    p_edit.add_argument("--title", "-t", type=str, default=None, help="New task title")
    p_edit.add_argument("--due", "-d", type=str, default=None, help="New due date (today, tomorrow, YYYY-MM-DD)")
    p_edit.add_argument("--start", "-s", type=str, default=None, help="New start date (today, YYYY-MM-DD)")
    p_edit.add_argument("--goal", "-g", type=str, default=None, help="New goal tag")

    # done
    p_done = subparsers.add_parser("done", help="Mark task completed")
    p_done.add_argument("id", type=int, help="Task ID")

    # rm
    p_rm = subparsers.add_parser("rm", help="Delete task")
    p_rm.add_argument("id", type=int, help="Task ID")

    # goal
    p_goal = subparsers.add_parser("goal", help="Manage overarching goals")
    p_goal_sub = p_goal.add_subparsers(dest="goal_command")
    p_g_add = p_goal_sub.add_parser("add", help="Add a goal")
    p_g_add.add_argument("title", type=str, help="Goal description")
    p_g_add.add_argument("--period", "-p", choices=["daily", "weekly", "monthly"], default="weekly")
    p_goal_sub.add_parser("list", help="List goals")

    # status / show / conky
    subparsers.add_parser("show", help="Show dashboard")
    subparsers.add_parser("list", help="Show dashboard")
    subparsers.add_parser("conky", help="Output formatted for desktop Conky widget")

    args = parser.parse_args()

    if args.command == "add":
        add_task(args.title, args.due, args.start, args.goal)
    elif args.command == "edit":
        edit_task(args.id, args.title, args.due, args.start, args.goal)
    elif args.command == "done":
        complete_task(args.id)
    elif args.command == "rm":
        delete_task(args.id)
    elif args.command == "goal":
        if args.goal_command == "add":
            add_goal(args.title, args.period)
        else:
            list_goals()
    elif args.command == "conky":
        show_conky()
    else:
        show_dashboard()


if __name__ == "__main__":
    main()
