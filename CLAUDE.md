# sustech blackboard CLI

CLI tool (`bb`) for SUSTech students and their agents to interact with Blackboard LMS via its REST API.

## Architecture

```
src/bb_cli/
├── cli.py               # Click group entry point, --json flag
├── auth.py              # CAS SSO login (Playwright headless), cookie persistence (~/.bb-cli/cookies.json)
├── client.py            # httpx wrapper: GET, paginated GET, file download, 401 re-auth
├── config.py            # Constants: BB URLs, cookie/context paths
├── context.py           # Stateful navigation context (~/.bb-cli/context.json)
├── formatting.py        # Rich tables / JSON output helpers
└── commands/
    ├── login.py          # bb login — force CAS login, show user info
    ├── courses.py        # bb courses [--term] — enrolled courses, fetch_courses() helper
    ├── announcements.py  # bb announcements [--course ID] — fetch_announcements() helper
    ├── contents.py       # bb ls [COURSE_ID] [PATH] — context-aware listing
    ├── nav.py            # bb cd [TARGET], bb pwd — stateful navigation
    ├── show.py           # bb show <target|grades|announcements> — unified viewer
    ├── download.py       # bb download TARGET [-o DIR] — context-aware download
    └── grades.py         # bb grades [COURSE_ID] — fetch_grades() helper
```

**Auth flow**: `ensure_authenticated()` → load cookies → validate via `/users/me` → if expired: prompt creds (or `BB_SID`/`BB_PASSWORD` env vars) → Playwright headless CAS login → save cookies.

**Data flow**: Commands call `ensure_authenticated()` → build `BBClient(cookies)` → call BB REST API → format with Rich or `--json`.

**Navigation state**: `context.py` manages `~/.bb-cli/context.json` — stores current course, folder path, and cached `last_ls` items. Enables `cd`/`ls`/`pwd` workflow so agents and humans don't repeat opaque IDs.

---

## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One tack per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management
1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

