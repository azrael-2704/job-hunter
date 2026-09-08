# tests/test_mailer.py
from unittest.mock import patch, MagicMock
from src.outreach.mailer import dispatch_email, get_email_credentials

def test_dry_run_dispatch_when_no_credentials():
    with patch.dict("os.environ", {}, clear=True):
        res = dispatch_email("recruiter@anthropic.com", "Application", "Hello recruiter")
        assert res["success"] is True
        assert res["status"] == "STAGED_READY"
        assert res["provider"] == "dry_run"

def test_smtp_dispatch_mock():
    mock_creds = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test@gmail.com",
        "smtp_pass": "secret",
        "sender_email": "test@gmail.com",
        "resend_api_key": None
    }
    with patch("src.outreach.mailer.get_email_credentials", return_value=mock_creds):
        with patch("smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            
            res = dispatch_email("recruiter@anthropic.com", "Test Subject", "Test Body")
            assert res["success"] is True
            assert res["status"] == "SENT"
            assert res["provider"] == "smtp"
            assert instance.sendmail.called
