from pathlib import Path

BB_DOMAIN = "bb.sustech.edu.cn"
BB_BASE_URL = f"https://{BB_DOMAIN}"
BB_API_BASE = f"{BB_BASE_URL}/learn/api/public/v1"

CAS_LOGIN_URL = f"https://{BB_DOMAIN}/webapps/bb-sso-BBLEARN/index.jsp"

CONFIG_DIR = Path.home() / ".bb-cli"
COOKIE_FILE = CONFIG_DIR / "cookies.json"
