from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import mysql.connector
from datetime import datetime, timedelta


app = Flask(__name__)
CORS(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'raj@123'
app.config['MYSQL_DB'] = 'fitnesstracker'

connection = mysql.connector.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB']
)


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    emailId = data.get('loginEmail')
    password = data.get('loginPassword')

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email_id = %s AND password = %s", (emailId, password))
    user = cursor.fetchone()
    cursor.close()

    if user:
        return jsonify({'message': 'valid'})
    else:
        return jsonify({'message': 'invalid'})
    

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    name = data.get('signUpName')
    email = data.get('signUpEmail')
    designation = data.get('signUpDesignation')
    phone = data.get('signUpPhone')
    password = data.get('signUpPassword')

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email_id = %s AND password = %s", (email, password))
        user = cursor.fetchone()

        if user:
            cursor.close()
            return jsonify({'message': 'User Account already exists, Click login.'})
        else:
            cursor.execute("INSERT into users (name,email_id,phone_no,role,password) VALUES (%s,%s,%s,%s,%s)", (name,email,phone,designation,password))
            connection.commit()
            cursor.close()

            return jsonify({'message': 'valid'})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'invalid'})


@app.route('/updateStepCount', methods=['POST'])
def update():
    data = request.get_json()
    userEmail = data['userEmail']
    step_count = data['stepCount']
    update_date = data['date']
 
    cursor = connection.cursor()
 
    # Use placeholders (%s) for dynamic values to prevent SQL injection
    cursor.execute("INSERT INTO stepcount (user_id, stepcount, date) SELECT u.user_id, %s, %s FROM users u WHERE u.email_id = %s", (step_count, update_date, userEmail))
    connection.commit()
    cursor.close()
 
    return jsonify({"message": "Step count updated successfully!"})


@app.route('/getUserProfile', methods=['POST'])
def getUserProfile():
    data = request.get_json()
    userEmail = data['userEmail']
    if userEmail:
        cursor = connection.cursor()
        query = "SELECT name, phone_no, role, address, profile_photo FROM users WHERE email_id = %s"
        cursor.execute(query, (userEmail,))
        result = cursor.fetchone()
        if result:
            return jsonify({
                'name': result[0],
                'phone': result[1],
                'role': result[2],
                'address': result[3],
                'profilePhoto': result[4],
            })
        else:
            return jsonify({'error': 'User not found'}), 404
    else:
        return jsonify({'error': 'User email is required'}), 400

@app.route('/updateUserProfile', methods=['POST'])
def updateUserProfile():
    data = request.get_json()
    userEmail = data['email']
    name = data['name']
    phone = data['phone']
    role = data['role']
    address = data['address']
    profilePhoto = data['profilePicture']

    if userEmail:
        cursor = connection.cursor()
        query = """
            UPDATE users
            SET name = %s, phone_no = %s, role = %s, address = %s, profile_photo = %s
            WHERE email_id = %s
        """
        cursor.execute(query, (name, phone, role, address, profilePhoto, userEmail))
        connection.commit()
        return jsonify({'success': 'User profile updated successfully'})
    else:
        return jsonify({'error': 'User email is required'}), 400
    

@app.route('/leaderboardDaily', methods=['GET'])
def leaderboardDaily():
    cursor = connection.cursor()
    cursor.execute("SELECT u.name, sc.stepcount FROM users u JOIN stepcount sc ON u.user_id = sc.user_id  WHERE DATE(sc.date) = CURDATE() ORDER BY sc.stepcount DESC")
    users = cursor.fetchall()
    cursor.close()

    steps = [{"name": user[0], "stepcount": user[1]} for user in users]
    return jsonify(steps)

 
