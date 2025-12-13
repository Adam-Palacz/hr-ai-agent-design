"""Quick test script for Gmail SMTP credentials."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
GMAIL_USERNAME = os.getenv('GMAIL_USERNAME', '')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD', '')

def test_gmail_connection():
    """Test Gmail SMTP connection and credentials."""
    print("=" * 60)
    print("Gmail SMTP Connection Test")
    print("=" * 60)
    
    # Check if credentials are set
    if not GMAIL_USERNAME:
        print("❌ ERROR: GMAIL_USERNAME not set in .env file")
        return False
    
    if not GMAIL_PASSWORD:
        print("❌ ERROR: GMAIL_PASSWORD not set in .env file")
        return False
    
    print(f"✓ Username: {GMAIL_USERNAME}")
    print(f"✓ Password: {'*' * len(GMAIL_PASSWORD)} (hidden)")
    print()
    
    # Test SMTP connection
    print("Testing SMTP connection...")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        print("✓ Connected to smtp.gmail.com:587")
        print("✓ TLS started")
        
        # Test login
        print("Testing login...")
        server.login(GMAIL_USERNAME, GMAIL_PASSWORD)
        print("✓ Login successful!")
        
        server.quit()
        print()
        print("=" * 60)
        print("✅ SUCCESS: Gmail credentials are valid!")
        print("=" * 60)
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print()
        print("=" * 60)
        print("❌ AUTHENTICATION FAILED")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("Possible issues:")
        print("1. Wrong password - make sure you're using an App Password, not your regular Gmail password")
        print("2. 2-Step Verification not enabled - enable it first")
        print("3. App Password not created - create one at:")
        print("   https://myaccount.google.com/apppasswords")
        print()
        return False
        
    except smtplib.SMTPException as e:
        print()
        print("=" * 60)
        print("❌ SMTP ERROR")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        return False
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ CONNECTION ERROR")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("Possible issues:")
        print("1. No internet connection")
        print("2. Firewall blocking SMTP port 587")
        print("3. Gmail SMTP server unavailable")
        print()
        return False


def test_send_email():
    """Test sending an actual email."""
    if not GMAIL_USERNAME or not GMAIL_PASSWORD:
        print("❌ Cannot send test email: credentials not configured")
        return False
    
    test_email = input("\nEnter your email address to send a test email (or press Enter to skip): ").strip()
    if not test_email:
        print("Skipping test email send.")
        return True
    
    print(f"\nSending test email to {test_email}...")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Test Email - Gmail SMTP Configuration'
        msg['From'] = GMAIL_USERNAME
        msg['To'] = test_email
        
        html_content = """
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #4CAF50;">✅ Gmail SMTP Test Successful!</h2>
            <p>This is a test email to verify that your Gmail SMTP configuration is working correctly.</p>
            <p>If you received this email, your credentials are valid and emails can be sent.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">Sent from: {}</p>
          </body>
        </html>
        """.format(GMAIL_USERNAME)
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USERNAME, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✅ Test email sent successfully!")
        print(f"Check your inbox at {test_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test email: {str(e)}")
        return False


if __name__ == "__main__":
    # Test connection
    if test_gmail_connection():
        # Optionally send test email
        test_send_email()
    else:
        print("\nFix the issues above before testing email sending.")

