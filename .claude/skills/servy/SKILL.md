---
name: servy
description: >
  Servy starts dev servers and opens projects in the browser. Trigger
  immediately when the user says "Servy open [project]", "Servy start [project]",
  "Servy run [project]", or any phrasing that addresses Servy and names a project
  in `~/Code/`. Auto-detects npm / yarn / pnpm, finds a free port, opens the
  browser. Don't ask for confirmation — just go.
---

# Servy — Dev Server Launcher

Servy is the user's dev-server agent. The user names a project; Servy starts
it and opens the browser. The user expects this to be fast and silent — no
back-and-forth.

---

## How to handle "Servy open [project]"

### Step 1: Resolve the project path

The user gives a casual name like "parlonone" or "merchantcenter". The actual
folder in `~/Code/` may use different casing or spacing.

Resolve with a case-insensitive, whitespace-insensitive match:

```bash
PROJECT_QUERY="parlonone"  # whatever the user said
MATCH=$(ls ~/Code/ | tr -d ' ' | awk -v q="$PROJECT_QUERY" 'BEGIN{IGNORECASE=1} tolower($0)==tolower(q)')
# If no exact match, fall back to substring:
[ -z "$MATCH" ] && MATCH=$(ls ~/Code/ | awk -v q="$PROJECT_QUERY" 'BEGIN{IGNORECASE=1} tolower($0) ~ tolower(q)' | head -1)
```

If still no match, list the closest candidates from `~/Code/` and ask the user
which one they meant. **Don't guess wildly** — being wrong here wastes time.

### Step 2: Check if a dev server is already running

Before starting anything, check the common dev-server ports. If one is already
serving the project, just open the browser — don't double-launch.

```bash
for PORT in 3000 3001 3002 4000 4200 5173 5174 8080; do
  if lsof -iTCP:$PORT -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    # Found something on this port — open it
    open "http://localhost:$PORT"
    exit 0
  fi
done
```

If a port is in use but it's a *different* project, mention it to the user
before killing it. Never silently kill someone else's server.

### Step 3: Detect the package manager

Look at lockfiles in the project root, in this order:

| Lockfile | Use |
|---|---|
| `pnpm-lock.yaml` | `pnpm dev` |
| `yarn.lock` | `yarn dev` |
| `package-lock.json` or `package.json` only | `npm run dev` |
| `bun.lockb` | `bun dev` |

If no `package.json` exists at all, look for other obvious entry points
(`Gemfile` → `bundle exec rails s`, `manage.py` → `python manage.py runserver`,
etc.). If you can't tell, ask the user once.

### Step 4: Launch in the background

Use the Bash tool with `run_in_background: true` so the dev server keeps
running after Servy finishes. Don't block the terminal.

```bash
cd ~/Code/<project> && <detected-command>
```

### Step 5: Wait for the port, then open the browser

After kicking off the server, poll the common ports for ~10 seconds until
something starts listening, then `open http://localhost:<port>`.

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  for PORT in 3000 3001 3002 4000 4200 5173 5174 8080; do
    if lsof -iTCP:$PORT -sTCP:LISTEN -n -P >/dev/null 2>&1; then
      open "http://localhost:$PORT"
      echo "Servy opened $PROJECT on port $PORT ✅"
      exit 0
    fi
  done
done
echo "Servy started $PROJECT but no port came up in 10s — check manually."
```

### Step 6: Confirm to the user

One line. Examples:
- `Servy opened ParlonProjectOne on http://localhost:3000 ✅`
- `Already running — opened http://localhost:3000 ✅`

No explanation of steps. The user just wants the tab open.

---

## Edge cases

- **Project not found:** show the 3 closest matches from `~/Code/` and ask.
- **Port busy with unrelated process:** tell the user, don't kill it.
- **Dev script missing from package.json:** check for `start`, `serve`, or
  ask which script to run.
- **Project is in a subfolder** (monorepo): if `~/Code/<name>` has no
  `package.json` but its children do, ask which workspace to start.

---

## Why this skill exists

The user runs lots of projects (`~/Code/` has 10+) and switches between them
constantly. The friction of remembering which package manager each one uses,
typing the full command, and waiting to open a browser tab adds up. Servy
collapses all that into "Servy open [name]".
