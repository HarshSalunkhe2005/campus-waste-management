import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------
# Base Directories & App Setup
# -------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.secret_key = "supersecretkey"

# -------------------------
# DB Config & Management
# -------------------------
DB_HOST, DB_USER, DB_PASS, DB_NAME = "localhost", "root", "root", "campus_food_waste"

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=DB_HOST, 
            user=DB_USER, 
            password=DB_PASS, 
            database=DB_NAME,
            autocommit=True
        )
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None: db.close()

# -------------------------
# Decorators
# -------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role", "").lower() != "admin":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def canteen_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role", "").lower() != "canteen":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def ngo_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role", "").lower() != "ngo":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------
# Helpers
# -------------------------
def write_audit(conn, action_text, table_name, record_id, performed_by):
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO audit_log (action, table_name, record_id, performed_by) VALUES (%s,%s,%s,%s)",
                    (action_text, table_name, record_id, performed_by))
        cur.close()
    except Exception as e:
        print(f"--- AUDIT LOG FAILED --- {e}")

# =============================================================================
# AUTH & GENERAL ROUTES
# =============================================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username, password = request.form["username"], request.form["password"]
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT u.user_id, u.username, u.password, u.ref_id, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.username = %s", (username,))
        user = cursor.fetchone()
        
        # Plaintext password check to match your new SQL file
        if user and user['password'] == password:
            session.update(user_id=user["user_id"], username=user["username"], role=user["role_name"], ref_id=user["ref_id"])
            cursor.execute("INSERT INTO login_activity (user_id, ip_address) VALUES (%s,%s)", (user["user_id"], request.remote_addr))
            cursor.close()
            
            flash(f"Welcome back, {user['username']}!", 'success')
            
            if user["role_name"].lower() == "admin": 
                return redirect(url_for("admin_dashboard"))
            if user["role_name"].lower() == "canteen": 
                return redirect(url_for("canteen_dashboard"))
            if user["role_name"].lower() == "ngo": 
                return redirect(url_for("ngo_dashboard"))
        else:
            flash("Invalid username or password.", "danger")
            cursor.close()
            
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password'] # Saving as plaintext
        role_name = request.form['role']
        
        ref_id = 0
        if role_name == 'canteen':
            ref_id = request.form.get('canteen_id')
        elif role_name == 'ngo':
            ref_id = request.form.get('ngo_id')

        try:
            cursor.execute("SELECT role_id FROM roles WHERE role_name = %s", (role_name,))
            role_id = cursor.fetchone()['role_id']
            
            cursor.execute("INSERT INTO users (username, email, password, role_id, ref_id) VALUES (%s, %s, %s, %s, %s)",
                           (username, email, password, role_id, ref_id))
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            if err.errno == 1062: # Duplicate entry
                flash("Username or email already exists.", "danger")
            else:
                flash(f"An error occurred: {err.msg}", "danger")
        
        return redirect(url_for('register'))

    cursor.execute("SELECT canteen_id, name FROM canteen")
    canteens = cursor.fetchall()
    cursor.execute("SELECT ngo_id, name FROM ngo")
    ngos = cursor.fetchall()
    cursor.close()
    
    return render_template("register.html", canteens=canteens, ngos=ngos)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

# =============================================================================
# ADMIN ROUTES
# =============================================================================
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute("SELECT SUM(quantity) as total_food FROM food")
    total_food = cursor.fetchone()['total_food'] or 0
    
    cursor.execute("SELECT COUNT(*) as total_donations FROM donation_request WHERE status = 'completed'")
    total_donations = cursor.fetchone()['total_donations']
    
    cursor.close()
    
    return render_template("admin/admin.html", 
                           user=session, 
                           total_users=total_users, 
                           total_food=total_food, 
                           total_donations=total_donations)

