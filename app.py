import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from datetime import datetime, timedelta
from functools import wraps

# -------------------------
# Base Directories & App Setup
# -------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
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
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def canteen_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role", "").lower() != "canteen":
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def ngo_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role", "").lower() != "ngo":
            flash("You do not have permission to access this page.", "error")
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
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username, password = request.form["username"], request.form["password"]
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT u.user_id, u.username, u.ref_id, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.username = %s AND u.password = %s", (username, password))
        user = cursor.fetchone()
        if user:
            session.update(user_id=user["user_id"], username=user["username"], role=user["role_name"], ref_id=user["ref_id"])
            cursor.execute("INSERT INTO login_activity (user_id, ip_address) VALUES (%s,%s)", (user["user_id"], request.remote_addr))
            cursor.close()
            if user["role_name"].lower() == "admin": return redirect(url_for("admin_dashboard"))
            if user["role_name"].lower() == "canteen": return redirect(url_for("canteen_dashboard"))
            if user["role_name"].lower() == "ngo": return redirect(url_for("ngo_dashboard"))
        else:
            error = "Invalid username or password."
            cursor.close()
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =============================================================================
# ADMIN ROUTES
# =============================================================================
@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin/admin.html", user=session)

@app.route("/admin/add_user", methods=["GET", "POST"])
@admin_required
def add_user():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT canteen_id, name FROM canteen")
    canteens = cursor.fetchall()
    cursor.execute("SELECT ngo_id, name FROM ngo")
    ngos = cursor.fetchall()
    error = None
    if request.method == "POST":
        username, email, password, role = request.form["username"].strip(), request.form["email"].strip(), request.form["password"].strip(), request.form["role"]
        ref_id = 0
        if role == "canteen": ref_id = request.form.get("canteen_id")
        elif role == "ngo": ref_id = request.form.get("ngo_id")
        
        cursor.execute("SELECT role_id FROM roles WHERE role_name=%s", (role,))
        role_id = cursor.fetchone()["role_id"]
        
        cursor.execute("SELECT 1 FROM users WHERE username=%s OR email=%s", (username, email))
        if cursor.fetchone():
            error = "Username or Email already exists."
        else:
            cursor.execute("INSERT INTO users (username, password, email, role_id, ref_id) VALUES (%s,%s,%s,%s,%s)", (username, password, email, role_id, ref_id))
            new_user_id = cursor.lastrowid
            write_audit(conn, f"Added user '{username}'", "users", new_user_id, session.get("user_id"))
            flash("User added successfully.", "success")
            return redirect(url_for("admin_dashboard"))
    cursor.close()
    return render_template("admin/add_user.html", canteens=canteens, ngos=ngos, error=error)

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
    return render_template("admin/manage_users.html", users=users, canteens=canteens, ngos=ngos)

@app.route("/admin/view_logs")
@admin_required
def view_logs():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT * FROM audit_log ORDER BY event_time DESC")
    logs = cursor.fetchall()
    return render_template("admin/view_logs.html", logs=logs)

@app.route("/admin/view_activity")
@admin_required
def view_activity():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT la.activity_id, u.username, la.login_time, la.logout_time, la.ip_address FROM login_activity la JOIN users u ON la.user_id = u.user_id ORDER BY la.login_time DESC")
    activities = cursor.fetchall()
    return render_template("admin/view_activity.html", activities=activities)

@app.route("/admin/view_reports")
@admin_required
def view_reports():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT wr.report_id, f.item_name, u.username AS reporter, wr.reason, wr.quantity_wasted, wr.report_time FROM waste_report wr JOIN food f ON wr.food_id=f.food_id JOIN users u ON wr.reported_by=u.user_id ORDER BY wr.report_time DESC")
    reports = cursor.fetchall()
    return render_template("admin/view_reports.html", reports=reports)

@app.route("/admin/view_leaderboard")
@admin_required
def view_leaderboard():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT l.lb_id, c.name AS canteen, l.total_items, l.donated_items, l.waste_score FROM leaderboard l JOIN canteen c ON l.canteen_id=c.canteen_id ORDER BY l.waste_score DESC")
    leaderboard = cursor.fetchall()
    return render_template("admin/view_leaderboard.html", leaderboard=leaderboard)

@app.route("/admin/impact")
@admin_required
def impact():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT mb.beneficiary_id, mb.donation_id, mb.people_served, mb.location, mb.recorded_time FROM meal_beneficiary mb ORDER BY mb.recorded_time DESC")
    impact_data = cursor.fetchall()
    return render_template("admin/impact.html", impact_data=impact_data)

