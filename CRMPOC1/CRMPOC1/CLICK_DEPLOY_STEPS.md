# Clickable Deployment Steps

This setup gives you two double-click files:

- `Deploy-UI.bat`
- `Deploy-Service.bat`

These prepare deployable output for the UI and API on a Windows server.

## What each file does

### `Deploy.cmd`

- runs deployment preflight checks before any deployment starts
- verifies the partner invite API rejects duplicate email addresses across registrations, users, and vendors
- verifies the invite UI displays duplicate validation errors inside the modal
- compiles the API source
- then continues to the existing local or production deployment prompt

### `Deploy-UI.bat`

- installs UI packages
- builds the React app
- creates `publish\ui`
- copies a `web.config` file for IIS SPA routing

### `Deploy-Service.bat`

- copies the API into `publish\api`
- creates a Python virtual environment
- installs Python requirements
- creates `.env` from template if missing
- creates helper files:
  - `run-api.cmd`
  - `install-api-task.cmd`
  - `start-api-task.cmd`
  - `stop-api-task.cmd`
  - `remove-api-task.cmd`

## Before you start

Install on the server or build machine:

- Node.js
- Python 3
- IIS if you want to host the UI on Windows Server

If using SQL Server, also install:

- Microsoft ODBC Driver 18 for SQL Server

## Step by step

### 1. Run the UI deploy file

Double-click:

- `Deploy-UI.bat`

After it finishes, your UI files will be in:

```text
publish\ui
```

### 2. Run the API deploy file

Double-click:

- `Deploy-Service.bat`

After it finishes, your API files will be in:

```text
publish\api
```

## 3. Edit API environment

Open:

```text
publish\api\.env
```

Set the correct values for:

- `DATABASE_BACKEND`
- `MYSQL_DATABASE_URL` or `SQLSERVER_DATABASE_URL`
- `JWT_SECRET`
- `CORS_ORIGINS`
- `SEED_ADMIN_PASSWORD`

## 4. Run database setup

Open Command Prompt in:

```text
publish\api
```

Run:

```bat
venv\Scripts\activate
alembic upgrade head
python -m app.seed
```

## 5. Install the API startup task

Run as Administrator:

```text
publish\api\install-api-task.cmd
```

Then run:

```text
publish\api\start-api-task.cmd
```

This starts the API on:

```text
http://127.0.0.1:8000
```

## 6. Host the UI

Use the contents of:

```text
publish\ui
```

as your IIS site root or upload target.

If using IIS:

- create a site pointing to `publish\ui`
- make sure URL Rewrite is installed

## 7. Connect UI to API on the same server

You need the web server to reverse proxy:

- `/api/*` -> `http://127.0.0.1:8000`
- `/uploads/*` -> `http://127.0.0.1:8000`
- `/health` -> `http://127.0.0.1:8000/health`

If you are using IIS, this reverse proxy is usually done with:

- IIS URL Rewrite
- Application Request Routing (ARR)

## Output folders

- UI output: `publish\ui`
- API output: `publish\api`
- Upload folder: `publish\uploads`

## Important note

These scripts are best for a Windows VPS or Windows Server.

They are not meant for normal Linux shared hosting or restricted cPanel hosting.
