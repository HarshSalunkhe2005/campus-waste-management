# Campus Food Waste Tracker

A Flask + MySQL web application that helps campuses reduce food waste by connecting canteens with NGOs for timely food donation, request tracking, and impact reporting.

## Project Overview

This platform enables:
- **Canteens** to publish surplus food and manage pickup requests.
- **NGOs** to request available food and report beneficiary impact.
- **Admins** to manage users, logs, reports, and leaderboard insights.

The application includes role-based access control, audit logging, donation workflows, and waste reporting.

## Features

- Multi-role authentication (**Admin / Canteen / NGO**)
- Secure password storage using hashed passwords
- Food listing, expiry-aware views, and inventory updates
- Donation request lifecycle (pending → approved/rejected → completed)
- Waste reporting and impact tracking
- Audit logs, login activity logs, and leaderboard metrics

## Tech Stack

- **Backend:** Python, Flask
- **Database:** MySQL
- **Frontend:** Jinja2 templates, Bootstrap, custom CSS
- **Driver/ORM Layer:** `mysql-connector-python`

## Repository Structure

```text
backend/                 Flask application
db/campus_food_waste_schema.sql
templates/               Jinja templates (admin/canteen/ngo/shared pages)
static/                  CSS/static assets
requirements.txt
```

## Prerequisites

- Python 3.10+
- MySQL 8+
- pip

## Setup

1. Clone repository and enter project root.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Set environment variables before starting the app.

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `FLASK_SECRET_KEY` | Recommended | auto-generated per startup | Secret key for session signing. Set explicitly in persistent environments. |
| `DB_HOST` | No | `localhost` | MySQL host |
| `DB_USER` | No | `root` | MySQL username |
| `DB_PASS` | No | empty | MySQL password |
| `DB_NAME` | No | `campus_food_waste` | Database name |
| `FLASK_DEBUG` | No | `0` | Set `1` only for local development |
| `PORT` | No | `5000` | Flask app port |

Example:

```bash
export FLASK_SECRET_KEY='replace-with-a-random-32+char-secret'
export DB_HOST='localhost'
export DB_USER='root'
export DB_PASS='your-db-password'
export DB_NAME='campus_food_waste'
export FLASK_DEBUG='0'
export PORT='5000'
```

## Database Setup

1. Ensure MySQL server is running.
2. Import schema + seed data:

```bash
mysql -u <user> -p < /absolute/path/to/db/campus_food_waste_schema.sql
```

This script creates database `campus_food_waste`, tables, roles, and sample records.

## Running the Application

From project root:

```bash
python backend/app.py
```

Open:

```text
http://localhost:5000
```

## Default Sample Accounts (from DB seed)

- Admin: `admin1`
- Canteen: `canteen_central`, `canteen_hostel`, `canteen_tech`
- NGO: `ngo_feedinghands`, `ngo_greenplate`, `ngo_helpinghearts`

> Passwords are stored as hashes in the seed and verified securely by the app.

## Screenshots / Placeholders

Add screenshots here if publishing docs externally:
- Home page screenshot placeholder
- Admin dashboard screenshot placeholder
- Canteen dashboard screenshot placeholder
- NGO dashboard screenshot placeholder

## Security Recommendations

- Never commit real credentials in source code.
- Always set `FLASK_SECRET_KEY` from environment/secret manager.
- Use a strong DB password and least-privilege DB user (avoid root in production).
- Keep `FLASK_DEBUG=0` in non-local environments.
- Rotate secrets periodically and after suspected exposure.
- Enforce HTTPS and secure cookies when deploying behind a reverse proxy.
- Restrict admin account creation to authorized admins only.

## Notes

- This version expects hashed passwords in the `users` table (as provided by the schema seed).
