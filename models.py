from datetime import datetime, timezone
from extensions import db


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    genre = db.Column(db.String(100))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    available = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    loans = db.relationship("Loan", backref="book", lazy=True)

    def __repr__(self):
        return f"<Book {self.title}>"


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    loans = db.relationship("Loan", backref="member", lazy=True)

    def __repr__(self):
        return f"<Member {self.name}>"


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    borrowed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.DateTime, nullable=False)
    returned_at = db.Column(db.DateTime, nullable=True)

    @property
    def is_overdue(self):
        if self.returned_at:
            return False
        now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        return now_naive_utc > self.due_date

    @property
    def is_active(self):
        return self.returned_at is None

    def __repr__(self):
        return f"<Loan book={self.book_id} member={self.member_id}>"
