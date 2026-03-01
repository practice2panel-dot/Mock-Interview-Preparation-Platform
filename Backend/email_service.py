"""
Email service for sending verification codes, password reset codes, and notifications.
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Email configuration from environment variables
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # App password

def send_email(to_email, subject, body_html, body_text=None):
    """
    Send an email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML email body
        body_text: Plain text email body (optional)
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return False, "Email configuration missing. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in .env file."
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add both plain text and HTML versions
        if body_text:
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)
        
        part2 = MIMEText(body_html, 'html')
        msg.attach(part2)
        
        # Connect to SMTP server and send
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True, None
    
    except Exception as e:
        return False, str(e)

def send_verification_code(to_email, code, full_name):
    """
    Send verification code email.
    
    Args:
        to_email: Recipient email address
        code: 6-digit verification code
        full_name: User's full name
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    subject = "Verify Your Email - Practice2Panel"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 5px 5px; }}
            .code {{ background-color: #fff; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #4f46e5; letter-spacing: 5px; margin: 20px 0; border-radius: 5px; border: 2px dashed #4f46e5; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Practice2Panel!</h1>
            </div>
            <div class="content">
                <p>Hi {full_name},</p>
                <p>Thank you for signing up! Please verify your email address by entering the verification code below:</p>
                <div class="code">{code}</div>
                <p>This code will expire in <strong>15 minutes</strong>.</p>
                <p>If you didn't create an account, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>© 2024 Practice2Panel. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
    Welcome to Practice2Panel!
    
    Hi {full_name},
    
    Thank you for signing up! Please verify your email address by entering the verification code below:
    
    Verification Code: {code}
    
    This code will expire in 15 minutes.
    
    If you didn't create an account, please ignore this email.
    
    © 2024 Practice2Panel. All rights reserved.
    """
    
    return send_email(to_email, subject, body_html, body_text)

def send_password_reset_code(to_email, code, full_name):
    """
    Send password reset code email.
    
    Args:
        to_email: Recipient email address
        code: 6-digit reset code
        full_name: User's full name
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    subject = "Password Reset - Practice2Panel"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 5px 5px; }}
            .code {{ background-color: #fff; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #dc2626; letter-spacing: 5px; margin: 20px 0; border-radius: 5px; border: 2px dashed #dc2626; }}
            .warning {{ background-color: #fef2f2; padding: 15px; border-left: 4px solid #dc2626; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Hi {full_name},</p>
                <p>We received a request to reset your password. Use the code below to reset your password:</p>
                <div class="code">{code}</div>
                <div class="warning">
                    <p><strong>⚠️ Security Notice:</strong></p>
                    <p>This code will expire in <strong>15 minutes</strong>.</p>
                    <p>If you didn't request a password reset, please ignore this email and your password will remain unchanged.</p>
                </div>
            </div>
            <div class="footer">
                <p>© 2024 Practice2Panel. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
    Password Reset Request
    
    Hi {full_name},
    
    We received a request to reset your password. Use the code below to reset your password:
    
    Reset Code: {code}
    
    ⚠️ Security Notice:
    This code will expire in 15 minutes.
    If you didn't request a password reset, please ignore this email and your password will remain unchanged.
    
    © 2024 Practice2Panel. All rights reserved.
    """
    
    return send_email(to_email, subject, body_html, body_text)

def send_welcome_email(to_email, full_name):
    """
    Send welcome email after successful verification.
    
    Args:
        to_email: Recipient email address
        full_name: User's full name
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    subject = "Welcome to Practice2Panel! 🎉"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #10b981; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 5px 5px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #4f46e5; color: white !important; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: 600; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Welcome to Practice2Panel!</h1>
            </div>
            <div class="content">
                <p>Hi {full_name},</p>
                <p>Your email has been successfully verified! You're all set to start your interview preparation journey.</p>
                <p>Get started by:</p>
                <ul>
                    <li>Practicing with our skill preparation modules</li>
                    <li>Taking mock AI interviews</li>
                    <li>Tracking your progress on the dashboard</li>
                </ul>
                <p style="text-align: center;">
                    <a href="#" class="button" style="color: white !important; background-color: #4f46e5; text-decoration: none; padding: 12px 24px; border-radius: 5px; display: inline-block; font-weight: 600;">Get Started</a>
                </p>
                <p>If you have any questions, feel free to reach out to our support team.</p>
            </div>
            <div class="footer">
                <p>© 2024 Practice2Panel. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
    🎉 Welcome to Practice2Panel!
    
    Hi {full_name},
    
    Your email has been successfully verified! You're all set to start your interview preparation journey.
    
    Get started by:
    - Practicing with our skill preparation modules
    - Taking mock AI interviews
    - Tracking your progress on the dashboard
    
    If you have any questions, feel free to reach out to our support team.
    
    © 2024 Practice2Panel. All rights reserved.
    """
    
    return send_email(to_email, subject, body_html, body_text)

def send_password_change_notification(to_email, full_name):
    """
    Send notification email after password change.
    
    Args:
        to_email: Recipient email address
        full_name: User's full name
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    subject = "Password Changed Successfully - Practice2Panel"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #059669; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 5px 5px; }}
            .warning {{ background-color: #fef2f2; padding: 15px; border-left: 4px solid #dc2626; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Changed Successfully</h1>
            </div>
            <div class="content">
                <p>Hi {full_name},</p>
                <p>Your password has been successfully changed.</p>
                <div class="warning">
                    <p><strong>⚠️ Security Notice:</strong></p>
                    <p>If you didn't make this change, please contact our support team immediately.</p>
                </div>
            </div>
            <div class="footer">
                <p>© 2024 Practice2Panel. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
    Password Changed Successfully
    
    Hi {full_name},
    
    Your password has been successfully changed.
    
    ⚠️ Security Notice:
    If you didn't make this change, please contact our support team immediately.
    
    © 2024 Practice2Panel. All rights reserved.
    """
    
    return send_email(to_email, subject, body_html, body_text)

