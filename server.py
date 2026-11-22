import hashlib
import hmac
from contextlib import closing
from html import escape
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "code-learn.sqlite3"
TEMPLATE = (ROOT / "index.html").read_text(encoding="utf-8")
PUBLIC_TEMPLATE = re.sub(r"<!-- PRIVATE START -->.*?<!-- PRIVATE END -->", "", TEMPLATE, flags=re.S)
LESSONS = {
    "HTML5 Learning Resource.html", "CSS3 Learning Resource.html",
    "JavaScript Learning Resource.html", "React.js Learning Resources.html",
    "Design Tools & Resources.html",
}
SECTIONS = {"frontend-section", "backend-section", "design-section"}
LEVELS = {"beginner", "intermediate", "advanced", "student", "professional"}
SESSION_SECONDS = 8 * 60 * 60
COOKIE = "code_learn_session"


def initialize():
    with closing(sqlite3.connect(DATABASE)) as db, db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                email TEXT PRIMARY KEY, name TEXT NOT NULL, level TEXT NOT NULL,
                salt BLOB NOT NULL, password_hash BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY, expires INTEGER NOT NULL
            );
        """)


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)


def learning_url(section):
    return f"/coding?section={section}#{section}" if section in SECTIONS else "/coding"


class Handler(BaseHTTPRequestHandler):
    def send_content(self, content, content_type="text/html; charset=utf-8", status=200, headers=()):
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(content)

    def redirect(self, location, cookie=None):
        headers = [("Location", location)]
        if cookie:
            headers.append(("Set-Cookie", cookie))
        self.send_content("", status=303, headers=headers)

    def session_token(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", "")).get(COOKIE)
        except CookieError:
            return ""
        return hashlib.sha256(cookie.value.encode()).hexdigest() if cookie else ""

    def render(self, page, signed_in=False, message="", section=""):
        html = TEMPLATE if signed_in and page == "coding" else PUBLIC_TEMPLATE
        html = html.replace(f'id="{page}" class="page"', f'id="{page}" class="page active"')
        if signed_in:
            html = re.sub(
                r'<!-- AUTH NAV -->.*?(?=</div>)',
                '<form method="post" action="/logout"><button class="btn btn-login">Log out</button></form>',
                html, count=1, flags=re.S,
            )
            html = html.replace(
                '<a class="btn btn-login" href="/register">Create an account</a>', ""
            )
        if section in SECTIONS:
            html = html.replace(
                '<!-- AUTH FORM -->', f'<input type="hidden" name="section" value="{section}">'
            )
            for route in ("login", "register"):
                html = html.replace(f'href="/{route}"', f'href="/{route}?section={section}"')
        if message:
            marker = f'action="/{page}">'
            html = html.replace(marker, marker + f'<p class="form-notice" role="status">{escape(message)}</p>', 1)
        self.send_content(html)

    def do_GET(self):
        url = urlsplit(self.path)
        path = unquote(url.path)
        query = parse_qs(url.query)
        section = query.get("section", [""])[0]
        if path == "/styles.css":
            self.send_content((ROOT / "styles.css").read_bytes(), "text/css; charset=utf-8")
            return

        with closing(sqlite3.connect(DATABASE)) as db:
            signed_in = db.execute(
                "SELECT 1 FROM sessions WHERE token = ? AND expires > ?",
                (self.session_token(), int(time.time())),
            ).fetchone() is not None

        if path.lstrip("/") in LESSONS:
            if signed_in:
                self.send_content((ROOT / path.lstrip("/")).read_bytes())
            else:
                self.redirect("/login?required=1")
            return

        if path in {"/", "/index.html", "/about", "/coding", "/login", "/register"}:
            page = "home" if path in {"/", "/index.html"} else path[1:]
            if page == "coding" and not signed_in:
                next_section = f"&section={section}" if section in SECTIONS else ""
                self.redirect("/login?required=1" + next_section)
                return
            if signed_in and page in {"login", "register"}:
                self.redirect(learning_url(section))
                return
            message = ""
            if page == "login":
                if "registered" in query:
                    message = "Account created. Log in to start learning."
                elif "required" in query:
                    message = "Log in to access Coding Topics. New here? Create an account first."
            self.render(page, signed_in, message, section)
            return
        self.send_error(404)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in {"/register", "/login", "/logout"}:
            self.send_error(404)
            return
        # Only accept form submissions initiated on this site.
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.send_error(403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 <= size <= 8192:
                raise ValueError
            fields = parse_qs(self.rfile.read(size).decode(), max_num_fields=10)
        except ValueError:
            self.send_error(400)
            return

        with closing(sqlite3.connect(DATABASE)) as db, db:
            if path == "/logout":
                db.execute("DELETE FROM sessions WHERE token = ?", (self.session_token(),))
                db.commit()
                self.redirect("/", self.cookie("", 0))
                return

            data = {name: values[0] for name, values in fields.items()}
            email = data.get("email", "").strip().casefold()
            password = data.get("password", "")
            section = data.get("section", "")
            if path == "/register":
                self.register(db, data, email, password, section)
                return

            row = db.execute("SELECT salt, password_hash FROM accounts WHERE email = ?", (email,)).fetchone()
            if not row or not hmac.compare_digest(password_hash(password, row[0]), row[1]):
                self.render("login", message="Email or password is incorrect.", section=section)
                return
            token = secrets.token_urlsafe(32)
            now = int(time.time())
            db.execute("DELETE FROM sessions WHERE expires <= ? OR token = ?", (now, self.session_token()))
            db.execute("INSERT INTO sessions VALUES (?, ?)", (hashlib.sha256(token.encode()).hexdigest(), now + SESSION_SECONDS))
            db.commit()
            self.redirect(learning_url(section), self.cookie(token, SESSION_SECONDS))

    def register(self, db, data, email, password, section):
        name = data.get("name", "").strip()
        level = data.get("level")
        if not 1 <= len(name) <= 100 or len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or level not in LEVELS:
            self.render("register", message="Enter your name, a valid email, and your learning level.", section=section)
            return
        if not 8 <= len(password) <= 128 or password != data.get("confirmation"):
            self.render("register", message="Use 8–128 characters and make sure both passwords match.", section=section)
            return
        salt = secrets.token_bytes(16)
        try:
            db.execute("INSERT INTO accounts VALUES (?, ?, ?, ?, ?)", (email, name, level, salt, password_hash(password, salt)))
            db.commit()
        except sqlite3.IntegrityError:
            self.render("register", message="That email is already registered. Log in to continue.", section=section)
            return
        next_section = f"&section={section}" if section in SECTIONS else ""
        self.redirect("/login?registered=1" + next_section)

    @staticmethod
    def cookie(token, age):
        return f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={age}"


if __name__ == "__main__":
    initialize()
    print("Code Learn System is running at http://127.0.0.1:8000", flush=True)
    with ThreadingHTTPServer(("127.0.0.1", 8000), Handler) as server:
        server.serve_forever()
