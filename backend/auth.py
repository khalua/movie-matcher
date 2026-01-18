from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from models import User, CircleMember, Circle


def get_circle_from_header():
    """Extract and validate circle_id from X-Circle-Id header"""
    circle_id = request.headers.get('X-Circle-Id')
    if not circle_id:
        return None, jsonify({'error': 'X-Circle-Id header required'}), 400

    try:
        circle_id = int(circle_id)
    except ValueError:
        return None, jsonify({'error': 'Invalid circle ID'}), 400

    circle = Circle.query.get(circle_id)
    if not circle or not circle.is_active:
        return None, jsonify({'error': 'Circle not found'}), 404

    return circle, None, None


def circle_required(f):
    """Decorator to validate user is member of circle in X-Circle-Id header"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_email = get_jwt_identity()
        user = User.query.filter_by(email=current_user_email).first()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        circle, error_response, status_code = get_circle_from_header()
        if error_response:
            return error_response, status_code

        # Check user is member
        member = CircleMember.query.filter_by(
            circle_id=circle.id,
            user_id=user.id
        ).first()

        if not member:
            return jsonify({'error': 'Not a member of this circle'}), 403

        # Pass circle and user to endpoint
        kwargs['circle'] = circle
        kwargs['user'] = user
        kwargs['member'] = member
        return f(*args, **kwargs)

    return decorated_function


def circle_admin_required(f):
    """Decorator to validate user is admin of circle"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_email = get_jwt_identity()
        user = User.query.filter_by(email=current_user_email).first()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        circle, error_response, status_code = get_circle_from_header()
        if error_response:
            return error_response, status_code

        member = CircleMember.query.filter_by(
            circle_id=circle.id,
            user_id=user.id,
            role='admin'
        ).first()

        if not member:
            return jsonify({'error': 'Admin access required'}), 403

        kwargs['circle'] = circle
        kwargs['user'] = user
        kwargs['member'] = member
        return f(*args, **kwargs)

    return decorated_function


def site_admin_required(f):
    """Decorator to validate user is site admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_email = get_jwt_identity()
        user = User.query.filter_by(email=current_user_email).first()

        if not user or not user.is_site_admin:
            return jsonify({'error': 'Site admin access required'}), 403

        kwargs['user'] = user
        return f(*args, **kwargs)

    return decorated_function
