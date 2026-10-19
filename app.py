"""
GGNoob Temp Mail - Free disposable email on @ggnoob.space
Powered by Catchmail API
"""

import os
import re
import time
import random
import string
from functools import wraps
from datetime import datetime, timezone

import requests
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    Response,
    abort,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production-ggnoob-2026")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DOMAIN = "ggnoob.space"
BASE_API = "https://api.catchmail.io/api/v1"
REQUEST_TIMEOUT = 15
RATE_LIMIT_SECONDS = 1.2  # respect public API limit (~1 req/s)

# Simple in-memory rate limiter per IP (good enough for small VPS)
_last_request = {}


def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
        now = time.time()
        last = _last_request.get(ip, 0)
        if now - last < 0.8:
            return jsonify({"error": "Too many requests. Please wait a moment."}), 429
        _last_request[ip] = now
        return f(*args, **kwargs)
    return decorated


def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def sanitize_name(name: str) -> str:
    """Allow only safe local-part characters."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9._+-]", "", name)
    return name[:64] if name else ""


def random_name(length: int = 10) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    name = request.args.get("name", "").strip()
    if name:
        name = sanitize_name(name)
        if not name:
            name = random_name()
    else:
        name = random_name()
    email = f"{name}@{DOMAIN}"
    return render_template(
        "index.html",
        email=email,
        name=name,
        domain=DOMAIN,
        year=datetime.now(timezone.utc).year,
    )


@app.route("/mailbox/<name>")
def mailbox(name):
    name = sanitize_name(name)
    if not name:
        return redirect(url_for("index"))
    email = f"{name}@{DOMAIN}"
    return render_template(
        "mailbox.html",
        email=email,
        name=name,
        domain=DOMAIN,
        year=datetime.now(timezone.utc).year,
    )


@app.route("/faq")
def faq():
    return render_template("faq.html", domain=DOMAIN, year=datetime.now(timezone.utc).year)


@app.route("/terms")
def terms():
    return render_template("terms.html", domain=DOMAIN, year=datetime.now(timezone.utc).year)


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", domain=DOMAIN, year=datetime.now(timezone.utc).year)


@app.route("/about")
def about():
    return render_template("about.html", domain=DOMAIN, year=datetime.now(timezone.utc).year)


@app.route("/contact")
def contact():
    return render_template("contact.html", domain=DOMAIN, year=datetime.now(timezone.utc).year)


# ---------------------------------------------------------------------------
# API endpoints (AJAX)
# ---------------------------------------------------------------------------

@app.route("/api/messages")
@rate_limit
def api_messages():
    email = request.args.get("email", "").strip().lower()
    if not email or not email.endswith(f"@{DOMAIN}"):
        return jsonify({"error": "Invalid email address"}), 400

    local = email.split("@")[0]
    if not sanitize_name(local):
        return jsonify({"error": "Invalid local part"}), 400

    try:
        data = get_json(
            f"{BASE_API}/mailbox",
            {"address": email, "page": 1, "page_size": 50},
        )
        messages = data.get("messages", [])
        # Normalize for frontend
        out = []
        for m in messages:
            out.append({
                "id": m.get("id"),
                "from": m.get("from", "Unknown"),
                "subject": m.get("subject") or "(no subject)",
                "date": m.get("date", ""),
                "size": m.get("size", 0),
            })
        return jsonify({
            "email": email,
            "total": data.get("total", len(out)),
            "messages": out,
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Unable to reach mail service. Try again shortly."}), 502
    except (ValueError, KeyError, TypeError):
        return jsonify({"error": "Unexpected response from mail service"}), 502


@app.route("/api/message/<msg_id>")
@rate_limit
def api_message(msg_id):
    email = request.args.get("email", "").strip().lower()
    if not email or not email.endswith(f"@{DOMAIN}"):
        return jsonify({"error": "Invalid email address"}), 400

    # Basic id sanitization
    if not re.match(r"^[a-zA-Z0-9_-]+$", msg_id):
        return jsonify({"error": "Invalid message id"}), 400

    try:
        detail = get_json(
            f"{BASE_API}/message/{msg_id}",
            {"mailbox": email},
        )
        body = detail.get("body", {}) or {}
        return jsonify({
            "id": detail.get("id"),
            "from": detail.get("from", "Unknown"),
            "to": detail.get("to", []),
            "subject": detail.get("subject") or "(no subject)",
            "date": detail.get("date", ""),
            "text": body.get("text") or "",
            "html": body.get("html") or "",
            "attachments": detail.get("attachments", []),
        })
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return jsonify({"error": "Message not found"}), 404
        return jsonify({"error": "Unable to fetch message"}), 502
    except requests.exceptions.RequestException:
        return jsonify({"error": "Unable to reach mail service"}), 502
    except (ValueError, KeyError, TypeError):
        return jsonify({"error": "Unexpected response"}), 502


@app.route("/api/random")
def api_random():
    name = random_name()
    return jsonify({"name": name, "email": f"{name}@{DOMAIN}"})


# ---------------------------------------------------------------------------
# SEO / Ads / Legal static files
# ---------------------------------------------------------------------------

@app.route("/robots.txt")
def robots():
    content = f"""User-agent: *
Allow: /
Disallow: /api/
Sitemap: https://{DOMAIN}/sitemap.xml
"""
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    base = f"https://{DOMAIN}"
    pages = [
        ("/", "1.0", "daily"),
        ("/faq", "0.8", "weekly"),
        ("/about", "0.7", "monthly"),
        ("/terms", "0.5", "monthly"),
        ("/privacy", "0.5", "monthly"),
        ("/contact", "0.6", "monthly"),
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for path, priority, freq in pages:
        xml.append("  <url>")
        xml.append(f"    <loc>{base}{path}</loc>")
        xml.append(f"    <changefreq>{freq}</changefreq>")
        xml.append(f"    <priority>{priority}</priority>")
        xml.append("  </url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/ads.txt")
def ads_txt():
    # Replace with your real AdSense publisher ID after approval
    # Format: google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0
    content = """# ads.txt for ggnoob.space
# Replace pub-XXXXXXXXXXXXXXXX with your actual AdSense publisher ID
google.com, pub-5246708787988002, DIRECT, f08c47fec0942fa0
"""
    return Response(content, mimetype="text/plain")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", domain=DOMAIN, year=datetime.now(timezone.utc).year), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html", domain=DOMAIN, year=datetime.now(timezone.utc).year), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
