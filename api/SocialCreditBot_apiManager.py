from flask import Flask, request, jsonify
import mysql.connector
import config  # Import your config settings
import os
app = Flask(__name__)

# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
os.chdir(parent_dir)  # Change working directory

print("Working directory set to:", os.getcwd())


# Database connection function
def get_db_connection():
    print("[INFO] Connecting to the database...")
    conn = mysql.connector.connect(
        host=config.HOST,
        user=config.USER,
        password=config.PASSWORD,
        database=config.DATABASE,
        port=config.PORT,
        autocommit=True
    )
    print("[INFO] Database connection established.")
    return conn

@app.route('/get_balance', methods=['GET'])
def get_balance():
    user_id = request.args.get('user_id')
    print(f"[REQUEST] GET /get_balance - user_id: {user_id}")

    if not user_id:
        print("[ERROR] Missing user_id in request.")
        return jsonify({'error': 'Missing user_id'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    print(f"[DB QUERY] Fetching balance for user_id: {user_id}")
    cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    conn.close()

    if user:
        print(f"[SUCCESS] Retrieved balance: {user['balance']} for user_id: {user_id}")
        return jsonify({'balance': user['balance']})
    else:
        print("[ERROR] User not found.")
        return jsonify({'error': 'User not found'}), 404

@app.route('/update_balance', methods=['POST'])
def update_balance():
    data = request.json
    user_id = data.get('user_id')
    amount = data.get('amount')

    print(f"[REQUEST] POST /update_balance - user_id: {user_id}, amount: {amount}")

    if not user_id or amount is None:
        print("[ERROR] Missing user_id or amount in request.")
        return jsonify({'error': 'Missing user_id or amount'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"[DB QUERY] Updating balance for user_id: {user_id} by {amount}")
    cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
    conn.commit()
    conn.close()

    print("[SUCCESS] Balance updated successfully.")
    return jsonify({'message': 'Balance updated successfully'})

def run_api():
    print("[INFO] Starting API server on port 5000...")
    port = int(os.environ.get("PORT", 5000))  # Get the port from environment variable
    app.run(host='0.0.0.0', port=port)

    
run_api()
print("Api run!")