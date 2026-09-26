from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
import mysql.connector
from datetime import datetime, date, timedelta
import base64
import traceback
import os
import subprocess
import hashlib
import threading

def drain_output(pipe, tag=""):
    for line in pipe:
        print(f"[{tag}] {line.strip()}")

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session handling

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="Exam"
    )
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Default route redirects to home
@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('userType')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            if role == 'student':
                cursor.execute("SELECT * FROM Student WHERE email = %s", (email,))
                user = cursor.fetchone()
                if user and user['password'] == hash_password(password):
                    session['user'] = {
                        'id': user['studentid'],
                        'name': user['name'],
                        'email': user['email'],
                        'gender': user['gender'],
                        'year': user['year'],
                        'contact': user['contact'],
                        'role': 'student'
                    }
                    return redirect(url_for('home'))
                else:
                    flash("Incorrect email or password. Please try again.", "danger")
                    return redirect(url_for('login'))  # Ensure redirection to show error

            elif role == 'faculty':
                cursor.execute("SELECT * FROM Faculty WHERE email = %s", (email,))
                user = cursor.fetchone()
                if user and user['password'] == hash_password(password):
                    session['user'] = {
                        'id': user['facultyid'],
                        'name': user['name'],
                        'email': user['email'],
                        'contact': user['contact'],
                        'role': 'faculty'
                    }
                    return redirect(url_for('home'))
                else:
                    flash("Incorrect email or password. Please try again.", "danger")
                    return redirect(url_for('login'))

            else:
                flash("Please select a user type.", "warning")
                return redirect(url_for('login'))
        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')  # Ensure GET request loads the page correctly

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    dark_mode = session.get('dark_mode', False)

    image_data = get_profile_image(user)
    return render_template('home.html', user=user, image=image_data, dark_mode=dark_mode)


@app.route('/exam')
def exam():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = session['user']
    dark_mode = session.get('dark_mode', False)
    image_data = get_profile_image(user)

    # Fetch exams
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT assesmentid, exam_date, exam_time, subjectid FROM Exams ORDER BY exam_date, exam_time")
        exams = cursor.fetchall()  # Fetch all exams
        
        return render_template('exam.html', user=user, image=image_data, dark_mode=dark_mode, exams=exams)

    except Exception as e:
        print("Error fetching exams:", str(e))
        return render_template('exam.html', user=user, image=image_data, dark_mode=dark_mode, exams=[])

    finally:
        cursor.close()
        conn.close()

