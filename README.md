# LibManagement

A Python web application for managing a library — built with Flask, SQLAlchemy, and Bootstrap 5.

## Features

- **Books** — add, edit, delete, search (by title, author, ISBN)
- **Members** — register, edit, remove library members
- **Loans** — issue books to members, set due dates, mark returns
- **Dashboard** — at-a-glance stats (total books, members, active loans, overdue count) and recent activity
- **Overdue tracking** — loans past their due date are highlighted

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Project Structure

```
LibManagement/
├── app.py              # Flask application and all routes
├── models.py           # SQLAlchemy models (Book, Member, Loan)
├── requirements.txt    # Python dependencies
├── static/
│   └── css/style.css  # Custom stylesheet
└── templates/
    ├── base.html       # Shared layout with navbar
    ├── index.html      # Dashboard
    ├── books/          # Book list, detail, add/edit form
    ├── members/        # Member list, detail, add/edit form
    └── loans/          # Loan list and borrow form
```

The app uses an SQLite database (`instance/library.db`) that is created automatically on first run.

## Running Tests

```bash
pip install pytest
pytest tests/
```
