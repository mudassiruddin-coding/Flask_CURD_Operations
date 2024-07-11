from flask import jsonify, request, render_template
from flask_pymongo import ObjectId
from app import app, mongo, logger  # Import 'app', 'mongo', 'logger' from main app

# MongoDB collections
tasks = mongo.db.tasks
users = mongo.db.users

# Your route definitions go here
# Example:
@app.route('/')
def index():
    return render_template('index.html')

# Example route using tasks collection
@app.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        all_tasks = list(tasks.find())
        for task in all_tasks:
            task['_id'] = str(task['_id'])  # Convert ObjectId to string

        return jsonify({'tasks': all_tasks}), 200

    except Exception as e:
        logger.error(f"Failed to fetch tasks: {e}")
        return jsonify({'error': 'Failed to fetch tasks', 'details': str(e)}), 500

# Other routes...
