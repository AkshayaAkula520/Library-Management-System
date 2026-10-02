from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL

app = Flask(__name__)

# ==========================================
# MySQL Configuration
# ==========================================

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'YOUR_MYSQL_PASSWORD'
app.config['MYSQL_DB'] = 'library_management'

mysql = MySQL(app)


# ==========================================
# Dashboard
# ==========================================

@app.route('/')
def home():

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM books
    """)
    total_copies = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(available_quantity), 0)
        FROM books
    """)
    available_copies = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
    """)
    total_students = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM borrowings
        WHERE status='Issued'
    """)
    active_borrowings = cursor.fetchone()[0]

    # Recent Borrowings
    cursor.execute("""
        SELECT
            books.title,
            borrowings.student_name,
            borrowings.issue_date,
            borrowings.status
        FROM borrowings
        JOIN books
        ON borrowings.book_id = books.id
        ORDER BY borrowings.id DESC
        LIMIT 5
    """)

    recent_borrowings = cursor.fetchall()

    cursor.close()

    return render_template(
        'index.html',
        total_books=total_books,
        total_copies=total_copies,
        available_copies=available_copies,
        total_students=total_students,
        active_borrowings=active_borrowings,
        recent_borrowings=recent_borrowings
    )


# ==========================================
# Add Book
# ==========================================

@app.route('/add-book', methods=['GET', 'POST'])
def add_book():

    if request.method == 'POST':

        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        isbn = request.form['isbn']
        quantity = request.form['quantity']

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO books
            (title, author, category, isbn, quantity, available_quantity)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            title,
            author,
            category,
            isbn,
            quantity,
            quantity
        ))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('books'))

    return render_template('add_book.html')


# ==========================================
# View / Search / Filter Books
# ==========================================

@app.route('/books')
def books():

    search = request.args.get('search', '')
    category = request.args.get('category', '')

    cursor = mysql.connection.cursor()

    query = """
        SELECT *
        FROM books
        WHERE 1=1
    """

    params = []

    if search:

        query += """
            AND (
                title LIKE %s
                OR author LIKE %s
            )
        """

        params.extend([
            f'%{search}%',
            f'%{search}%'
        ])

    if category:

        query += """
            AND category=%s
        """

        params.append(category)

    cursor.execute(
        query,
        tuple(params)
    )

    books = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT category
        FROM books
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
    """)

    categories = cursor.fetchall()

    cursor.close()

    return render_template(
        'books.html',
        books=books,
        search=search,
        category=category,
        categories=categories
    )


# ==========================================
# Edit Book
# ==========================================

@app.route('/edit-book/<int:id>', methods=['GET', 'POST'])
def edit_book(id):

    cursor = mysql.connection.cursor()

    if request.method == 'POST':

        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        isbn = request.form['isbn']
        quantity = request.form['quantity']

        cursor.execute("""
            UPDATE books
            SET title=%s,
                author=%s,
                category=%s,
                isbn=%s,
                quantity=%s,
                available_quantity=%s
            WHERE id=%s
        """, (
            title,
            author,
            category,
            isbn,
            quantity,
            quantity,
            id
        ))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('books'))

    cursor.execute(
        "SELECT * FROM books WHERE id=%s",
        (id,)
    )

    book = cursor.fetchone()

    cursor.close()

    return render_template(
        'edit_book.html',
        book=book
    )

# ==========================================
# Delete Student
# ==========================================

@app.route('/delete-student/<int:id>')
def remove_student(id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM borrowings WHERE student_id=%s",
        (id,)
    )

    borrowing_count = cursor.fetchone()[0]

    if borrowing_count > 0:

        cursor.close()

        return """
            <h2>Cannot Delete Student</h2>
            <p>This student has borrowing records and cannot be deleted.</p>
            <br>
            <a href="/students">← Back to Students</a>
        """

    cursor.execute(
        "DELETE FROM students WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('students'))


    


# ==========================================
# Issue Book
# ==========================================

@app.route('/issue-book', methods=['GET', 'POST'])
def issue_book():

    cursor = mysql.connection.cursor()

    if request.method == 'POST':

        student_id = request.form['student_id']
        book_id = request.form['book_id']

        cursor.execute(
            "SELECT name FROM students WHERE id=%s",
            (student_id,)
        )

        student = cursor.fetchone()

        cursor.execute(
            "SELECT available_quantity FROM books WHERE id=%s",
            (book_id,)
        )

        book = cursor.fetchone()

        if student and book and book[0] > 0:

            student_name = student[0]

            # Save both student ID and student name
            cursor.execute("""
                INSERT INTO borrowings
                (book_id, student_id, student_name, issue_date, status)
                VALUES (%s, %s, %s, CURDATE(), 'Issued')
            """, (
                book_id,
                student_id,
                student_name
            ))

            cursor.execute("""
                UPDATE books
                SET available_quantity =
                    available_quantity - 1
                WHERE id=%s
            """, (
                book_id,
            ))

            mysql.connection.commit()

    cursor.close()

    if request.method == 'POST':
        return redirect(url_for('books'))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT *
        FROM books
        WHERE available_quantity > 0
    """)

    books = cursor.fetchall()

    cursor.execute("""
        SELECT id, name, email
        FROM students
        ORDER BY name
    """)

    students = cursor.fetchall()

    cursor.close()

    return render_template(
        'issue_book.html',
        books=books,
        students=students
    )


