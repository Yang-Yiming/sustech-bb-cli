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
# Login via CAS SSO
uv run bb login

# List courses
uv run bb ls

# Enter a course by row number
uv run bb cd 3

# Browse contents
uv run bb ls

# Navigate into a folder
uv run bb cd "Lecture Notes"

# Download an item
uv run bb download 2

# Check grades
uv run bb show grades

# Where am I?
uv run bb pwd

# Go back
uv run bb cd ..

# Leave course entirely
uv run bb cd
```

## Commands

### Navigation

#### `bb ls [COURSE_ID] [PATH]`

List courses or folder contents, depending on context.

```bash
bb ls                              # no course context → list courses
bb ls                              # with course context → list current folder
bb ls CS101                        # explicit course root
bb ls CS101 "Lecture Notes/Week 1" # explicit path
```

#### `bb cd [TARGET]`

Change the current course or folder context.

```bash
bb cd 3              # enter course #3 (from bb ls)
bb cd "Lecture Notes" # enter folder by name
bb cd 1/2            # nested navigation by index
bb cd ..             # go up one level
bb cd /              # back to course root
bb cd                # clear context entirely
```

#### `bb pwd`

Show the current location.

```bash
$ bb pwd
/CS101/Lecture Notes/Week 1
```

### Viewing

#### `bb show TARGET`

Show details for a content item, grades, or announcements.

```bash
bb show 3              # item #3 from last bb ls
bb show grades         # grades for current course
bb show announcements  # announcements for current course
```

### Actions

#### `bb download TARGET [-o DIR]`

Download attachments. TARGET can be a row number, name, or Blackboard ID.

```bash
bb download 3              # download item #3 from last bb ls
bb download "Week 1"       # download by name
bb download _12345_1 _67890_1  # explicit content + course IDs
```

#### `bb login`

Force a fresh CAS SSO login and display user info.

### Backward-Compatible Commands

These still work with explicit IDs:

```bash
bb courses [--term TEXT]
bb grades COURSE_ID
bb announcements [--course COURSE_ID]
bb contents COURSE_ID [PATH]
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
uv run bb --json ls | jq '.[].Name'
```

Typical agent workflow:

```bash
bb ls                          # see courses
bb cd 3                        # pick one
bb ls                          # see contents
bb --json show grades          # get grades as JSON
bb download 2 -o ./out         # grab a file
bb cd                          # clean up
```

## State Files

| What              | Path                                       |
|-------------------|--------------------------------------------|
| Cookies           | `~/.bb-cli/cookies.json`                   |
| Navigation state  | `~/.bb-cli/context.json`                   |
| Config directory  | `~/.bb-cli/`                               |

Navigation state (`context.json`) stores the current course, folder path, and cached listing so that `cd`/`ls`/`pwd` work across separate invocations. Clear it with `bb cd`.

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
│   ├── context.py              # Stateful navigation (context.json)
│   ├── formatting.py           # Rich table / JSON output helpers
│   └── commands/
│       ├── __init__.py
│       ├── login.py            # bb login
│       ├── courses.py          # bb courses
│       ├── announcements.py    # bb announcements
│       ├── contents.py         # bb ls
│       ├── nav.py              # bb cd, bb pwd
│       ├── show.py             # bb show
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
| `ls`            | `GET /courses/{id}/contents`, `.../contents/{id}/children`  |
| `download`      | `GET .../contents/{id}/attachments`, `.../download`         |
| `grades`        | `GET .../gradebook/columns`, `.../columns/{id}/users/{id}`  |
