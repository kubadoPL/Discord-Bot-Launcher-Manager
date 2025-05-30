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


# Roblox support
@app.route('/roblox/get_balance', methods=['GET'])
def get_roblox_balance():
    roblox_id = request.args.get('roblox_id')
    print(f"[REQUEST] GET /roblox/get_balance - roblox_id: {roblox_id}")

    if not roblox_id:
        print("[ERROR] Missing roblox_id in request.")
        return jsonify({'error': 'Missing roblox_id'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    print(f"[DB QUERY] Fetching balance for roblox_id: {roblox_id}")
    cursor.execute("SELECT balance FROM users WHERE roblox_id = %s", (roblox_id,))
    user = cursor.fetchone()
    
    conn.close()

    if user:
        print(f"[SUCCESS] Retrieved balance: {user['balance']} for roblox_id: {roblox_id}")
        return jsonify({'balance': user['balance']})
    else:
        print("[ERROR] Roblox user not found.")
        return jsonify({'error': 'Roblox user not found'}), 404

@app.route('/roblox/update_balance', methods=['POST'])
def update_roblox_balance():
    data = request.json
    roblox_id = data.get('roblox_id')
    amount = data.get('amount')

    print(f"[REQUEST] POST /roblox/update_balance - roblox_id: {roblox_id}, amount: {amount}")

    if not roblox_id or amount is None:
        print("[ERROR] Missing roblox_id or amount in request.")
        return jsonify({'error': 'Missing roblox_id or amount'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"[DB QUERY] Updating balance for roblox_id: {roblox_id} by {amount}")
    cursor.execute("UPDATE users SET balance = balance + %s WHERE roblox_id = %s", (amount, roblox_id))
    conn.commit()
    conn.close()

    print("[SUCCESS] Roblox balance updated successfully.")
    return jsonify({'message': 'Roblox balance updated successfully'})


def run_api():
    port = int(os.environ.get("PORT", 5000))  # Get the port from environment variable
    print(f"[INFO] Starting API server on port {port}...")
    app.run(host='0.0.0.0', port=port)

    
run_api()