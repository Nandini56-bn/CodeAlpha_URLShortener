# Tally URL Shortener

A small, self-hosted URL shortener built with FastAPI, SQLite, and SQLAlchemy. Create compact links, copy them in one click, and revisit your saved link history from a responsive browser interface.

## Features

- Tracks redirect clicks and lists saved links with their click counts in newest-first order.
- Includes URL validation, useful error messages, and one-click copy controls.
- Serves the frontend and API from the same local FastAPI app; no paid APIs or external services are used.

## Technologies

- Python 3.10 or newer
- FastAPI and Uvicorn
| `GET` | `/api/urls/{short_code}/stats` | Returns the original URL, creation time, and click count for a short code; returns HTTP 404 if it does not exist. |
- SQLite and SQLAlchemy 2
- HTML, CSS, and vanilla JavaScript

## Installation

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/) and enable **Add Python to PATH** in the Windows installer.
2. Open this project folder in VS Code.
3. In the VS Code terminal, create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks environment activation, run `.venv\Scripts\activate.bat` from Command Prompt instead.
4. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

## How to Run

From the project folder with the virtual environment activated, start the development server:

```powershell
python -m uvicorn main:app --reload
```

Open <http://127.0.0.1:8000> in your browser. The database file `urlshortener.db` is created beside `main.py` when the application starts. Stop the server with `Ctrl+C`.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/shorten` | Accepts `{"url": "https://example.com"}` and returns the saved mapping, including `short_url`. Invalid URLs return HTTP 422 with a readable `detail` message. |
| `GET` | `/api/urls` | Returns all saved URL mappings, newest first. |
| `GET` | `/{short_code}` | Redirects to the original URL, or returns HTTP 404 if the code does not exist. |

Interactive API documentation is available at <http://127.0.0.1:8000/docs> while the server is running.