@app.route("/admin/add_user", methods=["GET", "POST"])
@admin_required
def add_user():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        role = request.form["role"]
        ref_id = 0
        if role == "canteen": ref_id = request.form.get("canteen_id")
        elif role == "ngo": ref_id = request.form.get("ngo_id")
        
        cursor.execute("SELECT role_id FROM roles WHERE role_name=%s", (role,))
        role_id = cursor.fetchone()["role_id"]
        
        try:
            cursor.execute("INSERT INTO users (username, password, email, role_id, ref_id) VALUES (%s,%s,%s,%s,%s)", (username, password, email, role_id, ref_id))
            new_user_id = cursor.lastrowid
            write_audit(conn, f"Added user '{username}'", "users", new_user_id, session.get("user_id"))
            flash("User added successfully.", "success")
            return redirect(url_for("admin_dashboard"))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash("Username or Email already exists.", "danger")
            else:
                flash(f"An error occurred: {err.msg}", "danger")
            
    cursor.execute("SELECT canteen_id, name FROM canteen")
    canteens = cursor.fetchall()
    cursor.execute("SELECT ngo_id, name FROM ngo")
    ngos = cursor.fetchall()
    cursor.close()
    return render_template("admin/add_user.html", canteens=canteens, ngos=ngos, user=session)

@app.route("/admin/manage_users", methods=["GET", "POST"])
@admin_required
def manage_users():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        if "delete" in request.form:
            uid = request.form["delete"]
            cursor.execute("SELECT username FROM users WHERE user_id=%s", (uid,))
            uname = cursor.fetchone()["username"]
            cursor.execute("DELETE FROM users WHERE user_id=%s", (uid,))
            write_audit(conn, f"Deleted user '{uname}'", "users", uid, session.get("user_id"))
            flash("User deleted successfully.", "success")
        elif "edit" in request.form:
            uid = request.form["edit"]
            username, email, password, role = request.form[f"username_{uid}"].strip(), request.form[f"email_{uid}"].strip(), request.form[f"password_{uid}"].strip(), request.form[f"role_{uid}"]
            ref_id = 0
            if role == "canteen": ref_id = request.form.get(f"canteen_id_{uid}")
            elif role == "ngo": ref_id = request.form.get(f"ngo_id_{uid}")
            cursor.execute("SELECT role_id FROM roles WHERE role_name=%s", (role,))
            role_id = cursor.fetchone()["role_id"]
            query_parts = ["UPDATE users SET username=%s, email=%s, role_id=%s, ref_id=%s"]
            params = [username, email, role_id, ref_id]
            if password:
                query_parts.append(", password=%s")
                params.append(password)
            query_parts.append("WHERE user_id=%s")
            params.append(uid)
            cursor.execute(" ".join(query_parts), tuple(params))
            write_audit(conn, f"Updated user '{username}'", "users", uid, session.get("user_id"))
            flash("Changes saved successfully.", "success")
        return redirect(url_for("manage_users"))
    
    cursor.execute("SELECT canteen_id, name FROM canteen")
    canteens = cursor.fetchall()
    cursor.execute("SELECT ngo_id, name FROM ngo")
    ngos = cursor.fetchall()
    cursor.execute("SELECT u.user_id, u.username, u.email, u.password, r.role_name, u.ref_id FROM users u JOIN roles r ON u.role_id = r.role_id ORDER BY u.user_id ASC")
    users = cursor.fetchall()
    cursor.close()
    return render_template("admin/manage_users.html", user=session, users=users, canteens=canteens, ngos=ngos)

@app.route("/admin/view_logs")
@admin_required
def view_logs():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT * FROM audit_log ORDER BY event_time DESC")
    logs = cursor.fetchall()
    return render_template("admin/view_logs.html", user=session, logs=logs)

@app.route("/admin/view_activity")
@admin_required
def view_activity():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT la.activity_id, u.username, la.login_time, la.logout_time, la.ip_address FROM login_activity la JOIN users u ON la.user_id = u.user_id ORDER BY la.login_time DESC")
    activities = cursor.fetchall()
    return render_template("admin/view_activity.html", user=session, activities=activities)

@app.route("/admin/view_reports")
@admin_required
def view_reports():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT wr.report_id, f.item_name, u.username AS reporter, wr.reason, wr.quantity_wasted, wr.report_time FROM waste_report wr JOIN food f ON wr.food_id=f.food_id JOIN users u ON wr.reported_by=u.user_id ORDER BY wr.report_time DESC")
    reports = cursor.fetchall()
    return render_template("admin/view_reports.html", user=session, reports=reports)

