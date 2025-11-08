Flask Ladder & Challenge System

A web application built with Flask and PostgreSQL that allows users to issue and accept challenges, track match results, and maintain a dynamic leaderboard.

Features

User Authentication: Secure login and session management.

Challenge System: Users can challenge each other, accept challenges, and submit match results.

Dynamic Ladderboard: Points and rankings are automatically calculated based on wins, losses, and relative player scores.

Match History: View past match results with scores, winners, and timestamps.

Database Integration: PostgreSQL backend with connection testing and environment variable configuration.

Point Calculation System: Intelligent point allocation based on winner-loser comparisons, including point deductions for losses.

Responsive Flash Messages: Inform users about challenge statuses, errors, and updates.

Tech Stack

Backend: Python, Flask

Database: PostgreSQL

Templating: Jinja2 (Flask templates)

Environment Management: dotenv

Setup

Clone the repository.

Create a .env file with:

SECRET_KEY=your_secret_key
DATABASE_URL=your_postgresql_connection_url


Install dependencies:

pip install -r requirements.txt


Run the app:

python app.py
