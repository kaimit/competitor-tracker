#!/usr/bin/env python3
"""
Email notifier for AI Model Release Tracker.

This module sends email notifications for new model releases.
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class EmailNotifier:
    """Email notification handler for model releases."""
    
    def __init__(self, config: Dict):
        """
        Initialize the email notifier.
        
        Args:
            config: Notifier configuration
        """
        self.config = config
        
        # Load SMTP settings from environment variables
        smtp_server_env = config.get('smtp_server_env')
        smtp_port_env = config.get('smtp_port_env')
        
        self.smtp_server = os.getenv(smtp_server_env) if smtp_server_env else config.get('smtp_server')
        self.smtp_port = int(os.getenv(smtp_port_env)) if smtp_port_env else config.get('smtp_port', 587)
        
        # Load credentials from environment variables
        username_env = config.get('username_env')
        password_env = config.get('password_env')
        self.username = os.getenv(username_env) if username_env else None
        self.password = os.getenv(password_env) if password_env else None
        
        # Load email addresses
        from_address_env = config.get('from_address_env')
        to_addresses_env = config.get('to_addresses_env')
        
        self.from_address = os.getenv(from_address_env) if from_address_env else config.get('from_address')
        
        # Handle to_addresses as either a single env var or a list in config
        if to_addresses_env:
            to_address = os.getenv(to_addresses_env)
            self.to_addresses = [addr.strip() for addr in to_address.split(',')] if to_address else []
        else:
            self.to_addresses = config.get('to_addresses', [])
        
        self.use_tls = config.get('use_tls', True)
        
        logger.info(f"Email notifier initialized with SMTP server: {self.smtp_server}")
    
    def send_notification(self, model_release: Dict) -> bool:
        """
        Send an email notification for a model release.
        
        Args:
            model_release: Dictionary containing model release information
            
        Returns:
            True if successful, False otherwise
        """
        if not self.smtp_server or not self.from_address or not self.to_addresses:
            logger.error("Cannot send email notification: Missing required configuration")
            return False
        
        subject = f"New Model Release: {model_release.get('title', 'Unknown Model')}"
        
        # Create email content
        html_content = self._create_email_content(model_release)
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_address
        msg['To'] = ', '.join(self.to_addresses)
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Use TLS if configured
            if self.use_tls:
                server.starttls()
            
            # Login if credentials are provided
            if self.username and self.password:
                server.login(self.username, self.password)
            
            # Send email
            server.sendmail(self.from_address, self.to_addresses, msg.as_string())
            server.quit()
            
            logger.info(f"Email notification sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    def _create_email_content(self, model_release: Dict) -> str:
        """
        Create HTML content for email notification.
        
        Args:
            model_release: Dictionary containing model release information
            
        Returns:
            HTML content for email
        """
        # Extract model information
        title = model_release.get('title', 'Unknown Model')
        source = model_release.get('source_name', 'Unknown Source')
        url = model_release.get('url', '#')
        date = model_release.get('date', datetime.now().isoformat())
        description = model_release.get('description', 'No description available')
        model_size = model_release.get('model_size', 'Unknown')
        
        # Format date if it's a string
        if isinstance(date, str):
            try:
                date_obj = datetime.fromisoformat(date.replace('Z', '+00:00'))
                date = date_obj.strftime('%Y-%m-%d %H:%M:%S UTC')
            except (ValueError, TypeError):
                pass
        
        # Create HTML content
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #0366d6; margin-top: 0; }}
                h2 {{ color: #586069; font-size: 18px; margin-top: 25px; }}
                .info {{ background-color: #f6f8fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .info p {{ margin: 5px 0; }}
                .description {{ border-left: 4px solid #0366d6; padding-left: 15px; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #586069; }}
                a {{ color: #0366d6; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>New AI Model Release Detected</h1>
            
            <div class="info">
                <p><strong>Model:</strong> {title}</p>
                <p><strong>Source:</strong> {source}</p>
                <p><strong>Date:</strong> {date}</p>
                <p><strong>Model Size:</strong> {model_size}</p>
                <p><strong>Link:</strong> <a href="{url}" target="_blank">View Details</a></p>
            </div>
            
            <h2>Description</h2>
            <div class="description">
                <p>{description}</p>
            </div>
            
            <div class="footer">
                <p>This notification was sent by the AI Model Release Tracker.</p>
                <p>Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        return html


# Example usage
if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    # Load environment variables
    load_dotenv()
    
    # Test configuration
    test_config = {
        'smtp_server_env': 'SMTP_SERVER',
        'smtp_port_env': 'SMTP_PORT',
        'from_address_env': 'EMAIL_USERNAME',
        'to_addresses_env': 'NOTIFY_EMAIL',
        'use_tls': True,
        'username_env': 'EMAIL_USERNAME',
        'password_env': 'EMAIL_PASSWORD'
    }
    
    # Test model release
    test_release = {
        'title': 'GPT-5 Test Model',
        'source_name': 'OpenAI Blog',
        'url': 'https://openai.com/blog/example',
        'date': datetime.now().isoformat(),
        'description': 'This is a test notification for a fictional model release.',
        'model_size': '175B'
    }
    
    notifier = EmailNotifier(test_config)
    success = notifier.send_notification(test_release)
    
    print(f"Notification sent: {success}")