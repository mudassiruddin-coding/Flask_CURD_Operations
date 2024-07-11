from flask import Flask, jsonify, request, render_template
from flask_pymongo import PyMongo
import logging
from bson import ObjectId
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps  # Import wraps from functools


app = Flask(__name__)
app.config['SECRET_KEY'] = '1277bhj21vhuy78tcuimudassir'  # Change this to a strong secret key; consider using environment variables

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure MongoDB connection
app.config['MONGO_URI'] = 'mongodb://localhost:27017/taskmanagerdb'
mongo = PyMongo(app)

# MongoDB collections
tasks = mongo.db.tasks
users = mongo.db.users

# Utility function to generate JWT
def generate_token(user_id):
    token = jwt.encode({
        'user_id': str(user_id),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    return token

# User Registration
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Missing username or password in request'}), 400

        existing_user = users.find_one({'username': data['username']})
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 409

        hashed_password = generate_password_hash(data['password'], method='sha256')
        user_id = users.insert_one({'username': data['username'], 'password': hashed_password}).inserted_id

        return jsonify({'message': 'User registered successfully', 'user_id': str(user_id)}), 201

    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        return jsonify({'error': 'Failed to register user', 'details': str(e)}), 500

# User Login
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Missing username or password in request'}), 400

        user = users.find_one({'username': data['username']})
        if not user or not check_password_hash(user['password'], data['password']):
            return jsonify({'message': 'Invalid credentials'}), 401

        token = generate_token(user['_id'])
        return jsonify({'token': token}), 200

    except Exception as e:
        logger.error(f"Failed to login user: {e}")
        return jsonify({'error': 'Failed to login user', 'details': str(e)}), 500

# Decorator to protect routes
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = users.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                return jsonify({'message': 'User not found!'}), 403

            # Make the current_user available to the endpoint function
            return f(current_user, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 403

        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 403

        except Exception as e:
            return jsonify({'message': 'Error decoding token!', 'error': str(e)}), 403

    return decorated_function

# Endpoint to get all tasks (requires authentication)
@app.route('/tasks', methods=['GET'])
@token_required
def get_tasks(current_user):
    try:
        all_tasks = list(tasks.find({'user_id': str(current_user['_id'])}))  # Convert ObjectId to string
        for task in all_tasks:
            task['_id'] = str(task['_id'])  # Convert ObjectId to string
            task['user_id'] = str(task['user_id'])  # Convert ObjectId to string

        return jsonify({'tasks': all_tasks})

    except Exception as e:
        logger.error(f"Failed to fetch tasks: {e}")
        return jsonify({'error': 'Failed to fetch tasks', 'details': str(e)}), 500

# Endpoint to get a specific task by ID (requires authentication)
@app.route('/tasks/<task_id>', methods=['GET'])
@token_required
def get_task(current_user, task_id):
    try:
        task = tasks.find_one({'_id': ObjectId(task_id), 'user_id': str(current_user['_id'])})  # Convert ObjectId to string
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        task['_id'] = str(task['_id'])  # Convert ObjectId to string
        task['user_id'] = str(task['user_id'])  # Convert ObjectId to string
        return jsonify({'task': task})

    except Exception as e:
        logger.error(f"Failed to fetch task: {e}")
        return jsonify({'error': 'Failed to fetch task', 'details': str(e)}), 500


# Endpoint to create a new task (requires authentication)
@app.route('/tasks', methods=['POST'])
@token_required
def create_task(current_user):
    try:
        data = request.json
        if not data or 'title' not in data:
            return jsonify({'error': 'Missing title in request'}), 400

        new_task = {
            'title': data['title'],
            'description': data.get('description', ''),
            'user_id': str(current_user['_id'])  # Convert ObjectId to string
        }

        result = tasks.insert_one(new_task)
        new_task['_id'] = str(result.inserted_id)

        logger.info(f"New task added: {new_task}")
        return jsonify({'task': new_task}), 201

    except Exception as e:
        logger.error(f"Failed to add task: {e}")
        return jsonify({'error': 'Failed to add task', 'details': str(e)}), 500



# Endpoint to update an existing task by ID (requires authentication)
@app.route('/tasks/<string:task_id>', methods=['PUT'])
@token_required
def update_task(current_user, task_id):
    try:
        data = request.json
        updated_task = {
            'title': data.get('title'),
            'description': data.get('description')
        }

        tasks.update_one({'_id': ObjectId(task_id), 'user_id': str(current_user['_id'])}, {'$set': updated_task})  # Convert ObjectId to string
        updated_task['_id'] = task_id
        updated_task['user_id'] = str(current_user['_id'])  # Convert ObjectId to string

        logger.info(f"Task updated: {updated_task}")
        return jsonify({'task': updated_task}), 200

    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        return jsonify({'error': 'Failed to update task', 'details': str(e)}), 500


# Endpoint to delete a task by ID (requires authentication)
@app.route('/tasks/<string:task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user, task_id):
    try:
        result = tasks.delete_one({'_id': ObjectId(task_id), 'user_id': str(current_user['_id'])})  # Convert ObjectId to string
        if result.deleted_count == 0:
            return jsonify({'error': 'Task not found'}), 404

        logger.info(f"Task deleted: {task_id}")
        return jsonify({'result': 'Task deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        return jsonify({'error': 'Failed to delete task', 'details': str(e)}), 500


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def show_login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