# ==========================================
# Borrowing Records
# ==========================================

@app.route('/borrowings')
def borrowings():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            borrowings.id,
            books.title,
            borrowings.student_name,
            borrowings.issue_date,
            borrowings.return_date,
            borrowings.status
        FROM borrowings
        JOIN books
        ON borrowings.book_id = books.id
        ORDER BY borrowings.id DESC
    """)

    records = cursor.fetchall()

    cursor.close()

    return render_template(
        'borrowings.html',
        records=records
    )


# ==========================================
# Return Book
# ==========================================

@app.route('/return-book/<int:id>')
def return_book(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT book_id
        FROM borrowings
        WHERE id=%s
        AND status='Issued'
    """, (
        id,
    ))

    borrowing = cursor.fetchone()

    if borrowing:

        book_id = borrowing[0]

        cursor.execute("""
            UPDATE borrowings
            SET return_date=CURDATE(),
                status='Returned'
            WHERE id=%s
        """, (
            id,
        ))

        cursor.execute("""
            UPDATE books
            SET available_quantity =
                available_quantity + 1
            WHERE id=%s
        """, (
            book_id,
        ))

        mysql.connection.commit()

    cursor.close()

    return redirect(url_for('borrowings'))


# ==========================================
# View Students
# ==========================================

@app.route('/students')
def students():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT *
        FROM students
        ORDER BY id DESC
    """)

    students = cursor.fetchall()

    cursor.close()

    return render_template(
        'students.html',
        students=students
    )


# ==========================================
# Add Student
# ==========================================

@app.route('/add-student', methods=['GET', 'POST'])
def add_student():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT id FROM students WHERE email=%s",
            (email,)
        )

        existing_student = cursor.fetchone()

        if existing_student:

            cursor.close()

            return """
                <h2>Student already exists</h2>
                <p>This email address is already registered.</p>
                <a href="/students">Back to Students</a>
            """

        cursor.execute("""
            INSERT INTO students
            (name, email, phone)
            VALUES (%s, %s, %s)
        """, (
            name,
            email,
            phone
        ))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('students'))

    return render_template('add_student.html')


# ==========================================
# Edit Student
# ==========================================

@app.route('/edit-student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):

    cursor = mysql.connection.cursor()

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        cursor.execute("""
            UPDATE students
            SET name=%s,
                email=%s,
                phone=%s
            WHERE id=%s
        """, (
            name,
            email,
            phone,
            id
        ))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('students'))

    cursor.execute(
        "SELECT * FROM students WHERE id=%s",
        (id,)
    )

    student = cursor.fetchone()

    cursor.close()

    return render_template(
        'edit_student.html',
        student=student
    )


# ==========================================
# Delete Student
# ==========================================

@app.route('/delete-student/<int:id>')
def delete_student(id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM students WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('students'))


# ==========================================
# Run Application
# ==========================================

if __name__ == '__main__':
    app.run(debug=True)