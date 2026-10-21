# 🎯 FocusForge — Terminal Productivity & Habit Enforcer

FocusForge is a lightweight, zero-dependency Python + SQLite dashboard designed to keep your goals, tasks, and deadlines front and center every time you open a terminal.

## Features
- **Zero external dependencies:** Pure Python standard library with SQLite and ANSI styling.
- **Terminal Greeter:** Displays active goals, pending tasks, deadlines, and daily YouTube limit every time you start a bash session.
- **Goal & Task Management:** Fast CLI commands to add, complete, and track tasks.

## Installation
```bash
cd focusforge
chmod +x install.sh
./install.sh
```

Ensure `~/.local/bin` is in your `$PATH`.

## Usage
```bash
# Add overarching goals
focusforge goal add "Master Machine Learning" --period weekly
focusforge goal list

# Add tasks with deadlines
focusforge add "Finish ML Assignment" --due today
focusforge add "Read Chapter 4" --due tomorrow
focusforge add "Project Milestone" --due 2026-11-01

# View dashboard
focusforge

# Mark task as completed
focusforge done 1

# Delete a task
focusforge rm 2
```
