#!/usr/bin/env python3
"""
NeuroCanvas - AI-Powered Emotional Art Generation Platform
Main Flask Application

This application creates personalized, neuromorphic art based on real-time emotion analysis
from text, images, and audio inputs, with contextual memory and narrative generation.
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
import redis
import json
import traceback
import uuid
from PIL import Image
import io
import base64

# Import our custom modules
from src.config import Config
from src.database import DatabaseManager, User, Artwork, Memory, UserSession, ArtworkInteraction
from src.emotion_analyzer import EmotionAnalyzer
from src.art_generator import NeuromorphicArtGenerator
from src.narrative_generator import NarrativeGenerator
from src.memory_system import EmotionalMemoryBank, ArtisticMemoryBank
from src.websocket_handler import WebSocketHandler

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
cors = CORS(app, origins=Config.CORS_ORIGINS)
socketio = SocketIO(app, cors_allowed_origins=Config.CORS_ORIGINS, async_mode='threading')
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

# Initialize Redis for caching and session management
try:
    redis_client = redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_DB,
        decode_responses=True
    )
    redis_client.ping()
except Exception as e:
    logging.warning(f"Redis connection failed: {e}. Using in-memory cache.")
    redis_client = None

# Initialize core components
db_manager = DatabaseManager()
emotion_analyzer = EmotionAnalyzer()
art_generator = NeuromorphicArtGenerator()
narrative_generator = NarrativeGenerator()
emotional_memory = EmotionalMemoryBank(db_manager)
artistic_memory = ArtisticMemoryBank(db_manager)
websocket_handler = WebSocketHandler(socketio)

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('neurocanvas.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# JWT token utilities
def generate_token(user_id):
    """Generate JWT token for user authentication"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """Decorator for routes that require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        # Get user from database
        user = db_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated

# File upload utilities
def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, upload_type):
    """Save uploaded file and return file path"""
    if not file or file.filename == '':
        return None
    
    allowed_extensions = {
        'image': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
        'audio': {'wav', 'mp3', 'ogg', 'm4a'},
        'video': {'mp4', 'webm', 'avi', 'mov'}
    }
    
    if not allowed_file(file.filename, allowed_extensions.get(upload_type, set())):
        return None
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    
    upload_dir = os.path.join(Config.UPLOAD_FOLDER, upload_type)
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    return file_path

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'retry_after': str(e.retry_after)}), 429

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': db_manager.health_check(),
            'redis': redis_client is not None,
            'emotion_analyzer': True,
            'art_generator': True,
            'narrative_generator': True
        }
    })

