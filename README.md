# GGNoob Temp Mail

Free disposable email service for **@ggnoob.space**, built with Flask and the Catchmail public API.

## Features

- Instant temporary addresses (`name@ggnoob.space`)
- Random or custom local-part
- Live inbox with auto-refresh
- Message detail view (text + sandboxed HTML)
- Clean, mobile-friendly dark UI
- SEO: sitemap.xml, robots.txt, human-readable content pages
- Legal: Terms of Service + Privacy Policy
- FAQ with common questions
- AdSense-ready: `ads.txt`, ad placeholder slots, policy-friendly structure
- Rate limiting on API routes

## Requirements

- Python 3.10+
- Domain `ggnoob.space` with MX record pointing to `smtp.catchmail.io` (Catchmail custom domain)

## Quick start

```bash
cd ggnoob-tempmail
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
export SECRET_KEY="your-random-secret"
python app.py
```

Open http://127.0.0.1:5000

## Production (example with Gunicorn)

```bash
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

Put Nginx/Caddy in front with HTTPS. Set `SECRET_KEY` in the environment.

## AdSense setup

1. Apply for AdSense with a real site that has content (this app already includes About, FAQ, Terms, Privacy).
2. After approval, edit `ads.txt` and replace `pub-XXXXXXXXXXXXXXXX` with your publisher ID.
3. Uncomment the AdSense script in `templates/base.html`.
4. Replace the placeholder `<div class="ad-slot">` blocks with real `<ins class="adsbygoogle">` units (slots are marked in index, mailbox, faq).

## Project structure

```
ggnoob-tempmail/
├── app.py
├── requirements.txt
├── README.md
├── static/
│   ├── css/style.css
│   └── js/app.js
└── templates/
    ├── base.html
    ├── index.html
    ├── mailbox.html
    ├── faq.html
    ├── about.html
    ├── terms.html
    ├── privacy.html
    ├── contact.html
    ├── 404.html
    └── 500.html
```

## API used

- `GET https://api.catchmail.io/api/v1/mailbox?address=...`
- `GET https://api.catchmail.io/api/v1/message/{id}?mailbox=...`

Public endpoints, ~1 request/second per IP. The app rate-limits client requests accordingly.

## License

Use and modify freely for your own domain. Not affiliated with Catchmail.
