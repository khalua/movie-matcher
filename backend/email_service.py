"""Email service using Resend for transactional emails"""
import os
import resend


# Initialize Resend with API key
resend.api_key = os.getenv('RESEND_API_KEY')

# Email sender - use your verified domain in production
# For testing, Resend provides onboarding@resend.dev
FROM_EMAIL = os.getenv('FROM_EMAIL', 'Movie Matcher <onboarding@resend.dev>')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')


def send_password_reset_email(to_email: str, reset_token: str, display_name: str = None) -> bool:
    """
    Send password reset email to user.

    Args:
        to_email: User's email address
        reset_token: The password reset token
        display_name: User's display name (optional)

    Returns:
        True if email sent successfully, False otherwise
    """
    if not resend.api_key:
        print("Warning: RESEND_API_KEY not set, skipping email send")
        return False

    reset_url = f"{FRONTEND_URL}/reset-password/{reset_token}"
    greeting = f"Hi {display_name}," if display_name else "Hi,"

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #333;">Reset Your Password</h2>
        <p>{greeting}</p>
        <p>We received a request to reset your Movie Matcher password. Click the button below to create a new password:</p>
        <p style="margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Reset Password
            </a>
        </p>
        <p style="color: #666; font-size: 14px;">This link will expire in 1 hour.</p>
        <p style="color: #666; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">Movie Matcher - Find films you all love</p>
    </div>
    """

    text_content = f"""
{greeting}

We received a request to reset your Movie Matcher password.

Reset your password here: {reset_url}

This link will expire in 1 hour.

If you didn't request this, you can safely ignore this email.

---
Movie Matcher - Find films you all love
"""

    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset your Movie Matcher password",
            "html": html_content,
            "text": text_content
        })
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False
