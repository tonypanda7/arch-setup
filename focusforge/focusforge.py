#!/usr/bin/env python3
"""
FocusForge - Personal Productivity & Task Tracking Dashboard
"""
import os
import sys
import sqlite3
import argparse
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

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT,
            goal_tag TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
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

def add_task(title, due=None, goal=None):
    parsed_due = None
    today = date.today()
    if due:
        lower = due.strip().lower()
        if lower in ("today", "t"):
            parsed_due = today.isoformat()
        elif lower in ("tomorrow", "tom"):
            parsed_due = (today + timedelta(days=1)).isoformat()
        else:
            try:
                parsed_due = datetime.strptime(due, "%Y-%m-%d").date().isoformat()
            except ValueError:
                parsed_due = due

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks (title, due_date, goal_tag) VALUES (?, ?, ?)",
                (title, parsed_due, goal))
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"{GREEN}✓ Task #{task_id} added:{RESET} {BOLD}{title}{RESET}" +
          (f" {YELLOW}(Due: {parsed_due}){RESET}" if parsed_due else ""))

def edit_task(task_id, title=None, due=None, goal=None):
    today = date.today()
    parsed_due = None
    if due:
        lower = due.strip().lower()
        if lower in ("today", "t"):
            parsed_due = today.isoformat()
        elif lower in ("tomorrow", "tom"):
            parsed_due = (today + timedelta(days=1)).isoformat()
        else:
            try:
                parsed_due = datetime.strptime(due, "%Y-%m-%d").date().isoformat()
            except ValueError:
                parsed_due = due

    conn = get_connection()
    cur = conn.cursor()
    updates = []
    params = []
    if title:
        updates.append("title = ?")
        params.append(title)
    if due is not None:
        updates.append("due_date = ?")
        params.append(parsed_due)
    if goal is not None:
        updates.append("goal_tag = ?")
        params.append(goal)

    if not updates:
        print(f"{YELLOW}No updates specified. Use --title, --due, or --goal.{RESET}")
        conn.close()
        return

    params.append(task_id)
    cur.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
    if cur.rowcount > 0:
        conn.commit()
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

def show_dashboard():
    today = date.today()
    today_str = today.isoformat()
    now_formatted = datetime.now().strftime("%a, %b %d, %Y")

    conn = get_connection()
    cur = conn.cursor()

    # Pending tasks
    cur.execute("""
        SELECT id, title, due_date, goal_tag FROM tasks
        WHERE completed = 0
        ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC
    """)
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

    width = 54
    line = "─" * width

    print(f"\n{BOLD}{CYAN}┌{line}┐{RESET}")
    header_text = f"🎯 FOCUSFORGE • {now_formatted}"
    print(f"{BOLD}{CYAN}│{RESET} {BOLD}{header_text.center(width - 2)}{RESET} {BOLD}{CYAN}│{RESET}")
    print(f"{BOLD}{CYAN}├{line}┤{RESET}")

    # Goals section
    if goals:
        print(f"{BOLD}{CYAN}│{RESET} {BOLD}{MAGENTA}🌟 KEY GOALS{RESET}" + " " * (width - 13) + f"{BOLD}{CYAN}│{RESET}")
        for _, gtitle, period in goals[:3]:
            g_disp = f"  • ({period}) {gtitle}"
            if len(g_disp) > width - 4:
                g_disp = g_disp[:width - 7] + "..."
            padding = width - 2 - len(g_disp)
            print(f"{BOLD}{CYAN}│{RESET}{DIM}{g_disp}{RESET}" + " " * padding + f"{BOLD}{CYAN}│{RESET}")
        print(f"{BOLD}{CYAN}│{RESET}" + " " * (width - 2) + f"{BOLD}{CYAN}│{RESET}")

    # Tasks section
    print(f"{BOLD}{CYAN}│{RESET} {BOLD}{YELLOW}📋 TASKS & DEADLINES{RESET}" + " " * (width - 22) + f"{BOLD}{CYAN}│{RESET}")
    if not pending:
        msg = "  No pending tasks! Add one with: focusforge add \"...\""
        padding = max(0, width - 2 - len(msg))
        print(f"{BOLD}{CYAN}│{RESET}{GREEN}{msg}{RESET}" + " " * padding + f"{BOLD}{CYAN}│{RESET}")
    else:
        for tid, title, due, goal in pending:
            status_box = "[ ]"
            due_str = ""
            if due:
                if due == today_str:
                    due_str = f" {RED}(Due: Today){RESET}"
                else:
                    due_str = f" {YELLOW}(Due: {due}){RESET}"

            clean_line = f"  #{tid} {status_box} {title}"
            raw_len = len(f"  #{tid} {status_box} {title}") + (len(f" (Due: {due})") if due else 0)
            if raw_len > width - 4:
                avail = width - 4 - (len(f"  #{tid} {status_box} ") + (len(f" (Due: {due})") if due else 0))
                title = title[:max(10, avail)] + "…"
                raw_len = len(f"  #{tid} {status_box} {title}") + (len(f" (Due: {due})") if due else 0)

            padding = max(0, width - 2 - raw_len)
            print(f"{BOLD}{CYAN}│{RESET}  {CYAN}#{tid}{RESET} [ ] {BOLD}{title}{RESET}{due_str}" + " " * padding + f"{BOLD}{CYAN}│{RESET}")

    print(f"{BOLD}{CYAN}├{line}┤{RESET}")

    # YouTube usage summary
    yt_color = GREEN if yt_mins < 10 else (YELLOW if yt_mins < 20 else RED)
    yt_status = f"{yt_color}{yt_mins}/20 mins used{RESET}"
    if yt_blocked:
        yt_status += f" {RED}{BOLD}[LOCKED]{RESET}"

    status_line = f"  ⏱️  YouTube: {yt_status}  |  ✓ Done Today: {GREEN}{completed_today_count}{RESET}"
    # Approximate visible length
    vis_len = len(f"  ⏱️  YouTube: {yt_mins}/20 mins used" + (" [LOCKED]" if yt_blocked else "") + f"  |  ✓ Done Today: {completed_today_count}")
    padding = max(0, width - 2 - vis_len)
    print(f"{BOLD}{CYAN}│{RESET}{status_line}" + " " * padding + f"{BOLD}{CYAN}│{RESET}")

    print(f"{BOLD}{CYAN}└{line}┘{RESET}\n")

def show_conky():
    today = date.today()
    today_str = today.isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, due_date FROM tasks
        WHERE completed = 0
        ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC
        LIMIT 6
    """)
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
        for tid, title, due in pending:
            due_tag = ""
            if due == today_str:
                due_tag = " ${color #ff5555}(Today)${color}"
            elif due:
                due_tag = f" ${{color #f1fa8c}}({due})${{color}}"
            print(f" [ ] #{tid} {title[:36]}" + due_tag)

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
    p_add.add_argument("--goal", "-g", type=str, default=None, help="Goal category or tag")

    # edit
    p_edit = subparsers.add_parser("edit", help="Edit an existing task")
    p_edit.add_argument("id", type=int, help="Task ID")
    p_edit.add_argument("--title", "-t", type=str, default=None, help="New task title")
    p_edit.add_argument("--due", "-d", type=str, default=None, help="New due date (today, tomorrow, YYYY-MM-DD)")
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
        add_task(args.title, args.due, args.goal)
    elif args.command == "edit":
        edit_task(args.id, args.title, args.due, args.goal)
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
