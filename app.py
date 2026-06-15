import sys
import os

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('TF_NUM_INTEROP_THREADS', '1')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS', '1')

import time
import sqlite3
import hashlib
import base64
import csv
from flask import Flask, render_template, request, redirect, send_file, send_from_directory, jsonify, session, url_for
from werkzeug.utils import secure_filename
from ai_generator import AIAger
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.secret_key = 'FORENSIC_SUPER_SECRET_KEY_999'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

forensic_suite = AIAger()
executor = ThreadPoolExecutor(max_workers=4)
ACTIVE_TASKS = {}  
TASK_TIMEOUT_SECONDS = 600

def _init_auth_db():
    conn = sqlite3.connect('forensic_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        default_users = [
            ('guest_user', hashlib.sha256('user123'.encode()).hexdigest(), 'user'),
            ('site_admin', hashlib.sha256('admin123'.encode()).hexdigest(), 'admin'),
            ('master_zookeeper', hashlib.sha256('zoo123'.encode()).hexdigest(), 'zookeeper')
        ]
        cursor.executemany('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', default_users)
        conn.commit()
    conn.close()

_init_auth_db()

def verify_database_chain_integrity():
    conn = sqlite3.connect('forensic_history.db')
    cursor = conn.cursor()
    cursor.execute('SELECT file_hash, dft_score, gan_signature, block_hash FROM cases ORDER BY id ASC')
    rows = cursor.fetchall()
    conn.close()
    if not rows: return True, "Chain Empty (Secure)"
    prev_hash = "GENESIS_BLOCK_0000"
    for file_hash, dft_score, gan_signature, logged_block_hash in rows:
        consensus_score = int((dft_score * 0.65) + (35 if "StyleGAN" in gan_signature or "Diffusion" in gan_signature else 0))
        check_string = f"{prev_hash}-{file_hash}-{consensus_score}-{gan_signature}"
        calculated_hash = hashlib.sha256(check_string.encode('utf-8')).hexdigest()
        if calculated_hash != logged_block_hash:
            return False, f"🔴 WARNING: Integrity Fault Found at File Signature Block {file_hash[:10]}..."
        prev_hash = logged_block_hash
    return True, "🟢 Verified Chain Custody Secured via Cryptographic Ledger"

@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login_page'))
    filter_verdict = request.args.get('verdict', 'ALL')
    conn = sqlite3.connect('forensic_history.db')
    cursor = conn.cursor()
    if filter_verdict == 'DEEPFAKE':
        cursor.execute('SELECT filename, timestamp, final_verdict FROM cases WHERE final_verdict LIKE "%🚨%" ORDER BY id DESC')
    elif filter_verdict == 'AUTHENTIC':
        cursor.execute('SELECT filename, timestamp, final_verdict FROM cases WHERE final_verdict LIKE "%🟢%" ORDER BY id DESC')
    else:
        cursor.execute('SELECT filename, timestamp, final_verdict FROM cases ORDER BY id DESC LIMIT 10')
    history = cursor.fetchall()
    conn.close()
    
    task_id = request.args.get('task_id')
    return render_template('index.html', history=history, current_user=session['username'], current_role=session['role'], active_filter=filter_verdict, loading_task_id=task_id)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        conn = sqlite3.connect('forensic_history.db')
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE username=? AND password=?', (username, hashed_pw))
        user_match = cursor.fetchone()
        conn.close()
        if user_match:
            session['username'] = username
            session['role'] = user_match[0]
            return redirect(url_for('index'))
        else:
            error = "🚨 INVALID ACCESS CREDENTIALS"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout_action():
    session.clear()
    return redirect(url_for('login_page'))