@app.route("/admin/view_leaderboard")
@admin_required
def view_leaderboard():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT l.lb_id, c.name AS canteen_name, c.location, l.total_items, l.donated_items, l.waste_score FROM leaderboard l JOIN canteen c ON l.canteen_id=c.canteen_id ORDER BY l.waste_score DESC")
    leaderboard = cursor.fetchall()
    return render_template("leaderboard.html", user=session, leaderboard=leaderboard, title="Full Leaderboard")

@app.route("/admin/impact")
@admin_required
def impact():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT mb.beneficiary_id, mb.donation_id, mb.people_served, mb.location, mb.recorded_time FROM meal_beneficiary mb ORDER BY mb.recorded_time DESC")
    impact_data = cursor.fetchall()
    return render_template("admin/impact.html", user=session, impact_data=impact_data)

# =============================================================================
# CANTEEN ROUTES
# =============================================================================
@app.route("/canteen/dashboard")
@canteen_required
def canteen_dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    canteen_id = session['ref_id']
    
    cursor.execute("SELECT name FROM canteen WHERE canteen_id = %s", (canteen_id,))
    canteen = cursor.fetchone()

    cursor.execute("""
        SELECT 
            SUM(quantity) as total,
            SUM(CASE WHEN status = 'available' THEN quantity ELSE 0 END) as available,
            SUM(CASE WHEN status = 'donated' THEN quantity ELSE 0 END) as donated
        FROM food WHERE canteen_id = %s
    """, (canteen_id,))
    stats = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) as pending
        FROM donation_request dr
        JOIN food f ON dr.food_id = f.food_id
        WHERE f.canteen_id = %s AND dr.status = 'pending'
    """, (canteen_id,))
    stats['pending'] = cursor.fetchone()['pending']
    
    cursor.execute("SELECT * FROM leaderboard WHERE canteen_id = %s", (canteen_id,))
    leaderboard = cursor.fetchone()
    
    cursor.execute("""
        SELECT f.item_name, f.quantity, f.unit, n.name as ngo_name, dr.approved_time as donated_time
        FROM donation_request dr
        JOIN food f ON dr.food_id = f.food_id
        JOIN ngo n ON dr.ngo_id = n.ngo_id
        WHERE f.canteen_id = %s AND dr.status IN ('approved', 'completed')
        ORDER BY dr.approved_time DESC LIMIT 5
    """, (canteen_id,))
    recent_donations = cursor.fetchall()
    
    cursor.close()
    
    return render_template("canteen/canteen.html", 
                           user=session, 
                           canteen_name=canteen['name'],
                           stats=stats,
                           leaderboard=leaderboard,
                           recent_donations=recent_donations)

@app.route("/canteen/add_food", methods=['GET', 'POST'])
@canteen_required
def add_food():
    if request.method == 'POST':
        canteen_id, item_name, category, quantity, unit, expiry_time, notes = session['ref_id'], request.form['item_name'], request.form['category'], request.form['quantity'], request.form['unit'], request.form['expiry_time'], request.form.get('notes')
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO food (canteen_id, item_name, category, quantity, unit, expiry_time, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (canteen_id, item_name, category, int(quantity), unit, expiry_time, notes))
            new_food_id = cursor.lastrowid
            
            cursor.execute("UPDATE leaderboard SET total_items = total_items + %s WHERE canteen_id = %s", (int(quantity), canteen_id))
            
            write_audit(conn, f"Added food '{item_name}'", "food", new_food_id, session.get("user_id"))
            flash("Food item added successfully!", "success")
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")

        return redirect(url_for('canteen_dashboard'))

    return render_template("canteen/add_food.html", user=session)
    
@app.route("/canteen/food_list")
@canteen_required
def canteen_food_list():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    canteen_id = session['ref_id']
    
    cursor.execute("SELECT name FROM canteen WHERE canteen_id = %s", (canteen_id,))
    canteen_name = cursor.fetchone()['name']
    
    cursor.execute("SELECT *, %s as canteen_name FROM food WHERE canteen_id = %s ORDER BY expiry_time ASC", (canteen_name, canteen_id))
    food_items = cursor.fetchall()
    
    now = datetime.now()
    for food in food_items:
        food['expiry_class'] = ''
        if food.get('expiry_time'):
            time_diff = food['expiry_time'] - now
            if time_diff < timedelta(hours=1): food['expiry_class'] = 'expiry-critical'
            elif time_diff < timedelta(hours=3): food['expiry_class'] = 'expiry-warning'

    return render_template("food_list.html", user=session, food_items=food_items, title=f"My Food Items ({canteen_name})")

@app.route("/canteen/edit_food/<int:food_id>", methods=['GET', 'POST'])
@canteen_required
def edit_food(food_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM food WHERE food_id = %s AND canteen_id = %s", (food_id, session['ref_id']))
    food = cursor.fetchone()
    if not food:
        flash("Food item not found or you don't have permission to edit it.", "error")
        return redirect(url_for('canteen_food_list'))
    if request.method == 'POST':
        item_name, category, quantity, unit, expiry_time, notes = request.form['item_name'], request.form['category'], request.form['quantity'], request.form['unit'], request.form['expiry_time'], request.form.get('notes')
        update_cursor = conn.cursor()
        update_cursor.execute("UPDATE food SET item_name=%s, category=%s, quantity=%s, unit=%s, expiry_time=%s, notes=%s WHERE food_id=%s",
                              (item_name, category, quantity, unit, expiry_time, notes, food_id))
        write_audit(conn, f"Edited food '{item_name}'", "food", food_id, session.get("user_id"))
        flash(f"'{item_name}' updated successfully!", "success")
        return redirect(url_for('canteen_food_list'))
    return render_template("canteen/edit_food.html", user=session, food=food)

@app.route("/canteen/delete_food/<int:food_id>")
@canteen_required
def delete_food(food_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT item_name FROM food WHERE food_id = %s AND canteen_id = %s", (food_id, session['ref_id']))
    food = cursor.fetchone()
    if food:
        item_name = food['item_name']
        delete_cursor = conn.cursor()
        delete_cursor.execute("DELETE FROM food WHERE food_id = %s", (food_id,))
        write_audit(conn, f"Deleted food '{item_name}'", "food", food_id, session.get("user_id"))
        flash(f"'{item_name}' has been deleted.", "success")
    else:
        flash("Food item not found or you don't have permission to delete it.", "error")
    return redirect(url_for('canteen_food_list'))

@app.route('/canteen/manage_requests', methods=['GET', 'POST'])
@canteen_required
def manage_requests():
    conn, canteen_id = get_db(), session['ref_id']
    if request.method == 'POST':
        request_id, action = request.form['request_id'], request.form['action']
        new_status = 'approved' if action == 'approve' else 'rejected'
        cursor = conn.cursor(dictionary=True)
        cursor.execute("UPDATE donation_request SET status = %s, approved_by = %s, approved_time = NOW() WHERE request_id = %s",
                       (new_status, session['user_id'], request_id))
        cursor.execute("SELECT food_id FROM donation_request WHERE request_id = %s", (request_id,))
        result = cursor.fetchone()
        if result:
            food_id_to_update = result['food_id']
            food_status_update = 'available' if action == 'reject' else 'approved'
            cursor.execute("UPDATE food SET status = %s WHERE food_id = %s", (food_status_update, food_id_to_update,))
        write_audit(conn, f"Request {request_id} was {new_status}", "donation_request", request_id, session.get("user_id"))
        flash(f"Request has been {new_status}.", "success")
        return redirect(url_for('manage_requests'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT dr.request_id, f.item_name, f.quantity, f.unit, n.name AS ngo_name, n.phone, dr.request_time, dr.status
        FROM donation_request dr 
        JOIN food f ON dr.food_id = f.food_id 
        JOIN ngo n ON dr.ngo_id = n.ngo_id
        WHERE f.canteen_id = %s AND dr.status = 'pending' 
        ORDER BY dr.request_time DESC
    """, (canteen_id,))
    requests = cursor.fetchall()
    return render_template('canteen/manage_requests.html', user=session, requests=requests)

