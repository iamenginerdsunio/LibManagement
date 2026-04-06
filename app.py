from datetime import datetime, timedelta, timezone
import os

from flask import Flask, flash, redirect, render_template, request, url_for
from extensions import db


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")

    db.init_app(app)

    from models import Book, Loan, Member

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_now():
        return {"now": datetime.now(timezone.utc)}

    # ── Dashboard ──────────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        total_books = Book.query.count()
        total_members = Member.query.count()
        active_loans = Loan.query.filter_by(returned_at=None).count()
        overdue_loans = [
            loan
            for loan in Loan.query.filter_by(returned_at=None).all()
            if loan.is_overdue
        ]
        recent_loans = (
            Loan.query.order_by(Loan.borrowed_at.desc()).limit(5).all()
        )
        return render_template(
            "index.html",
            total_books=total_books,
            total_members=total_members,
            active_loans=active_loans,
            overdue_count=len(overdue_loans),
            recent_loans=recent_loans,
        )

    # ── Books ──────────────────────────────────────────────────────────────────
    @app.route("/books")
    def books():
        query = request.args.get("q", "").strip()
        if query:
            books_list = Book.query.filter(
                Book.title.ilike(f"%{query}%")
                | Book.author.ilike(f"%{query}%")
                | Book.isbn.ilike(f"%{query}%")
            ).all()
        else:
            books_list = Book.query.order_by(Book.title).all()
        return render_template("books/list.html", books=books_list, query=query)

    @app.route("/books/add", methods=["GET", "POST"])
    def add_book():
        if request.method == "POST":
            title = request.form["title"].strip()
            author = request.form["author"].strip()
            isbn = request.form["isbn"].strip()
            genre = request.form.get("genre", "").strip()
            quantity = int(request.form.get("quantity", 1))

            if not title or not author or not isbn:
                flash("Title, author, and ISBN are required.", "danger")
                return render_template("books/form.html", action="Add")

            if Book.query.filter_by(isbn=isbn).first():
                flash("A book with that ISBN already exists.", "danger")
                return render_template("books/form.html", action="Add")

            book = Book(
                title=title,
                author=author,
                isbn=isbn,
                genre=genre,
                quantity=quantity,
                available=quantity,
            )
            db.session.add(book)
            db.session.commit()
            flash(f'"{title}" added successfully.', "success")
            return redirect(url_for("books"))

        return render_template("books/form.html", action="Add")

    @app.route("/books/<int:book_id>")
    def book_detail(book_id):
        book = db.get_or_404(Book, book_id)
        loans = (
            Loan.query.filter_by(book_id=book_id)
            .order_by(Loan.borrowed_at.desc())
            .all()
        )
        return render_template("books/detail.html", book=book, loans=loans)

    @app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
    def edit_book(book_id):
        book = db.get_or_404(Book, book_id)
        if request.method == "POST":
            title = request.form["title"].strip()
            author = request.form["author"].strip()
            isbn = request.form["isbn"].strip()
            genre = request.form.get("genre", "").strip()
            quantity = int(request.form.get("quantity", 1))

            if not title or not author or not isbn:
                flash("Title, author, and ISBN are required.", "danger")
                return render_template("books/form.html", action="Edit", book=book)

            existing = Book.query.filter_by(isbn=isbn).first()
            if existing and existing.id != book_id:
                flash("Another book with that ISBN already exists.", "danger")
                return render_template("books/form.html", action="Edit", book=book)

            diff = quantity - book.quantity
            book.title = title
            book.author = author
            book.isbn = isbn
            book.genre = genre
            book.quantity = quantity
            book.available = max(0, book.available + diff)
            db.session.commit()
            flash(f'"{title}" updated successfully.', "success")
            return redirect(url_for("book_detail", book_id=book_id))

        return render_template("books/form.html", action="Edit", book=book)

    @app.route("/books/<int:book_id>/delete", methods=["POST"])
    def delete_book(book_id):
        book = db.get_or_404(Book, book_id)
        if Loan.query.filter_by(book_id=book_id, returned_at=None).count() > 0:
            flash("Cannot delete a book that is currently on loan.", "danger")
            return redirect(url_for("book_detail", book_id=book_id))
        db.session.delete(book)
        db.session.commit()
        flash(f'"{book.title}" deleted.', "success")
        return redirect(url_for("books"))

    # ── Members ────────────────────────────────────────────────────────────────
    @app.route("/members")
    def members():
        query = request.args.get("q", "").strip()
        if query:
            members_list = Member.query.filter(
                Member.name.ilike(f"%{query}%")
                | Member.email.ilike(f"%{query}%")
            ).all()
        else:
            members_list = Member.query.order_by(Member.name).all()
        return render_template("members/list.html", members=members_list, query=query)

    @app.route("/members/add", methods=["GET", "POST"])
    def add_member():
        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip()
            phone = request.form.get("phone", "").strip()

            if not name or not email:
                flash("Name and email are required.", "danger")
                return render_template("members/form.html", action="Add")

            if Member.query.filter_by(email=email).first():
                flash("A member with that email already exists.", "danger")
                return render_template("members/form.html", action="Add")

            member = Member(name=name, email=email, phone=phone)
            db.session.add(member)
            db.session.commit()
            flash(f'Member "{name}" added successfully.', "success")
            return redirect(url_for("members"))

        return render_template("members/form.html", action="Add")

    @app.route("/members/<int:member_id>")
    def member_detail(member_id):
        member = db.get_or_404(Member, member_id)
        loans = (
            Loan.query.filter_by(member_id=member_id)
            .order_by(Loan.borrowed_at.desc())
            .all()
        )
        return render_template("members/detail.html", member=member, loans=loans)

    @app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
    def edit_member(member_id):
        member = db.get_or_404(Member, member_id)
        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip()
            phone = request.form.get("phone", "").strip()

            if not name or not email:
                flash("Name and email are required.", "danger")
                return render_template("members/form.html", action="Edit", member=member)

            existing = Member.query.filter_by(email=email).first()
            if existing and existing.id != member_id:
                flash("Another member with that email already exists.", "danger")
                return render_template("members/form.html", action="Edit", member=member)

            member.name = name
            member.email = email
            member.phone = phone
            db.session.commit()
            flash(f'Member "{name}" updated.', "success")
            return redirect(url_for("member_detail", member_id=member_id))

        return render_template("members/form.html", action="Edit", member=member)

    @app.route("/members/<int:member_id>/delete", methods=["POST"])
    def delete_member(member_id):
        member = db.get_or_404(Member, member_id)
        if Loan.query.filter_by(member_id=member_id, returned_at=None).count() > 0:
            flash("Cannot delete a member who has active loans.", "danger")
            return redirect(url_for("member_detail", member_id=member_id))
        db.session.delete(member)
        db.session.commit()
        flash(f'Member "{member.name}" deleted.', "success")
        return redirect(url_for("members"))

    # ── Loans ──────────────────────────────────────────────────────────────────
    @app.route("/loans")
    def loans():
        filter_type = request.args.get("filter", "active")
        if filter_type == "returned":
            loans_list = (
                Loan.query.filter(Loan.returned_at.isnot(None))
                .order_by(Loan.returned_at.desc())
                .all()
            )
        elif filter_type == "overdue":
            loans_list = [
                loan
                for loan in Loan.query.filter_by(returned_at=None).all()
                if loan.is_overdue
            ]
        else:
            loans_list = (
                Loan.query.filter_by(returned_at=None)
                .order_by(Loan.due_date)
                .all()
            )
        return render_template("loans/list.html", loans=loans_list, filter_type=filter_type)

    @app.route("/loans/borrow", methods=["GET", "POST"])
    def borrow():
        books_available = Book.query.filter(Book.available > 0).order_by(Book.title).all()
        members_all = Member.query.order_by(Member.name).all()

        if request.method == "POST":
            book_id = int(request.form["book_id"])
            member_id = int(request.form["member_id"])
            days = int(request.form.get("days", 14))

            book = db.get_or_404(Book, book_id)
            member = db.get_or_404(Member, member_id)

            if book.available < 1:
                flash("That book is not available for borrowing.", "danger")
                return render_template(
                    "loans/borrow.html",
                    books=books_available,
                    members=members_all,
                )

            due = datetime.now(timezone.utc) + timedelta(days=days)
            loan = Loan(book_id=book_id, member_id=member_id, due_date=due)
            book.available -= 1
            db.session.add(loan)
            db.session.commit()
            flash(
                f'"{book.title}" loaned to {member.name}. Due: {due.strftime("%Y-%m-%d")}.',
                "success",
            )
            return redirect(url_for("loans"))

        return render_template(
            "loans/borrow.html", books=books_available, members=members_all
        )

    @app.route("/loans/<int:loan_id>/return", methods=["POST"])
    def return_book(loan_id):
        loan = db.get_or_404(Loan, loan_id)
        if loan.returned_at:
            flash("This loan has already been returned.", "warning")
            return redirect(url_for("loans"))
        loan.returned_at = datetime.now(timezone.utc)
        loan.book.available += 1
        db.session.commit()
        flash(f'"{loan.book.title}" returned successfully.', "success")
        return redirect(url_for("loans"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run()
