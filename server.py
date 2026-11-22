import hashlib
import hmac
from contextlib import closing
from html import escape
from http.cookies import CookieError, SimpleCookie
from http import HTTPStatus
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import parse_qs, quote, unquote, urlsplit
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("CODE_LEARN_DATABASE", ROOT / "code-learn.sqlite3"))
BIND_HOST = os.environ.get("CODE_LEARN_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
SECURE_COOKIES = os.environ.get("CODE_LEARN_SECURE_COOKIES", "1" if BIND_HOST != "127.0.0.1" else "0") == "1"
TEMPLATE = (ROOT / "index.html").read_text(encoding="utf-8")
CODING_PAGE = ROOT / "coding-content.html"
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


class Request:
    def __init__(self, environ):
        path = quote(environ["PATH_INFO"].encode("latin-1"), safe="/")
        self.path = path + "?" + environ.get("QUERY_STRING", "")
        self.environ = environ

    def send_content(self, content, content_type="text/html; charset=utf-8", status=200, headers=()):
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.status = f"{status} {HTTPStatus(status).phrase}"
        self.headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(content))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            *headers,
        ]
        self.body = content

    def send_error(self, status):
        self.send_content(HTTPStatus(status).phrase, "text/plain; charset=utf-8", status)

    def redirect(self, location, cookie=None):
        headers = [("Location", location)]
        if cookie:
            headers.append(("Set-Cookie", cookie))
        self.send_content("", status=303, headers=headers)

    def session_token(self):
        try:
            cookie = SimpleCookie(self.environ.get("HTTP_COOKIE", "")).get(COOKIE)
        except CookieError:
            return ""
        return hashlib.sha256(cookie.value.encode()).hexdigest() if cookie else ""

    def render(self, page, signed_in=False, message="", section=""):
        html = TEMPLATE.replace('<body class="static-site">', '<body>')
        html = html.replace('    <script src="pages-navigation.js" defer></script>\n', '')
        html = html.replace('href="#home"', 'href="/"').replace('href="#about"', 'href="/about"')
        html = re.sub(
            r'href="#learning-access" data-route="(\w+)"(?: data-section="([\w-]+)")?',
            lambda match: f'href="{learning_url(match[2]) if match[1] == "coding" else "/" + match[1]}"',
            html,
        )
        if signed_in and page == "coding":
            html = html.replace("<!-- CODING PAGE -->", CODING_PAGE.read_text(encoding="utf-8"))
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
        if self.environ.get("HTTP_SEC_FETCH_SITE") == "cross-site":
            self.send_error(403)
            return
        try:
            size = int((self.environ.get("CONTENT_LENGTH") or "0"))
            if not 0 <= size <= 8192:
                raise ValueError
            fields = parse_qs(self.environ["wsgi.input"].read(size).decode(), max_num_fields=10)
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

    def cookie(self, token, age):
        secure = "; Secure" if SECURE_COOKIES or self.environ["wsgi.url_scheme"] == "https" else ""
        return f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={age}{secure}"


def application(environ, start_response):
    request = Request(environ)
    method = environ["REQUEST_METHOD"]
    if method in {"GET", "HEAD"}:
        request.do_GET()
    elif method == "POST":
        request.do_POST()
    else:
        request.send_content("Method Not Allowed", "text/plain; charset=utf-8", 405, [("Allow", "GET, HEAD, POST")])
    start_response(request.status, request.headers)
    return [b"" if method == "HEAD" else request.body]


if __name__ == "__main__":
    initialize()
    with make_server(BIND_HOST, PORT, application) as server:
        print(f"Code Learn System listening on {BIND_HOST}:{server.server_port}", flush=True)
        server.serve_forever()
