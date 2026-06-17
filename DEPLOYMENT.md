# OurHome Deployment

## Environment

Create a server-side `.env` from `.env.example` and set real values:

```bash
DEBUG=False
SECRET_KEY=<long-random-secret>
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

Keep `.env` out of git.

## Install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If the server has an old system SQLite and Django reports `SQLite 3.31 or later is required`,
install the bundled SQLite package and enable it in `.env`:

```bash
pip install pysqlite3-binary
echo "USE_PYSQLITE3=True" >> .env
```

On Windows, activate with:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Prepare Database And Static Files

Run from the repository root:

```bash
python TodoList/manage.py migrate
python TodoList/manage.py collectstatic --noinput
python TodoList/manage.py check --deploy
```

## Run

For a real server, run Django through a WSGI server and put it behind HTTPS:

```bash
gunicorn TodoList.wsgi:application --chdir TodoList --bind 127.0.0.1:8000
```

Then proxy traffic from Nginx/Caddy/Apache to `127.0.0.1:8000`.

## Notes

- Files and chat media are stored in the database, including encrypted chat attachments.
- Browser desktop notifications require the chat page to be open and notification permission to be granted.
- If the app is behind a reverse proxy, keep `SECURE_PROXY_SSL_HEADER` enabled and pass `X-Forwarded-Proto: https`.
