import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from extensions import db
from models import Book, Member, Loan


@pytest.fixture
def client():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    app.config["TESTING"] = True

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()



def add_book(client, title="Python 101", author="Guido", isbn="0000000001"):
    return client.post(
        "/books/add",
        data={"title": title, "author": author, "isbn": isbn, "quantity": 2},
        follow_redirects=True,
    )


def add_member(client, name="Alice", email="alice@example.com"):
    return client.post(
        "/members/add",
        data={"name": name, "email": email},
        follow_redirects=True,
    )


# ── Dashboard ──────────────────────────────────────────────────────────────────

def test_dashboard(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Dashboard" in r.data


# ── Books ──────────────────────────────────────────────────────────────────────

def test_books_list_empty(client):
    r = client.get("/books")
    assert r.status_code == 200
    assert b"No books found" in r.data


def test_add_book(client):
    r = add_book(client)
    assert r.status_code == 200
    assert b"Python 101" in r.data


def test_add_book_duplicate_isbn(client):
    add_book(client)
    r = add_book(client)  # same ISBN
    assert b"already exists" in r.data


def test_add_book_missing_fields(client):
    r = client.post("/books/add", data={"title": "", "author": "", "isbn": ""})
    assert r.status_code == 200
    assert b"required" in r.data


def test_edit_book(client):
    add_book(client)
    book = Book.query.first()
    r = client.post(
        f"/books/{book.id}/edit",
        data={
            "title": "Updated Title",
            "author": "New Author",
            "isbn": "0000000001",
            "quantity": 3,
        },
        follow_redirects=True,
    )
    assert b"Updated Title" in r.data


def test_delete_book(client):
    add_book(client)
    book = Book.query.first()
    r = client.post(f"/books/{book.id}/delete", follow_redirects=True)
    assert r.status_code == 200
    assert Book.query.count() == 0


def test_search_books(client):
    add_book(client, title="Flask Web Dev")
    add_book(client, title="Django Guide", isbn="0000000002")
    r = client.get("/books?q=Flask")
    assert b"Flask Web Dev" in r.data
    assert b"Django Guide" not in r.data


# ── Members ────────────────────────────────────────────────────────────────────

def test_members_list_empty(client):
    r = client.get("/members")
    assert r.status_code == 200
    assert b"No members found" in r.data


def test_add_member(client):
    r = add_member(client)
    assert b"Alice" in r.data


def test_add_member_duplicate_email(client):
    add_member(client)
    r = add_member(client)  # same email
    assert b"already exists" in r.data


def test_delete_member(client):
    add_member(client)
    member = Member.query.first()
    r = client.post(f"/members/{member.id}/delete", follow_redirects=True)
    assert Member.query.count() == 0


# ── Loans ──────────────────────────────────────────────────────────────────────

def test_issue_and_return_loan(client):
    add_book(client)
    add_member(client)
    book = Book.query.first()
    member = Member.query.first()

    r = client.post(
        "/loans/borrow",
        data={"book_id": book.id, "member_id": member.id, "days": 14},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert Loan.query.count() == 1

    book = Book.query.first()
    assert book.available == 1  # was 2, now 1

    loan = Loan.query.first()
    r = client.post(f"/loans/{loan.id}/return", follow_redirects=True)
    assert r.status_code == 200

    book = Book.query.first()
    assert book.available == 2  # restored
    assert Loan.query.first().returned_at is not None


def test_cannot_borrow_unavailable_book(client):
    client.post(
        "/books/add",
        data={"title": "Rare Book", "author": "Author", "isbn": "9999", "quantity": 1},
        follow_redirects=True,
    )
    add_member(client)
    book = Book.query.first()
    member = Member.query.first()

    # borrow once — exhausts the single copy
    client.post(
        "/loans/borrow",
        data={"book_id": book.id, "member_id": member.id, "days": 7},
        follow_redirects=True,
    )
    assert Book.query.first().available == 0

    # book no longer in available list on borrow page
    r = client.get("/loans/borrow")
    assert b"Rare Book" not in r.data


def test_cannot_delete_book_on_loan(client):
    add_book(client)
    add_member(client)
    book = Book.query.first()
    member = Member.query.first()
    client.post(
        "/loans/borrow",
        data={"book_id": book.id, "member_id": member.id, "days": 7},
        follow_redirects=True,
    )
    r = client.post(f"/books/{book.id}/delete", follow_redirects=True)
    assert b"Cannot delete" in r.data
    assert Book.query.count() == 1


def test_loans_filter_tabs(client):
    r = client.get("/loans?filter=active")
    assert r.status_code == 200
    r = client.get("/loans?filter=returned")
    assert r.status_code == 200
    r = client.get("/loans?filter=overdue")
    assert r.status_code == 200