@app.route('/get_exams')
def get_exams():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        
        if(session['user']['role']=='faculty'):
            cursor.execute("select assesmentid,exam_date,exam_time,subjectid from exams;")
        else:
        # Run the SQL query
            cursor.execute("SELECT DISTINCT E.assesmentid, E.exam_date, E.exam_time, E.subjectid FROM Exams E WHERE NOT EXISTS ( SELECT 1 FROM Response R WHERE R.assesmentid = E.assesmentid AND R.subjectid = E.subjectid AND R.studentid = %s) AND E.exam_date = CURRENT_DATE AND E.exam_time >= CURRENT_TIME - INTERVAL 10 MINUTE ORDER BY E.exam_time;",(session["user"]["id"],))
        exams = cursor.fetchall()

        # Debugging: Print raw database output
        print("Raw Exam Data from DB:", exams)

        # Ensure data exists
        if not exams:
            print("No exams found in database.")
            return jsonify({"exams": []})

        # Convert query results into a list of dictionaries
        formatted_exams = []
        for exam in exams:
            formatted_exams.append({
                "assesmentid": exam["assesmentid"],  
                "exam_date": str(exam["exam_date"]),  # Convert date to string
                "exam_time": str(exam["exam_time"]),  # Convert timedelta to string
                "subjectid": exam["subjectid"]
            })
            
        # Debugging: Print formatted exams data
        print("Formatted Exams Data:", formatted_exams)

        return jsonify({"exams": formatted_exams})
    

    except Exception as e:
        print("Error:", str(e))
        traceback.print_exc()  # This prints the full error traceback
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        
@app.route("/delete_exam", methods=["POST"])
def delete_exam():
    if 'user' not in session or session['user']['role'] != 'faculty':
        return jsonify({"error": "Unauthorized access"}), 403
    try:
        data = request.json
        print("Received Delete Request:", data)  # Debugging
        subjectid = data.get("subjectid")
        assesmentid = data.get("assesmentid")

        if not subjectid or not assesmentid:
            return jsonify({"error": "Invalid request parameters"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM exams WHERE subjectid = %s AND assesmentid = %s", (subjectid, assesmentid))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Exam not found"}), 404  # Handle non-existent exams

        cursor.close()
        conn.close()

        return jsonify({"message": "Exam deleted successfully!"})

    except Exception as e:
        print("Error deleting exam:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500

@app.route('/create_exam', methods=['POST'])
def create_exam():
    if 'user' not in session or session['user']['role'] != 'faculty':
        return jsonify({"error": "Unauthorized access"}), 403

    # Extract form data
    subjectid = request.form.get('subjectid')
    assesmentid = request.form.get('assessmentid')
    exam_date = request.form.get('exam_date')
    exam_time = request.form.get('exam_time')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Insert into Exams table
        cursor.execute("""
            INSERT INTO Exams (subjectid, assesmentid, exam_date, exam_time)
            VALUES (%s, %s, %s, %s)
        """, (subjectid, assesmentid, exam_date, exam_time))

        # Insert questions into Question_Paper table
        for i in range(1, 11):  # Assuming 10 questions
            question = request.form.get(f'question{i}')
            option1 = request.form.get(f'option1_{i}')
            option2 = request.form.get(f'option2_{i}')
            option3 = request.form.get(f'option3_{i}')
            option4 = request.form.get(f'option4_{i}')

            if question:  # Only insert if question exists
                cursor.execute("""
                    INSERT INTO Question_Paper (subjectid, assesmentid, question_number, question, option1, option2, option3, option4)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (subjectid, assesmentid, i, question, option1, option2, option3, option4))

        # Commit transaction
        conn.commit()
        return jsonify({"message": "Exam Created Successfully!"}), 200

    except Exception as e:
        conn.rollback()  # Rollback in case of error
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_start_time')
def get_start_time():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    subjectid = session.get('subjectid')
    assessmentid = session.get('assessmentid')
    
    cursor.execute("SELECT exam_date, exam_time FROM exams WHERE subjectid=%s AND assesmentid=%s", (subjectid, assessmentid))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        # Convert timedelta to time
        exam_time_delta = result['exam_time']
        exam_time = (datetime.min + exam_time_delta).time()

        # Combine with date
        exam_datetime = datetime.combine(result['exam_date'], exam_time)
        
        # Return ISO format
        return jsonify({'start_time': exam_datetime.isoformat()})
    else:
        return jsonify({'error': 'Start time not found'}), 404

proctoring_process = None  # Global variable

@app.route("/start_proctoring")
def start_proctoring():
    global proctoring_process
    studentid = session['user']['id']
    subjectid = session.get('subjectid')
    assessmentid = session.get('assessmentid')

    proctoring_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'online_proctoring.py'))

    try:
        # Start subprocess and store globally
        proctoring_process = subprocess.Popen(
            ['python3', '-u', proctoring_script_path, studentid, str(subjectid), str(assessmentid)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            text=True
        )

        # Wait until successful message appears:
        while True:
            line = proctoring_process.stdout.readline()
            print("Proctoring:", line.strip())
            if "Running Successfully" in line:
                threading.Thread(target=drain_output, args=(proctoring_process.stdout, "STDOUT"), daemon=True).start()
                threading.Thread(target=drain_output, args=(proctoring_process.stderr, "STDERR"), daemon=True).start()
                return jsonify({"status": "started"})
            if line == '' and proctoring_process.poll() is not None:
                break  # Process ended unexpectedly

        return jsonify({"status": "failed"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/stop_proctoring", methods=["POST"])
def stop_proctoring():
    global proctoring_process
    if proctoring_process and proctoring_process.poll() is None:
        proctoring_process.terminate()  # Send SIGTERM
        proctoring_process.wait()  # Wait till it exits
        proctoring_process = None
        return jsonify({"status": "terminated"})
    else:
        return jsonify({"status": "not_running"})

@app.route('/instructions/<subjectid>/<assessmentid>')
def instructions(subjectid, assessmentid):
    if 'user' not in session:
        return redirect(url_for('login'))
    user = session['user']
    image_data = get_profile_image(user)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch all questions
        cursor.execute("SELECT question_number, question, option1, option2, option3, option4 FROM question_paper WHERE subjectid=%s AND assesmentid=%s", (subjectid, assessmentid))
        questions = cursor.fetchall()

        # Fetch existing responses
        cursor.execute("SELECT question_number, response FROM response WHERE studentid=%s AND subjectid=%s AND assesmentid=%s", (user['id'], subjectid, assessmentid))
        responses = cursor.fetchall()
        response_dict = {r['question_number']: r['response'] for r in responses}

        # Format questions
        formatted_questions = []
        for question in questions:
            formatted_questions.append({
                "question_number": question["question_number"],
                "question": question["question"],
                "option1": question["option1"],
                "option2": question["option2"],
                "option3": question["option3"],
                "option4": question["option4"],
                "response": response_dict.get(question["question_number"])  # Set saved response
            })

        # Store currentIndex in session
        if 'currentIndex' not in session:
            session['currentIndex'] = 0
        session['subjectid'] = subjectid
        session['assessmentid'] = assessmentid

    finally:
        cursor.close()
        conn.close()

    return render_template('instructions.html', 
        subjectid=subjectid, 
        assessmentid=assessmentid, 
        user=user, 
        image=image_data, 
        questions=formatted_questions,
        currentIndex=session['currentIndex']  # Pass index to frontend
    )
@app.route('/submit_responses', methods=['POST'])
def submit_responses():
    data = request.json
    responses = data['responses']  # { question_number: option }

    studentid = session['user']['id']
    subjectid = session.get('subjectid')
    assessmentid = session.get('assessmentid')

    conn = get_db_connection()
    cursor = conn.cursor()

    for qnum, ans in responses.items():
        cursor.execute(
            "INSERT INTO response (studentid, subjectid, assesmentid, question_number, response) VALUES (%s, %s, %s, %s, %s)",
            (studentid, subjectid, assessmentid, qnum, ans)
        )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Responses submitted!"})
@app.route("/eligible")
def eligible():
    studentid = session['user']['id']
    subjectid = session.get('subjectid')
    assessmentid = session.get('assessmentid')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(DISTINCT CONCAT(studentid, subjectid, assesmentid)) FROM response WHERE subjectid = %s AND assesmentid = %s AND studentid = %s;",(subjectid,assessmentid,studentid))
        count=cursor.fetchone()[0]
        print("Response Count = ", count)
        if(count!=0):
            return jsonify({"eligible":"False"})
        else:
            return jsonify({"eligible":"True"})
    finally:
        conn.close()
        cursor.close()
        
@app.route("/result")
def result():
    if 'user' not in session:
        return redirect (url_for("login"))
    user= session['user']
    dark_mode = session.get('dark_mode', False)
    image_data = get_profile_image(user)
    
    return render_template('result.html', user=user, image=image_data, dark_mode=dark_mode)
    
@app.route("/upload_answers", methods=["POST"])
def upload_result():
    if 'user' not in session or session['user']['role'] != 'faculty':
        return jsonify({"error": "Unauthorized access"}), 403
    subjectid = request.form.get('subjectid')
    assesmentid = request.form.get('assesmentid')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        for i in range(1, 11):  # Assuming 10 questions
            answer = request.form.get(f'answer{i}')

            if answer or answer==0:  # Only insert if question exists
                cursor.execute("""
                    INSERT INTO answer (subjectid, assesmentid, question_number, answer)
                    VALUES (%s, %s, %s, %s)
                """, (subjectid, assesmentid, i, answer))

        # Commit transaction
        conn.commit()
        return jsonify({"message": "Answers Uploaded Successfully!"}), 200

    except Exception as e:
        conn.rollback()  # Rollback in case of error
        if("Duplicate entry" in str(e)):
            return jsonify({"error": "Answers already uploaded!"}), 400
        elif("foreign key constraint fails" in str(e)):
            return jsonify({"error": "Invalid subjectid or assessmentid!"}), 400
        else:
            return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/calculate_result", methods=["POST"])
def calculate_result():
    if 'user' not in session or session['user']['role'] != 'faculty':
        return jsonify({"error": "Unauthorized access"}), 403
    subjectid = request.form.get('subjectid')
    assesmentid = request.form.get('assesmentid')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Calculate results
        cursor.execute("""
                       INSERT INTO result (studentid, subjectid, assesmentid, result)
SELECT 
    r.studentid,
    r.subjectid,
    r.assesmentid,
    SUM(r.response = a.answer) AS correct_count
FROM response r
LEFT JOIN answer a
  ON r.subjectid = a.subjectid
  AND r.assesmentid = a.assesmentid
  AND r.question_number = a.question_number
WHERE r.subjectid = %s AND r.assesmentid = %s
GROUP BY r.studentid, r.subjectid, r.assesmentid;
                       """,(subjectid, assesmentid))

        conn.commit()
        return jsonify({"message": "Results Calculated Successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_results', methods=["POST"])
def get_result():
    try:
        # Support both form data and JSON body
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        subjectid = data.get('subjectid')
        assesmentid = data.get('assesmentid')

        if not subjectid or not assesmentid:
            return jsonify({"error": "Missing subjectid or assesmentid"}), 400

        # Convert to int with error handling
        try:
            subjectid = int(subjectid)
            assesmentid = int(assesmentid)
        except ValueError:
            return jsonify({"error": "subjectid and assesmentid must be integers"}), 400

        # Check session exists
        if 'user' not in session or 'role' not in session['user']:
            return jsonify({"error": "Unauthorized"}), 403

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        uploaded_answers = False
        
        cursor.execute("select count(*) as count from answer where subjectid=%s and assesmentid=%s;",(subjectid,assesmentid))
        count=cursor.fetchone()["count"]
        if(count==10):
            uploaded_answers = True
        if uploaded_answers:
            if session['user']['role'] == 'faculty':
                cursor.execute(
                    "SELECT studentid, subjectid, assesmentid, result FROM result WHERE subjectid=%s AND assesmentid=%s;",
                    (subjectid, assesmentid)
                )
                results = cursor.fetchall()

                formatted_results = [{
                    "studentid": r["studentid"],
                    "subjectid": r["subjectid"],
                    "assesmentid": r["assesmentid"],
                    "result": r["result"]
                } for r in results]

                return jsonify({"uploaded_answers": uploaded_answers, "results": formatted_results})

            else:
                studentid = session['user']['id']
                cursor.execute(
                    "SELECT subjectid, assesmentid, result FROM result WHERE studentid=%s AND subjectid=%s AND assesmentid=%s;",
                    (studentid, subjectid, assesmentid)
                )
                result = cursor.fetchone()
                if not result:
                    return jsonify({"uploaded_answers": uploaded_answers, "results": []})
                formatted_result = [{
                    "subjectid": result["subjectid"],
                    "assesmentid": result["assesmentid"],
                    "result": result["result"]
                }]
                return jsonify({"uploaded_answers": uploaded_answers, "results": formatted_result})
        else:
            return jsonify({"uploaded_answers": uploaded_answers, "results":[]})

    except Exception as e:
        print("Error:", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            
@app.route('/review_violations', methods=['GET', 'POST'])
def review_violations():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    if user['role'] != 'faculty':
        return redirect(url_for('home'))

    dark_mode = session.get('dark_mode', False)
    image_data = get_profile_image(user)

    # Filter parameters from form
    studentid = request.args.get('studentid', '').strip()
    subjectid = request.args.get('subjectid', '').strip()
    assesmentid = request.args.get('assesmentid', '').strip()
    violation_type = request.args.get('violation', '').strip()

    query = "SELECT * FROM violations WHERE 1=1"
    params = []

    if studentid:
        query += " AND studentid = %s"
        params.append(studentid)
    if subjectid:
        query += " AND subjectid = %s"
        params.append(subjectid)
    if assesmentid:
        query += " AND assesmentid = %s"
        params.append(assesmentid)
    if violation_type:
        query += " AND violation = %s"
        params.append(violation_type)

    query += " ORDER BY timestamp DESC"

    conn= get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    violations = cursor.fetchall()

    return render_template('review_violations.html',
                           user=user,
                           image=image_data,
                           violations=violations,
                           studentid=studentid,
                           subjectid=subjectid,
                           assesmentid=assesmentid,
                           violation=violation_type,
                           dark_mode=dark_mode)


@app.route('/violation_video')
def violation_video():
    studentid = request.args.get('studentid')
    subjectid = request.args.get('subjectid')
    assesmentid = request.args.get('assesmentid')
    timestamp = request.args.get('timestamp')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT video FROM violations 
            WHERE studentid = %s AND subjectid = %s AND assesmentid = %s AND timestamp = %s
        """, (studentid, subjectid, assesmentid, timestamp))

        row = cursor.fetchone()
        if row and row['video']:
            return app.response_class(row['video'], mimetype='video/mp4')
        return "Video not found", 404
    finally:
        cursor.close()
        conn.close()


@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    dark_mode = session.get('dark_mode', False)
    image_data = get_profile_image(user)
    
    return render_template('profile.html', user=user, image=image_data, dark_mode=dark_mode)


def get_profile_image(user):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    image_data = None
    try:
        if user['role'] == 'student':  
            cursor.execute("SELECT image FROM Student WHERE studentid = %s", (user['id'],))
            result = cursor.fetchone()
            if result and result['image']:
                image_data = "data:image/jpeg;base64," + base64.b64encode(result['image']).decode('utf-8')
    finally:
        cursor.close()
        conn.close()
    return image_data


@app.route('/toggle-dark-mode', methods=['POST'])
def toggle_dark_mode():
    session['dark_mode'] = not session.get('dark_mode', False)  # Toggle dark mode
    return '', 204  # No content response


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)