@app.route('/leaderboardWeekly', methods=['GET'])
def leaderboardWeekly():
    cursor = connection.cursor()
    cursor.execute("SELECT u.name, ROUND(AVG(sc.stepcount),0) AS avg_steps FROM users u JOIN stepcount sc ON u.user_id = sc.user_id Where sc.date >= DATE_SUB(CURRENT_DATE(), INTERVAL WEEKDAY(CURRENT_DATE()) DAY) + INTERVAL 1 DAY AND sc.date <= DATE_SUB(CURRENT_DATE(), INTERVAL WEEKDAY(CURRENT_DATE()) DAY) + INTERVAL 7 DAY GROUP BY u.user_id, u.name ORDER BY avg_steps DESC")
    rows = cursor.fetchall()
    cursor.close()

    steps = [{"name": row[0], "avg_steps": row[1]} for row in rows]
    return jsonify(steps)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    cursor = connection.cursor()
    
    # Execute query to get total steps for each user for the last 7 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=6)
    cursor.execute("""
        SELECT u.user_id, u.email_id, SUM(sc.stepcount) AS total_steps 
        FROM users u 
        JOIN stepcount sc ON u.user_id = sc.user_id 
        WHERE sc.date BETWEEN %s AND %s 
        GROUP BY u.user_id
    """, (start_date, end_date))
    total_steps_rows = cursor.fetchall()
    
    # Execute query to get average steps for each user for the last 7 days
    cursor.execute("""
        SELECT u.user_id, AVG(sc.stepcount) AS average_steps 
        FROM users u 
        JOIN stepcount sc ON u.user_id = sc.user_id 
        WHERE sc.date BETWEEN %s AND %s 
        GROUP BY u.user_id
    """, (start_date, end_date))
    average_steps_rows = cursor.fetchall()
    
    # Execute query to get step count for the last 7 days for each user
    last_7_days_data = {}
    cursor.execute("""
        SELECT u.user_id, sc.date, SUM(sc.stepcount) AS steps 
        FROM users u 
        JOIN stepcount sc ON u.user_id = sc.user_id 
        WHERE sc.date BETWEEN %s AND %s 
        GROUP BY u.user_id, sc.date
    """, (start_date, end_date))
    last_7_days_rows = cursor.fetchall()
    for row in last_7_days_rows:
        user_id = row[0]
        date = row[1].strftime("%Y-%m-%d")  # Formatting date to YYYY-MM-DD
        steps = row[2]
        if user_id not in last_7_days_data:
            last_7_days_data[user_id] = []
        last_7_days_data[user_id].append({"date": date, "steps": steps})
    
    cursor.close()

    # Restructure data with total_steps, average_steps, email, and last_7_days for each user
    user_data = {}
    for total_row, average_row in zip(total_steps_rows, average_steps_rows):
        user_id = total_row[0]
        email = total_row[1]
        total_steps = total_row[2]
        average_steps = average_row[1]
        last_7_days = last_7_days_data.get(user_id, [])
        user_data[user_id] = {"user_id": user_id, "email": email, "total_steps": total_steps, "average_steps": average_steps, "last_7_days": last_7_days}
        
    # Convert user_data to list and jsonify
    return jsonify([user_data[user_id] for user_id in user_data])


@app.route('/buttonAverage', methods=['POST'])
def buttonAverage():
    data = request.get_json()
    userEmail = data['userEmail']

    cursor = connection.cursor()
    cursor.execute("SELECT AVG(s.stepcount) as average_stepcount FROM users u JOIN stepcount s on u.user_id = s.user_id where u.email_id = %s group by u.user_id", (userEmail,))
    averageStepCount = cursor.fetchall()

    return jsonify(averageStepCount)


@app.route('/buttonTotal', methods=['POST'])
def buttonTotal():
    data = request.get_json()
    userEmail = data['userEmail']

    cursor = connection.cursor()
    cursor.execute("SELECT SUM(s.stepcount) AS total_stepcount FROM users u JOIN stepcount s on u.user_id = s.user_id where u.email_id = %s group by u.user_id", (userEmail,))
    totalStepCount = cursor.fetchall()

    return jsonify(totalStepCount)

if __name__ == '__main__':
    app.run(debug=True)

