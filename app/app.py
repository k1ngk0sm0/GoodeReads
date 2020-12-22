import os

from flask import Flask, session, render_template, url_for, redirect, request, flash, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import requests

from helpers import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    """Display Home Page"""

    username = db.execute('SELECT username FROM users WHERE user_id = :user_id', {'user_id': session['user_id']}).fetchone()['username']

    return render_template('index.html', username=username)

@app.route("/register", methods=['GET', 'POST'])
def register():
    """Register User for Site"""

    # Render HTML if accessed via GET
    if request.method == 'GET':
        return render_template('register.html')

    # If accessed via post
    if request.method == 'POST':

        # Set variables for email and username
        email = request.form.get('email')
        username = request.form.get('username')

        # Validate Username
        if not username:
            flash('Must enter a valid username')
            return redirect(url_for('register'))

        if len(username) > 15:
            flash('Username must not exceed 15 characters')
            return redirect(url_for('register'))

        if db.execute("SELECT * FROM users WHERE username = :username", {'username': username}).fetchone():
            flash('Username is already in use.')
            return redirect(url_for('register'))

        if '@' in username:
            flash('Username cannot contain @ symbol')
            return redirect(url_for('register'))

        # Validate Email
        if not email:
            flash('Must enter a valid email')
            return redirect(url_for('register'))

        if db.execute("SELECT * FROM users WHERE email = :email", {"email": email}).fetchone():
            flash('Email is already registered.')
            return redirect(url_for('register'))

        # Validate Password
        if not request.form.get('password1'):
            flash('Must enter a password') 
            return redirect(url_for('register'))

        if request.form.get('password1') != request.form.get('password2'):
            flash('Passwords do not match.')
            return redirect(url_for('register'))
        
        # Opt into email if form not checked
        if not request.form.get('check'):
            updates = 'yes'
        else:
            updates = 'no'

        pass_hash = generate_password_hash(request.form.get('password1'))
        db.execute("INSERT INTO users (email, username, pass_hash, updates) VALUES (:email, :username, :pass_hash, :updates)", {'email': email, 'username':username, 'pass_hash': pass_hash, 'updates': updates})
        db.commit()
        return redirect('/login')
        
    
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must provide username or email")
            return render_template('login.html')

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must provide password")
            return render_template('login.html')
            

        # Query database for username
        username = request.form.get('username')
        rows = db.execute('SELECT * FROM users WHERE email = :email OR username = :username', {'email': username, 'username': username}).fetchall()
        
        # Ensure username exists and password is correct
        if len(rows) != 1:
            flash("Invalid Username")
            return render_template('login.html')

        if not check_password_hash(rows[0].pass_hash, request.form.get('password')):
            flash('Invalid Password') 
            return render_template('login.html')   
        
        else:
            # Remember which user has logged in
            session["user_id"] = rows[0].user_id

            # Redirect user to home page
            return redirect(url_for('index'))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    flash('Logged Out')
    return render_template('/login.html')

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Return results for main search bar"""

    if request.method == 'POST':

        # Assign search input to variable
        search = request.form.get('search')

        # Return no results if search bar left blank
        if not search:
            books = []
        
        # Otherwise, query database for reseults
        else:
            books = db.execute(f"SELECT * FROM books WHERE isbn LIKE '%{search}%' OR title ILIKE '%{search}%' OR author ILIKE '%{search}%'").fetchall()

        # Return results to user
        return render_template('search.html', books=books)

@app.route("/book/<isbn>", methods=["GET", "POST"])
@login_required
def book(isbn):
    """Show page for selected book and/or process submitted reviews"""

    if request.method == "POST":
        rating = request.form.get('rating')
        if not rating:
            flash('Must select a rating')
            return redirect(f'/book/{isbn}')
        
        review = request.form.get('review')
        if not review:
            flash('Please leave a review')
            return redirect(f'/book/{isbn}')

        db.execute('INSERT INTO reviews (user_id, isbn, rating, review) VALUES (:user_id, :isbn, :rating, :review)',
                    {'user_id': session['user_id'], 'isbn': isbn, 'rating': int(rating), 'review': review})
        db.commit()
        flash('Review Submitted')
        return redirect(f'/book/{isbn}')

    else:
        book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {'isbn': isbn}).fetchone()

        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                            params={"key": "HHMPS8uPGyImqdR5Gf00g", "isbns": book.isbn13})

        review_counts = res.json()['books'][0]['work_ratings_count'] 

        rating = res.json()['books'][0]['average_rating']

        results = db.execute('SELECT * FROM reviews WHERE isbn = :isbn', {'isbn': book['isbn']}).fetchall()

        reviews = []

        for result in results:
            user = db.execute('SELECT username FROM users WHERE user_id = :user_id', {'user_id': result['user_id']}).fetchone()
            reviews.append({'user': user['username'], 'rating': result['rating'], 'review': result['review']})

        return render_template('book.html', book=book, review_counts=review_counts, rating=rating, reviews=reviews)

@app.route("/api/<isbn>")
def api(isbn):
    """Return a JSON object detailing the requested ISBN"""

    book = db.execute('SELECT * FROM books WHERE isbn = :isbn', {'isbn': isbn}).fetchone()

    if book is None:
          return jsonify({"error": "Invalid ISBN"}), 422

    reviews = db.execute('select * from reviews where isbn = :isbn', {'isbn': isbn}).fetchall() 

    review_count = len(reviews)

    average_score = 0

    for review in reviews:
        average_score += review['rating']

    try:
        average_score /= review_count
    except ZeroDivisionError:
        average_score = 0

    return jsonify({
        "title": book['title'],
        "author": book['author'],
        "year": book['year'],
        "isbn": book['isbn'],
        "review_count": review_count,
        "average_score": average_score
    })

if __name__ == '__main__':
    app.debug=True
    app.run(port=8080)