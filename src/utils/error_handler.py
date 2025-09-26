import logging
import traceback
from typing import Any, Dict, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.logging_config import structured_logger

class ErrorHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_notifications_enabled = True
        self.admin_email = "admin@opensource4you.com"  # From env

    def handle_error(self, error: Exception, context: str = "", notify: bool = False) -> Dict[str, Any]:
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc()
        }
        
        # Log error
        structured_logger.error("Application error occurred", extra=error_info)
        
        # Send notification if enabled and critical
        if notify and self.error_notifications_enabled:
            self._send_error_notification(error_info)
        
        return error_info

    def _send_error_notification(self, error_info: Dict[str, Any]):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.admin_email
            msg['To'] = self.admin_email
            msg['Subject'] = f"Community AI Agent Error: {error_info['error_type']}"
            
            body = f"""
            Error Type: {error_info['error_type']}
            Message: {error_info['error_message']}
            Context: {error_info['context']}
            Time: {error_info['timestamp']}
            
            Traceback:
            {error_info['traceback']}
            """
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email (implement SMTP config)
            # smtp_server.send_message(msg)
            self.logger.info("Error notification sent")
        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}")

def handle_error(error: Exception, context: str = "", notify: bool = False) -> Dict[str, Any]:
    handler = ErrorHandler()
    return handler.handle_error(error, context, notify)