# Authentication endpoints
@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user already exists
        existing_user = db_manager.get_user_by_email(data['email'])
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 409
        
        existing_user = db_manager.get_user_by_username(data['username'])
        if existing_user:
            return jsonify({'error': 'Username already taken'}), 409
        
        # Create new user
        password_hash = generate_password_hash(data['password'])
        user_data = {
            'username': data['username'],
            'email': data['email'],
            'password_hash': password_hash,
            'full_name': data.get('full_name', ''),
            'preferences': data.get('preferences', {})
        }
        
        user = db_manager.create_user(user_data)
        if not user:
            return jsonify({'error': 'Failed to create user'}), 500
        
        # Generate token
        token = generate_token(user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'created_at': user.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Get user by email
        user = db_manager.get_user_by_email(email)
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db_manager.session.commit()
        
        # Generate token
        token = generate_token(user.id)
        
        # Create user session
        session_data = {
            'user_id': user.id,
            'session_token': str(uuid.uuid4()),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'login_time': datetime.utcnow()
        }
        db_manager.create_user_session(session_data)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'preferences': user.preferences,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout():
    """User logout endpoint"""
    try:
        # Invalidate session (in a real app, you'd maintain a blacklist)
        return jsonify({'message': 'Logout successful'})
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

# Emotion analysis endpoints
@app.route('/api/emotion/analyze', methods=['POST'])
@token_required
@limiter.limit("30 per minute")
def analyze_emotion():
    """Analyze emotion from text, image, or audio"""
    try:
        user = request.current_user
        
        # Handle different input types
        emotion_data = None
        
        if 'text' in request.json:
            # Text emotion analysis
            text = request.json['text']
            emotion_data = emotion_analyzer.analyze_text_emotion(text)
            
        elif 'image' in request.files:
            # Image emotion analysis
            image_file = request.files['image']
            file_path = save_uploaded_file(image_file, 'image')
            if file_path:
                emotion_data = emotion_analyzer.analyze_image_emotion(file_path)
                # Clean up uploaded file
                os.remove(file_path)
            
        elif 'audio' in request.files:
            # Audio emotion analysis
            audio_file = request.files['audio']
            file_path = save_uploaded_file(audio_file, 'audio')
            if file_path:
                emotion_data = emotion_analyzer.analyze_audio_emotion(file_path)
                # Clean up uploaded file
                os.remove(file_path)
        
        if not emotion_data:
            return jsonify({'error': 'No valid input provided'}), 400
        
        # Store emotion data in memory system
        emotional_memory.process_interaction(user.id, emotion_data)
        
        # Emit real-time update
        websocket_handler.emit_emotion_update(user.id, emotion_data)
        
        return jsonify({
            'emotion_data': emotion_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Emotion analysis error: {e}")
        return jsonify({'error': 'Emotion analysis failed'}), 500

@app.route('/api/emotion/history', methods=['GET'])
@token_required
def get_emotion_history():
    """Get user's emotion analysis history"""
    try:
        user = request.current_user
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get emotion history from memory system
        history = emotional_memory.get_emotion_history(user.id, limit, offset)
        
        return jsonify({
            'history': history,
            'total': len(history)
        })
        
    except Exception as e:
        logger.error(f"Get emotion history error: {e}")
        return jsonify({'error': 'Failed to get emotion history'}), 500

# Art generation endpoints
@app.route('/api/art/generate', methods=['POST'])
@token_required
@limiter.limit("10 per minute")
def generate_art():
    """Generate neuromorphic art based on emotion analysis"""
    try:
        user = request.current_user
        data = request.get_json()
        
        emotion_data = data.get('emotion_data')
        style_preferences = data.get('style_preferences', {})
        
        if not emotion_data:
            return jsonify({'error': 'Emotion data is required'}), 400
        
        # Get user's artistic preferences from memory
        user_preferences = artistic_memory.get_user_preferences(user.id)
        
        # Generate art
        artwork_data = art_generator.generate_artwork(
            emotion_data, 
            style_preferences, 
            user_preferences
        )
        
        if not artwork_data:
            return jsonify({'error': 'Art generation failed'}), 500
        
        # Save artwork to database
        artwork_record = {
            'user_id': user.id,
            'title': artwork_data.get('title', 'Untitled'),
            'description': artwork_data.get('description', ''),
            'emotion_data': emotion_data,
            'style_data': artwork_data.get('style_data', {}),
            'image_data': artwork_data.get('image_data'),
            'metadata': artwork_data.get('metadata', {})
        }
        
        artwork = db_manager.create_artwork(artwork_record)
        
        # Update artistic memory
        artistic_memory.process_interaction(user.id, artwork_data)
        
        # Emit real-time update
        websocket_handler.emit_art_generation_complete(user.id, artwork_data)
        
        return jsonify({
            'artwork': {
                'id': artwork.id,
                'title': artwork.title,
                'description': artwork.description,
                'image_data': artwork.image_data,
                'emotion_data': artwork.emotion_data,
                'style_data': artwork.style_data,
                'metadata': artwork.metadata,
                'created_at': artwork.created_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Art generation error: {e}")
        return jsonify({'error': 'Art generation failed'}), 500

@app.route('/api/art/gallery', methods=['GET'])
@token_required
def get_art_gallery():
    """Get user's art gallery"""
    try:
        user = request.current_user
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        artworks = db_manager.get_user_artworks(user.id, limit, offset)
        
        gallery = []
        for artwork in artworks:
            gallery.append({
                'id': artwork.id,
                'title': artwork.title,
                'description': artwork.description,
                'image_data': artwork.image_data,
                'emotion_data': artwork.emotion_data,
                'style_data': artwork.style_data,
                'metadata': artwork.metadata,
                'likes': artwork.likes,
                'views': artwork.views,
                'created_at': artwork.created_at.isoformat()
            })
        
        return jsonify({
            'gallery': gallery,
            'total': len(gallery)
        })
        
    except Exception as e:
        logger.error(f"Get gallery error: {e}")
        return jsonify({'error': 'Failed to get gallery'}), 500

# Narrative generation endpoints
@app.route('/api/narrative/generate', methods=['POST'])
@token_required
@limiter.limit("15 per minute")
def generate_narrative():
    """Generate narrative for artwork"""
    try:
        user = request.current_user
        data = request.get_json()
        
        artwork_id = data.get('artwork_id')
        narrative_style = data.get('style', 'poetic')
        
        if not artwork_id:
            return jsonify({'error': 'Artwork ID is required'}), 400
        
        # Get artwork from database
        artwork = db_manager.get_artwork_by_id(artwork_id)
        if not artwork or artwork.user_id != user.id:
            return jsonify({'error': 'Artwork not found'}), 404
        
        # Generate narrative
        narrative_data = narrative_generator.generate_narrative(
            artwork.emotion_data,
            artwork.style_data,
            artwork.metadata,
            narrative_style
        )
        
        if not narrative_data:
            return jsonify({'error': 'Narrative generation failed'}), 500
        
        # Update artwork with narrative
        artwork.metadata = artwork.metadata or {}
        artwork.metadata['narrative'] = narrative_data
        db_manager.session.commit()
        
        # Emit real-time update
        websocket_handler.emit_narrative_complete(user.id, narrative_data)
        
        return jsonify({
            'narrative': narrative_data,
            'artwork_id': artwork_id
        })
        
    except Exception as e:
        logger.error(f"Narrative generation error: {e}")
        return jsonify({'error': 'Narrative generation failed'}), 500

# Memory system endpoints
@app.route('/api/memory/patterns', methods=['GET'])
@token_required
def get_memory_patterns():
    """Get user's emotional and artistic patterns"""
    try:
        user = request.current_user
        
        emotional_patterns = emotional_memory.get_user_patterns(user.id)
        artistic_patterns = artistic_memory.get_user_patterns(user.id)
        
        return jsonify({
            'emotional_patterns': emotional_patterns,
            'artistic_patterns': artistic_patterns
        })
        
    except Exception as e:
        logger.error(f"Get memory patterns error: {e}")
        return jsonify({'error': 'Failed to get memory patterns'}), 500

@app.route('/api/memory/recommendations', methods=['GET'])
@token_required
def get_recommendations():
    """Get personalized recommendations"""
    try:
        user = request.current_user
        
        emotional_recs = emotional_memory.get_personalized_recommendations(user.id)
        artistic_recs = artistic_memory.get_personalized_recommendations(user.id)
        
        return jsonify({
            'emotional_recommendations': emotional_recs,
            'artistic_recommendations': artistic_recs
        })
        
    except Exception as e:
        logger.error(f"Get recommendations error: {e}")
        return jsonify({'error': 'Failed to get recommendations'}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to NeuroCanvas'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_user_room')
def handle_join_user_room(data):
    """Join user-specific room for real-time updates"""
    user_id = data.get('user_id')
    if user_id:
        room = f"user_{user_id}"
        join_room(room)
        emit('joined_room', {'room': room})

@socketio.on('leave_user_room')
def handle_leave_user_room(data):
    """Leave user-specific room"""
    user_id = data.get('user_id')
    if user_id:
        room = f"user_{user_id}"
        leave_room(room)
        emit('left_room', {'room': room})

# Serve frontend files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve frontend files"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Initialize database
    db_manager.init_db()
    
    # Create upload directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    for subdir in ['image', 'audio', 'video']:
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, subdir), exist_ok=True)
    
    logger.info("Starting NeuroCanvas application...")
    
    # Run the application
    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