def async_heavy_math_task(input_path, filename, task_id):
    try:
        log_output_path = forensic_suite.age_face(input_path)
        manifest_data = []
        with open(log_output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split("||")
                    if len(parts) == 2: manifest_data.append({"metric": parts[0], "value": parts[1]})
        
        timestamp = int(time.time())
        base_name, _ = os.path.splitext(filename)
        normalized_filename = f"normalized_{base_name}.jpg"
        
        clean_input_path = os.path.join(UPLOAD_FOLDER, normalized_filename).replace('\\', '/')
        clean_hud_path = os.path.join(UPLOAD_FOLDER, 'hud_' + filename).replace('\\', '/')
        clean_dft_path = os.path.join(UPLOAD_FOLDER, 'dft_' + filename).replace('\\', '/')
        clean_ela_path = os.path.join(UPLOAD_FOLDER, 'ela_' + filename).replace('\\', '/')
        clean_heatmap_path = os.path.join(UPLOAD_FOLDER, 'heatmap_' + filename).replace('\\', '/')
        
        ACTIVE_TASKS[task_id] = {
            "status": "SUCCESS",
            "original": f"/{clean_input_path}?v={timestamp}",
            "hud_image": f"/{clean_hud_path}?v={timestamp}",
            "dft_image": f"/{clean_dft_path}?v={timestamp}",
            "ela_image": f"/{clean_ela_path}?v={timestamp}",
            "heatmap_image": f"/{clean_heatmap_path}?v={timestamp}",
            "manifest": manifest_data,
            "pdf_url": f"/download_pdf/{normalized_filename}"
        }
    except Exception as e:
        ACTIVE_TASKS[task_id] = {"status": "FAILED", "error": str(e)}

@app.route('/process', methods=['POST'])
def process_image():
    if 'username' not in session: return redirect(url_for('login_page'))
    if 'file' not in request.files: return redirect(request.url)
    file = request.files['file']
    if file.filename == '': return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        task_id = f"task_{int(time.time() * 1000)}"
        ACTIVE_TASKS[task_id] = {"status": "PROCESSING", "started_at": time.time()}
        executor.submit(async_heavy_math_task, input_path, filename, task_id)
        return redirect(url_for('index', task_id=task_id))

@app.route('/process_webcam', methods=['POST'])
def process_webcam():
    if 'username' not in session: return redirect(url_for('login_page'))
    base64_data = request.form.get('image_base64')
    if not base64_data: return redirect('/')
    header, encoded = base64_data.split(",", 1)
    binary_data = base64.b64decode(encoded)
    filename = f"webcam_snap_{int(time.time())}.jpg"
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(input_path, "wb") as f: 
        f.write(binary_data)
        
    task_id = f"task_{int(time.time() * 1000)}"
    ACTIVE_TASKS[task_id] = {"status": "PROCESSING", "started_at": time.time()}
    executor.submit(async_heavy_math_task, input_path, filename, task_id)
    return redirect(url_for('index', task_id=task_id))

@app.route('/api/v1/task_status/<task_id>')
def get_task_status(task_id):
    task = ACTIVE_TASKS.get(task_id, {"status": "NOT_FOUND"})
    if task.get("status") == "PROCESSING":
        started_at = task.get("started_at")
        if started_at and (time.time() - started_at) > TASK_TIMEOUT_SECONDS:
            task = {"status": "FAILED", "error": "Analysis timed out before producing results."}
            ACTIVE_TASKS[task_id] = task
    return jsonify(task)

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    if 'username' not in session: return redirect(url_for('login_page'))
    pdf_target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename + "_official_report.pdf")
    if os.path.exists(pdf_target_path):
        return send_file(pdf_target_path, as_attachment=True, download_name=f"Forensic_Report_{filename}.pdf")
    return "Target PDF Missing.", 404

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/v1/export/csv', methods=['GET'])
def export_database_csv():
    if 'username' not in session: return redirect(url_for('login_page'))
    csv_target_path = os.path.join(app.config['UPLOAD_FOLDER'], 'forensic_audit_trail.csv')
    conn = sqlite3.connect('forensic_history.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, filename, timestamp, age_bracket, demographics, dft_score, ela_verdict, final_verdict, block_hash, gan_signature FROM cases ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    with open(csv_target_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Case ID', 'Target Name', 'Timestamp', 'Age Range', 'Demographics', 'DFT Metric', 'ELA Check', 'Verdict Matrix Output', 'Cryptographic Block Hash Seal', 'GAN Core Fingerprint'])
        writer.writerows(rows)
    return send_file(csv_target_path, as_attachment=True, download_name='Forensic_Master_Audit_Trail.csv')

@app.route('/api/v1/metrics', methods=['GET'])
def get_dashboard_metrics():
    if 'username' not in session: return jsonify({"error": "Unauthorized"}), 403
    conn = sqlite3.connect('forensic_history.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*), SUM(CASE WHEN final_verdict LIKE "%🚨%" THEN 1 ELSE 0 END) FROM cases')
    total, deepfakes = cursor.fetchone()
    total = total if total else 0
    deepfakes = deepfakes if deepfakes else 0
    authentic = total - deepfakes
    conn.close()
    return jsonify({"total": total, "deepfakes": deepfakes, "authentic": authentic})

@app.route('/api/v1/chat', methods=['POST'])
def assistant_chat():
    if 'username' not in session: return jsonify({"reply": "Please log in first."}), 401
    user_message = request.json.get('message', '').strip().lower()
    if not user_message: return jsonify({"reply": "I am listening!"})
    conn = sqlite3.connect('forensic_history.db')
    cursor = conn.cursor()
    try:
        if "status" in user_message or "summary" in user_message or "📊 system status" in user_message:
            is_secure, integrity_msg = verify_database_chain_integrity()
            cursor.execute('SELECT COUNT(*), SUM(CASE WHEN final_verdict LIKE "%🚨%" THEN 1 ELSE 0 END) FROM cases')
            total, deepfakes = cursor.fetchone()
            deepfakes = deepfakes if deepfakes else 0
            reply = f"📊 System Status Summary:\n• Total Images Analyzed: {total}\n• AI Deepfakes Flagged: {deepfakes}\n• Storage Integrity: {integrity_msg}"
        elif "recent" in user_message or "logs" in user_message or "📋 view recent logs" in user_message:
            cursor.execute('SELECT filename, final_verdict FROM cases ORDER BY id DESC LIMIT 3')
            rows = cursor.fetchall()
            if rows:
                reply = "📋 Here are the latest test items:\n" + "\n".join([f"• {r[0]}: {r[1]}" for r in rows])
            else:
                reply = "📋 The log history database is empty right now. Try uploading a new file!"
        elif "how" in user_message or "work" in user_message:
            reply = "❓ How This System Works:\n1. Upload a picture or use your camera.\n2. Ingestion pipelines execute verification math arrays inside separate background thread tasks so your browser tab never locks up.\n3. Every single log row is linked via a Cryptographic Hash Chain."
        else:
            reply = "👋 Hi there! I am USHA. Click one of the shortcut buttons above, or ask me for a 'system status' or 'recent logs' and I'll lookup the data for you!"
    except Exception as e: 
        reply = f"Oops, I had trouble looking that up: {str(e)}"
    finally: 
        conn.close()
    return jsonify({"reply": reply})

@app.route('/api/v1/clear_logs', methods=['POST'])
def clear_history_logs():
    if 'username' not in session: return jsonify({"success": False, "error": "Unauthorized"}), 401
    conn = sqlite3.connect('forensic_history.db')
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM cases')
        conn.commit()
    except Exception as e:
        print(f"Error clearing logs: {e}")
    finally:
        conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True, use_reloader=False)