@app.route("/canteen/file_waste_report", methods=['GET', 'POST'])
@canteen_required
def file_waste_report():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        food_id, reason, quantity_wasted, reported_by = request.form.get('food_id'), request.form.get('reason'), request.form.get('quantity_wasted'), session['user_id']
        
        # 1. Fetch current quantity
        cursor.execute("SELECT quantity FROM food WHERE food_id = %s", (food_id,))
        food = cursor.fetchone()
        
        if not food:
            flash("Food item not found.", "danger")
            return redirect(url_for('canteen_dashboard'))

        current_quantity = food['quantity']
        wasted = int(quantity_wasted)
        
        if wasted > current_quantity:
            flash("Cannot report more waste than available quantity.", "danger")
        else:
            new_quantity = current_quantity - wasted
            insert_cursor = conn.cursor()
            
            # 2. Insert the waste report
            insert_cursor.execute("INSERT INTO waste_report (food_id, reported_by, reason, quantity_wasted) VALUES (%s, %s, %s, %s)",
                                  (food_id, reported_by, reason, wasted))
            new_report_id = insert_cursor.lastrowid
            
            # 3. FIX: Check if new quantity is zero and DELETE the record instead of setting quantity to 0.
            if new_quantity == 0:
                insert_cursor.execute("DELETE FROM food WHERE food_id = %s", (food_id,))
                status_message = "Food item fully wasted and removed from inventory."
            else:
                insert_cursor.execute("UPDATE food SET quantity = %s WHERE food_id = %s", (new_quantity, food_id))
                status_message = "Waste report filed successfully."
                
            write_audit(conn, f"Filed waste report (qty: {wasted}) for food_id {food_id}", "waste_report", new_report_id, session.get("user_id"))
            flash(status_message, "success")
            return redirect(url_for('canteen_dashboard'))
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    canteen_id = session['ref_id']
    cursor.execute("SELECT food_id, item_name, expiry_time FROM food WHERE canteen_id = %s AND status = 'available' AND quantity > 0", (canteen_id,))
    available_food = cursor.fetchall()
    cursor.close()
    return render_template("canteen/file_waste_report.html", user=session, available_food=available_food)

