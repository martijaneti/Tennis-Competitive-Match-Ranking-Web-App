from flask import Flask, render_template, request, redirect, session, url_for, flash
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env (optional, for local development)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')  # Use .env value or fallback for dev


def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE Username = %s AND Password = %s", (username, password))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
        except Exception as e:
            flash(f'Database error: {e}', 'danger')

    return render_template('login.html')

@app.route('/')
def dashboard():
    if 'username' not in session:
        flash("You must be logged in to view the dashboard.", "warning")
        return redirect(url_for('login'))

    username = session['username']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get pending challenges
    cursor.execute("SELECT challenger FROM Challenges WHERE opponent = %s AND status = 'pending'", (username,))
    pending_challenges = cursor.fetchall()

    # Get accepted challenges where this user is involved
    cursor.execute(
        """SELECT 
            CASE 
                WHEN challenger = %s THEN opponent 
                ELSE challenger 
            END 
        FROM Challenges 
        WHERE (challenger = %s OR opponent = %s) AND status = 'accepted'""",
        (username, username, username)
    )
    accepted_challenges = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        username=username,
        pending_challenges=pending_challenges,
        accepted_challenges=accepted_challenges
    )

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dbtest')
def db_test():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1;')
        result = cur.fetchone()
        cur.close()
        conn.close()
        return f"✅ Database connection successful! Test query result: {result}"
    except Exception as e:
        return f"❌ Database connection failed: {str(e)}"
    
@app.route('/ladderboard')
def ladderboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Username, Wins, Losses, Points FROM Users ORDER BY Points DESC;")
    ladderboard_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('ladderboard.html', ladderboard=ladderboard_data)


def calculate_points_winner(winner, loser):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch current points safely, default to 0 if NULL
    cursor.execute("SELECT COALESCE(Points, 0) FROM Users WHERE Username = %s", (winner,))
    winner_points = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(Points, 0) FROM Users WHERE Username = %s", (loser,))
    loser_points = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    # Calculate the difference
    point_diff = loser_points - winner_points

    if winner_points < loser_points:
        if point_diff >= 300:
            return int(15 * 3)
        elif point_diff >= 200:
            return int(15 * 2.5)
        elif point_diff >= 100:
            return int(15 * 1.5)
        elif point_diff >= 50:
            return 15
        else:
            return 15

    elif winner_points > loser_points:
        if point_diff >= 300:
            return 5
        elif point_diff >= 200:
            return 10
        elif point_diff >= 100:
            return 10
        elif point_diff >= 50:
            return 15
        else:
            return 15
    
    # If both points are equal (like 0 vs 0)
    return 15

def calculate_points_loser(winner, loser):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch current points safely, default to 0 if NULL
    cursor.execute("SELECT COALESCE(Points, 0) FROM Users WHERE Username = %s", (winner,))
    winner_points = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(Points, 0) FROM Users WHERE Username = %s", (loser,))
    loser_points = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    # Calculate the difference
    point_diff = loser_points - winner_points

    if winner_points < loser_points:
        if point_diff >= 300:
            return int(15 * 2.75)
        elif point_diff >= 200:
            return int(15 * 2.25)
        elif point_diff >= 100:
            return int(15 * 2)
        elif point_diff >= 50:
            return int(15 * 1.5)
        else:
            return 15

    elif winner_points > loser_points:
        if point_diff >= 300:
            return 5
        elif point_diff >= 200:
            return 10
        elif point_diff >= 100:
            return 10
        elif point_diff >= 50:
            return 15
        else:
            return 15

    # If both points are equal (like 0 vs 0)
    return 15

def should_deduct_points(loser):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure NULL values are treated as 0
    cursor.execute("SELECT COALESCE(Points, 0) FROM Users WHERE Username = %s", (loser,))
    loser_points = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return loser_points > 0



@app.route('/submit_result/<opponent>', methods=['GET', 'POST'])
def submit_result(opponent):
    if 'username' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    username = session['username']

    if request.method == 'POST':
        winner = request.form['winner']
        score = request.form['score']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Mark challenge as completed
        cursor.execute("""
            UPDATE Challenges 
            SET status = 'completed', score = %s, winner = %s
            WHERE ((challenger = %s AND opponent = %s) OR (challenger = %s AND opponent = %s))
              AND status = 'accepted'
        """, (score, winner, username, opponent, opponent, username))

        # Update user records
        if winner == username:
            loser = opponent
        else:
            loser = username

        # Update winner stats
        cursor.execute("UPDATE Users SET Wins = Wins + 1, Points = Points + %s WHERE Username = %s", (calculate_points_winner(winner, loser), winner))
        # Update loser stats
        if should_deduct_points(loser):
            cursor.execute("UPDATE Users SET Losses = Losses + 1, Points = Points - %s WHERE Username = %s", (calculate_points_loser(winner, loser), loser))
        else:
            cursor.execute("UPDATE Users SET Losses = Losses + 1 WHERE Username = %s", (loser,))



        conn.commit()
        cursor.close()
        conn.close()

        flash("Match result submitted!", "success")
        return redirect(url_for('dashboard'))

    return render_template('submit_result.html', opponent=opponent)


@app.route('/challenge/<opponent>', methods=['GET', 'POST'])
def challenge(opponent):
    if 'username' not in session:
        flash("You must be logged in to issue a challenge.", "warning")
        return redirect(url_for('login'))

    current_user = session['username']

    # Prevent challenging yourself
    if current_user == opponent:
        flash("You cannot challenge yourself.", "danger")
        return redirect(url_for('ladderboard'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if a challenge already exists
    cursor.execute("SELECT * FROM Challenges WHERE challenger = %s AND opponent = %s AND status = 'pending'", (current_user, opponent))
    existing = cursor.fetchone()

    if existing:
        flash("You have already challenged this player.", "info")
    else:
        # Create the new challenge
        cursor.execute("INSERT INTO Challenges (challenger, opponent, status) VALUES (%s, %s, 'pending')", (current_user, opponent))
        conn.commit()
        flash(f"Challenge sent to {opponent}.", "success")

    cursor.close()
    conn.close()

    return redirect(url_for('ladderboard'))
    

@app.route('/accept/<challenger>', methods=['GET'])
def accept_challenge(challenger):
    if 'username' not in session:
        flash("Login to accept challenges.", "warning")
        return redirect(url_for('login'))

    opponent = session['username']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Challenges SET status = 'accepted' WHERE challenger = %s AND opponent = %s AND status = 'pending'",
        (challenger, opponent)
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"You accepted the challenge from {challenger}.", "success")
    return redirect(url_for('dashboard'))

@app.route('/match_history')
def match_history():
    if 'username' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    username = session['username']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT challenger, opponent, winner, score, created_at
        FROM Challenges
        WHERE status = 'completed'
          AND (challenger = %s OR opponent = %s)
        ORDER BY created_at DESC;
    """, (username, username))
    matches = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('match_history.html', matches=matches)



if __name__ == '__main__':
    app.run(debug=True)