# =============================================================================
# CANTEEN ROUTES
# =============================================================================
@app.route("/canteen")
@canteen_required
def canteen_dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    canteen_id = session['ref_id']
    cursor.execute("SELECT name FROM canteen WHERE canteen_id = %s", (canteen_id,))
    canteen = cursor.fetchone()
    cursor.execute("SELECT * FROM food WHERE canteen_id = %s ORDER BY expiry_time ASC", (canteen_id,))
    food_items = cursor.fetchall()
    now = datetime.now()
    for food in food_items:
        food['expiry_class'] = ''
        if food.get('expiry_time'):
            time_diff = food['expiry_time'] - now
            if time_diff < timedelta(hours=1): food['expiry_class'] = 'expiry-critical'
            elif time_diff < timedelta(hours=3): food['expiry_class'] = 'expiry-warning'
    return render_template("canteen/canteen.html", user=session, food_items=food_items, canteen_name=canteen['name'])

@app.route("/canteen/add_food", methods=['GET', 'POST'])
@canteen_required
def add_food():
    if request.method == 'POST':
        canteen_id = session['ref_id']
        quantity = request.form['quantity']
        item_name = request.form['item_name']
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            print("\n--- LEADERBOARD DEBUG: Attempting to add food ---")
            print(f"--- LEADERBOARD DEBUG: Canteen ID: {canteen_id}, Quantity: {quantity}")
            
            cursor.execute("INSERT INTO food (canteen_id, item_name, category, quantity, unit, expiry_time, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (canteen_id, item_name, request.form['category'], int(quantity), request.form['unit'], request.form['expiry_time'], request.form.get('notes')))
            new_food_id = cursor.lastrowid
            
            cursor.execute("UPDATE leaderboard SET total_items = total_items + %s WHERE canteen_id = %s", (int(quantity), canteen_id))
            print(f"--- LEADERBOARD DEBUG: UPDATE command executed for total_items.")

            write_audit(conn, f"Added food '{item_name}'", "food", new_food_id, session.get("user_id"))
            flash("Food item added successfully!", "success")

        except Exception as e:
            print(f"--- LEADERBOARD DEBUG: An error occurred in add_food: {e}")
            flash("An error occurred while adding food.", "error")

        return redirect(url_for('canteen_dashboard'))

    return render_template("canteen/add_food.html", user=session)

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
        SELECT dr.request_id, f.item_name, n.name AS ngo_name, dr.request_time, dr.status
        FROM donation_request dr JOIN food f ON dr.food_id = f.food_id JOIN ngo n ON dr.ngo_id = n.ngo_id
        WHERE f.canteen_id = %s ORDER BY dr.request_time DESC
    """, (canteen_id,))
    requests = cursor.fetchall()
    return render_template('canteen/manage_requests.html', user=session, requests=requests)

@app.route("/canteen/edit_food/<int:food_id>", methods=['GET', 'POST'])
@canteen_required
def edit_food(food_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM food WHERE food_id = %s AND canteen_id = %s", (food_id, session['ref_id']))
    food = cursor.fetchone()
    if not food:
        flash("Food item not found or you don't have permission to edit it.", "error")
        return redirect(url_for('canteen_dashboard'))
    if request.method == 'POST':
        item_name, category, quantity, unit, expiry_time, notes = request.form['item_name'], request.form['category'], request.form['quantity'], request.form['unit'], request.form['expiry_time'], request.form.get('notes')
        update_cursor = conn.cursor()
        update_cursor.execute("UPDATE food SET item_name=%s, category=%s, quantity=%s, unit=%s, expiry_time=%s, notes=%s WHERE food_id=%s",
                              (item_name, category, quantity, unit, expiry_time, notes, food_id))
        write_audit(conn, f"Edited food '{item_name}'", "food", food_id, session.get("user_id"))
        flash(f"'{item_name}' updated successfully!", "success")
        return redirect(url_for('canteen_dashboard'))
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
    return redirect(url_for('canteen_dashboard'))

@app.route("/canteen/file_waste_report", methods=['GET', 'POST'])
@canteen_required
def file_waste_report():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    canteen_id = session['ref_id']
    if request.method == 'POST':
        food_id, reason, quantity_wasted, reported_by = request.form.get('food_id'), request.form.get('reason'), request.form.get('quantity_wasted'), session['user_id']
        cursor.execute("SELECT quantity FROM food WHERE food_id = %s", (food_id,))
        food = cursor.fetchone()
        if not food or int(quantity_wasted) > food['quantity']:
            flash("Cannot report more waste than available quantity.", "error")
        else:
            insert_cursor = conn.cursor()
            insert_cursor.execute("INSERT INTO waste_report (food_id, reported_by, reason, quantity_wasted) VALUES (%s, %s, %s, %s)",
                                  (food_id, reported_by, reason, quantity_wasted))
            new_report_id = insert_cursor.lastrowid
            new_quantity = food['quantity'] - int(quantity_wasted)
            insert_cursor.execute("UPDATE food SET quantity = %s WHERE food_id = %s", (new_quantity, food_id))
            write_audit(conn, f"Filed waste report for food_id {food_id}", "waste_report", new_report_id, session.get("user_id"))
            flash("Waste report filed successfully.", "success")
            return redirect(url_for('canteen_dashboard'))
    
    cursor.execute("SELECT food_id, item_name, expiry_time FROM food WHERE canteen_id = %s AND status = 'available' AND quantity > 0", (canteen_id,))
    available_food = cursor.fetchall()
    cursor.close()
    return render_template("canteen/file_waste_report.html", user=session, available_food=available_food)

@app.route("/canteen/leaderboard")
@canteen_required
def canteen_leaderboard():
    conn, canteen_id = get_db(), session['ref_id']
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT l.canteen_id, c.name, l.waste_score FROM leaderboard l JOIN canteen c ON l.canteen_id = c.canteen_id ORDER BY l.waste_score DESC")
    full_leaderboard = cursor.fetchall()
    your_rank, your_score = None, None
    for i, canteen in enumerate(full_leaderboard):
        if canteen['canteen_id'] == canteen_id:
            your_rank, your_score = i + 1, canteen['waste_score']
            break
    top_canteens = full_leaderboard[:3]
    return render_template("canteen/view_leaderboard.html", user=session, your_rank=your_rank, your_score=your_score, top_canteens=top_canteens, your_canteen_id=canteen_id)

# =============================================================================
# NGO ROUTES
# =============================================================================
@app.route("/ngo")
@ngo_required
def ngo_dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    ngo_id = session['ref_id']
    cursor.execute("SELECT name FROM ngo WHERE ngo_id = %s", (ngo_id,))
    ngo = cursor.fetchone()
    cursor.execute("""
        SELECT f.food_id, f.item_name, f.quantity, f.unit, f.expiry_time, c.name AS canteen_name
        FROM food f JOIN canteen c ON f.canteen_id = c.canteen_id
        WHERE f.status = 'available' AND f.quantity > 0 ORDER BY f.expiry_time ASC
    """)
    available_food = cursor.fetchall()
    return render_template("ngo/ngo.html", user=session, ngo_name=ngo['name'], available_food=available_food)

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
    return redirect(url_for('ngo_dashboard'))

@app.route("/ngo/history")
@ngo_required
def ngo_donation_history():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    ngo_id = session['ref_id']
    cursor.execute("""
        SELECT f.item_name, c.name AS canteen_name, dr.request_id, dr.request_time, dr.status
        FROM donation_request dr JOIN food f ON dr.food_id = f.food_id JOIN canteen c ON f.canteen_id = c.canteen_id
        WHERE dr.ngo_id = %s ORDER BY dr.request_time DESC
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

        print("\n--- LEADERBOARD DEBUG: Attempting to record beneficiaries ---")
        print(f"--- LEADERBOARD DEBUG: donation_request_id: {donation_request_id}")

        if not donation_request_id:
            flash("Please select a completed donation to report on.", "error")
        else:
            try:
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

                    print(f"--- LEADERBOARD DEBUG: Found food_info. Canteen to update: {canteen_id_to_update}, Donated quantity: {quantity}")

                    cursor.execute("INSERT INTO meal_beneficiary (donation_id, people_served, location) VALUES (%s, %s, %s)",
                                          (donation_request_id, people_served, location))
                    new_beneficiary_id = cursor.lastrowid

                    cursor.execute("UPDATE donation_request SET status = 'completed' WHERE request_id = %s", (donation_request_id,))
                    cursor.execute("UPDATE food SET status = 'donated' WHERE food_id = %s", (food_id,))
                    
                    cursor.execute("UPDATE leaderboard SET donated_items = donated_items + %s WHERE canteen_id = %s", (int(quantity), canteen_id_to_update))
                    print(f"--- LEADERBOARD DEBUG: UPDATE command executed for donated_items.")
                    
                    write_audit(conn, f"Recorded beneficiaries for request_id {donation_request_id}", "meal_beneficiary", new_beneficiary_id, session.get("user_id"))
                    flash("Impact report submitted successfully!", "success")
                else:
                    print(f"--- LEADERBOARD DEBUG: Could not find food_info for request {donation_request_id}")
                    flash("Could not find the original donation. Report failed.", "error")
            
            except Exception as e:
                print(f"--- LEADERBOARD DEBUG: An error occurred in record_beneficiaries: {e}")
                flash("An error occurred while submitting the report.", "error")

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
    app.run(debug=True)