@app.route("/canteen/leaderboard")
@canteen_required
def canteen_leaderboard():
    conn, canteen_id = get_db(), session['ref_id']
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT l.canteen_id, c.name as canteen_name, c.location, l.total_items, l.donated_items, l.waste_score FROM leaderboard l JOIN canteen c ON l.canteen_id = c.canteen_id ORDER BY l.waste_score DESC")
    full_leaderboard = cursor.fetchall()
    return render_template("leaderboard.html", user=session, leaderboard=full_leaderboard, title="Canteen Leaderboard", your_canteen_id=canteen_id)

# =============================================================================
# NGO ROUTES
# =============================================================================
@app.route("/ngo/dashboard")
@ngo_required
def ngo_dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    ngo_id = session['ref_id']
    
    cursor.execute("SELECT name FROM ngo WHERE ngo_id = %s", (ngo_id,))
    ngo = cursor.fetchone()

    cursor.execute("""
        SELECT 
            COUNT(*) as total_requests,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
        FROM donation_request WHERE ngo_id = %s
    """, (ngo_id,))
    stats = cursor.fetchone()
    
    cursor.execute("SELECT SUM(people_served) as total_meals FROM meal_beneficiary mb JOIN donation_request dr ON mb.donation_id = dr.request_id WHERE dr.ngo_id = %s", (ngo_id,))
    stats['total_meals'] = cursor.fetchone()['total_meals'] or 0

    return render_template("ngo/ngo.html", user=session, ngo_name=ngo['name'], stats=stats)

