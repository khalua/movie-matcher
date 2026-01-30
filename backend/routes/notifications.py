from flask import Blueprint, Response, request, jsonify, stream_with_context
from flask_jwt_extended import decode_token
from models import User, CircleMember, Circle
import json
import logging
import queue
import threading

notifications_bp = Blueprint('notifications', __name__)
logger = logging.getLogger(__name__)

# In-memory store for active SSE connections
# Key: "user_id:circle_id", Value: Queue for sending events
active_connections = {}
connections_lock = threading.Lock()


def get_connection_key(user_id, circle_id):
    return f"{user_id}:{circle_id}"


def register_connection(user_id, circle_id):
    """Register a new SSE connection and return its event queue"""
    key = get_connection_key(user_id, circle_id)
    event_queue = queue.Queue()
    with connections_lock:
        # Close any existing connection for this user/circle
        if key in active_connections:
            logger.info(f"Replacing existing connection for {key}")
        active_connections[key] = event_queue
    logger.info(f"SSE connection registered: user={user_id}, circle={circle_id}, total connections: {len(active_connections)}")
    return event_queue


def unregister_connection(user_id, circle_id):
    """Remove an SSE connection"""
    key = get_connection_key(user_id, circle_id)
    with connections_lock:
        if key in active_connections:
            del active_connections[key]
    logger.info(f"SSE connection unregistered: user={user_id}, circle={circle_id}")


def broadcast_to_circle(circle_id, event_type, data, exclude_user_id=None):
    """
    Broadcast an event to all connected users in a circle.
    Optionally exclude a specific user (e.g., the sender).
    """
    logger.info(f"Broadcasting {event_type} to circle {circle_id}, exclude_user={exclude_user_id}")
    logger.info(f"Active connections: {list(active_connections.keys())}")
    sent_count = 0
    with connections_lock:
        for key, event_queue in active_connections.items():
            conn_user_id, conn_circle_id = key.split(':')
            if int(conn_circle_id) == circle_id:
                if exclude_user_id and int(conn_user_id) == exclude_user_id:
                    logger.info(f"Skipping user {conn_user_id} (sender)")
                    continue
                try:
                    event_queue.put_nowait({
                        'event': event_type,
                        'data': data
                    })
                    sent_count += 1
                    logger.info(f"Sent to connection {key}")
                except queue.Full:
                    logger.warning(f"Queue full for connection {key}")
    logger.info(f"Broadcast complete: sent to {sent_count} connections")


@notifications_bp.route('/stream', methods=['GET'])
def sse_stream():
    """
    SSE endpoint for real-time notifications.
    Requires JWT token as query parameter: ?token=<jwt>
    Requires circle_id as query parameter: ?circle_id=<id>
    """
    # Get token from query param (SSE can't use headers easily)
    token = request.args.get('token')
    circle_id = request.args.get('circle_id')

    if not token or not circle_id:
        return jsonify({'error': 'Token and circle_id required'}), 400

    try:
        circle_id = int(circle_id)
    except ValueError:
        return jsonify({'error': 'Invalid circle_id'}), 400

    # Verify JWT manually
    try:
        decoded = decode_token(token)
        user_email = decoded['sub']
    except Exception as e:
        logger.error(f"JWT verification failed: {e}")
        return jsonify({'error': 'Invalid token'}), 401

    # Get user and verify circle membership
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    circle = Circle.query.get(circle_id)
    if not circle or not circle.is_active:
        return jsonify({'error': 'Circle not found'}), 404

    member = CircleMember.query.filter_by(
        circle_id=circle_id,
        user_id=user.id
    ).first()

    if not member and not user.is_site_admin:
        return jsonify({'error': 'Not a member of this circle'}), 403

    def generate():
        event_queue = register_connection(user.id, circle_id)
        logger.info(f"Generator started for user={user.id}, circle={circle_id}")
        try:
            # Send initial connection confirmation
            yield f"event: connected\ndata: {json.dumps({'user_id': user.id, 'circle_id': circle_id})}\n\n"

            while True:
                try:
                    # Wait for events with timeout (for keepalive)
                    event = event_queue.get(timeout=30)
                    logger.info(f"Generator yielding event: {event['event']} for user={user.id}")
                    yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
                except queue.Empty:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
        except GeneratorExit:
            logger.info(f"Generator exit for user={user.id}")
        finally:
            unregister_connection(user.id, circle_id)

    response = Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Access-Control-Allow-Origin': '*',  # Allow SSE from any origin
        }
    )
    return response
