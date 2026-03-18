# sustech-bb-cli

CLI tool for SUSTech students (and their agents) to interact with Blackboard LMS.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
git clone https://github.com/<you>/sustech-bb-cli.git
cd sustech-bb-cli
uv sync
uv run playwright install chromium
```

## Quick Start

```bash
# Login via CAS SSO (interactive)
uv run bb login

# List your courses
uv run bb courses

# Any command as JSON (for scripts/agents)
uv run bb --json courses
```

## Commands

### `bb login`

Force a fresh CAS login and display your user info.

```bash
uv run bb login
```

### `bb courses [--term TEXT]`

List enrolled courses. Optionally filter by term name (substring match).

```bash
uv run bb courses
uv run bb courses --term "2025-2026-2"
```

### `bb announcements [--course COURSE_ID]`

List announcements. System-wide by default, or filtered to a specific course.

```bash
uv run bb announcements
uv run bb announcements --course _12345_1
```

### `bb contents COURSE_ID [--folder FOLDER_ID]`

List course content. Shows top-level folders by default, or a specific folder's children.

```bash
uv run bb contents _12345_1
uv run bb contents _12345_1 --folder _67890_1
```

### `bb download COURSE_ID CONTENT_ID [-o DIR]`

Download all attachments for a content item. Saves to current directory by default.

```bash
uv run bb download _12345_1 _67890_1
uv run bb download _12345_1 _67890_1 -o ./downloads
```

### `bb grades COURSE_ID`

Show your grades for a course.

```bash
uv run bb grades _12345_1
```

### Global Options

| Flag     | Description                          |
|----------|--------------------------------------|
| `--json` | Output as JSON instead of Rich table |
| `--help` | Show help for any command            |

## Non-Interactive / Agent Usage

Set environment variables to skip interactive prompts:

```bash
export BB_SID="12110000"
export BB_PASSWORD="your_password"
uv run bb login
```

Combine with `--json` for machine-readable output:

```bash
uv run bb --json courses | jq '.[].Name'
```

## File Paths

| What                    | Path                                       |
|-------------------------|--------------------------------------------|
| Cookie file             | `~/.bb-cli/cookies.json`                   |
| Config directory        | `~/.bb-cli/`                               |
| Playwright browsers     | `~/Library/Caches/ms-playwright/` (macOS)  |
| Project source          | `src/bb_cli/`                              |
| CLI entry point         | `src/bb_cli/cli.py`                        |

### Cookie File

Cookies are persisted at `~/.bb-cli/cookies.json` with `0600` permissions (owner read/write only). They are automatically validated on each command — if expired, you'll be prompted to re-login.

### Playwright Browsers

`uv run playwright install chromium` downloads Chromium to the platform-specific Playwright cache:

| Platform | Path                                  |
|----------|---------------------------------------|
| macOS    | `~/Library/Caches/ms-playwright/`     |
| Linux    | `~/.cache/ms-playwright/`             |
| Windows  | `%LOCALAPPDATA%\ms-playwright\`       |

## Project Structure

```
sustech-bb-cli/
├── pyproject.toml              # Dependencies, entry point, build config
├── uv.lock                     # Locked dependency versions
├── src/bb_cli/
│   ├── __init__.py
│   ├── __main__.py             # python -m bb_cli
│   ├── cli.py                  # Click group, --json flag
│   ├── auth.py                 # CAS SSO login, cookie persistence
│   ├── client.py               # httpx API client, pagination, download
│   ├── config.py               # URL and path constants
│   ├── formatting.py           # Rich table / JSON output helpers
│   └── commands/
│       ├── __init__.py
│       ├── login.py            # bb login
│       ├── courses.py          # bb courses
│       ├── announcements.py    # bb announcements
│       ├── contents.py         # bb contents
│       ├── download.py         # bb download
│       └── grades.py           # bb grades
└── tasks/
    ├── todo.md                 # Task tracking
    └── lessons.md              # Development lessons
```

## API Endpoints Used

All calls go through `https://bb.sustech.edu.cn/learn/api/public/v1`:

| Command         | Endpoints                                                   |
|-----------------|-------------------------------------------------------------|
| `login`         | `GET /users/me`                                             |
| `courses`       | `GET /users/{id}/courses`, `GET /courses/{id}`              |
| `announcements` | `GET /announcements`, `GET /courses/{id}/announcements`     |
| `contents`      | `GET /courses/{id}/contents`, `.../contents/{id}/children`  |
| `download`      | `GET .../contents/{id}/attachments`, `.../download`         |
| `grades`        | `GET .../gradebook/columns`, `.../columns/{id}/users/{id}`  |