@app.route("/ngo/food_list")
@ngo_required
def ngo_food_list():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.*, c.name as canteen_name 
        FROM food f JOIN canteen c ON f.canteen_id = c.canteen_id
        WHERE f.status = 'available' AND f.quantity > 0 
        ORDER BY f.expiry_time ASC
    """)
    food_items = cursor.fetchall()
    return render_template("food_list.html", user=session, food_items=food_items, title="Available Food for Donation")

@app.route("/ngo/request", methods=['POST'])
@ngo_required
def request_pickup():
    food_id, ngo_id = request.form.get('food_id'), session['ref_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM donation_request WHERE food_id = %s AND ngo_id = %s", (food_id, ngo_id))
    if cursor.fetchone():
        flash("You have already requested this item.", "error")
    else:
        cursor.execute("INSERT INTO donation_request (food_id, ngo_id) VALUES (%s, %s)", (food_id, ngo_id))
        new_request_id = cursor.lastrowid
        cursor.execute("UPDATE food SET status = 'requested' WHERE food_id = %s", (food_id,))
        write_audit(conn, f"NGO request for food_id {food_id}", "donation_request", new_request_id, session.get("user_id"))
        flash("Request sent successfully!", "success")
    return redirect(url_for('ngo_food_list'))

@app.route("/ngo/history")
@ngo_required
def ngo_donation_history():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    ngo_id = session['ref_id']
    
    # THIS IS THE UPDATED QUERY
    cursor.execute("""
        SELECT 
            f.item_name, 
            f.category, 
            f.quantity, 
            f.unit, 
            c.name AS canteen_name, 
            n.name AS ngo_name, 
            dr.request_id, 
            dr.request_time, 
            dr.status, 
            dr.approved_time as donated_time
        FROM donation_request dr 
        JOIN food f ON dr.food_id = f.food_id 
        JOIN canteen c ON f.canteen_id = c.canteen_id
        JOIN ngo n ON dr.ngo_id = n.ngo_id
        WHERE dr.ngo_id = %s 
        ORDER BY dr.request_time DESC
    """, (ngo_id,))
    history = cursor.fetchall()
    return render_template("ngo/donation_history.html", user=session, history=history)

@app.route("/ngo/record_beneficiaries", methods=['GET', 'POST'])
@ngo_required
def ngo_record_beneficiaries():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    ngo_id = session['ref_id']
    if request.method == 'POST':
        donation_request_id = request.form.get('donation_id')
        people_served = request.form.get('people_served')
        location = request.form.get('location')
        if not donation_request_id:
            flash("Please select a completed donation to report on.", "error")
        else:
            cursor.execute("""
                SELECT f.food_id, f.quantity, f.canteen_id 
                FROM food f JOIN donation_request dr ON f.food_id = dr.food_id
                WHERE dr.request_id = %s
            """, (donation_request_id,))
            food_info = cursor.fetchone()
            if food_info:
                food_id = food_info['food_id']
                quantity = food_info['quantity']
                canteen_id_to_update = food_info['canteen_id']

                cursor.execute("INSERT INTO meal_beneficiary (donation_id, people_served, location) VALUES (%s, %s, %s)",
                                      (donation_request_id, people_served, location))
                new_beneficiary_id = cursor.lastrowid

                cursor.execute("UPDATE donation_request SET status = 'completed' WHERE request_id = %s", (donation_request_id,))
                cursor.execute("UPDATE food SET status = 'donated' WHERE food_id = %s", (food_id,))
                cursor.execute("UPDATE leaderboard SET donated_items = donated_items + %s WHERE canteen_id = %s", (int(quantity), canteen_id_to_update))
                
                write_audit(conn, f"Recorded beneficiaries for request_id {donation_request_id}", "meal_beneficiary", new_beneficiary_id, session.get("user_id"))
                flash("Impact report submitted successfully!", "success")
            else:
                flash("Could not find the original donation. Report failed.", "error")
            return redirect(url_for('ngo_donation_history'))
    
    cursor.execute("""
        SELECT dr.request_id AS donation_id, f.item_name, c.name as canteen_name, dr.approved_time
        FROM donation_request dr JOIN food f ON dr.food_id = f.food_id JOIN canteen c ON f.canteen_id = c.canteen_id
        WHERE dr.ngo_id = %s AND dr.status = 'approved' ORDER BY dr.approved_time DESC
    """, (ngo_id,))
    completed_donations = cursor.fetchall()
    return render_template("ngo/record_beneficiaries.html", user=session, completed_donations=completed_donations)

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)