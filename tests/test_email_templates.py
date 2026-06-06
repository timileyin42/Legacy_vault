from backend.app.integrations import email_templates


def _assert_email_safe_responsive(html: str):
    # Every template is now email-client-safe: no Tailwind/JS, inline styles,
    # a responsive viewport + media query, and a constrained 600px container.
    assert "<!DOCTYPE html>" in html
    assert 'name="viewport"' in html
    assert "@media only screen and (max-width:620px)" in html
    assert "max-width:600px" in html
    assert "cdn.tailwindcss.com" not in html
    assert "<script" not in html
    assert "LegacyVault" in html


def test_welcome_email_matches_stitch_design():
    subject, html, text = email_templates.welcome_email("Ada")
    assert subject == "Welcome to LegacyVault"
    _assert_email_safe_responsive(html)
    assert "Your legacy is now secure." in html
    assert "Secure your assets" in html and "Assign your heirs" in html and "Set your rules" in html


def test_security_alert_email_fills_device_details():
    subject, html, text = email_templates.security_alert_email("Ada", "iPhone 15 Pro", "82.14.92.10", "today")
    assert subject == "New Security Alert: Action Required"
    _assert_email_safe_responsive(html)
    assert "{{" not in html  # no unsubstituted placeholders
    assert "iPhone 15 Pro" in html and "82.14.92.10" in html and "today" in html
    assert "High Priority Notification" in html


def test_heir_designation_email_fills_owner():
    subject, html, text = email_templates.heir_designation_email("Sarah", "Julian")
    assert subject == "You have been designated as a Legacy Heir"
    _assert_email_safe_responsive(html)
    assert "Julian" in html
    assert "designated you as a trusted beneficiary" in html
    assert "Unshakeable Security" in html and "Clear Directives" in html


def test_verification_code_email_shows_code_and_ttl():
    subject, html, text = email_templates.verification_code_email("Ada", "482915", 10)
    _assert_email_safe_responsive(html)
    assert "482915" in text  # digits are rendered spaced in HTML; check plain text
    assert "10 minutes" in html


def test_password_reset_email_shows_code_and_safe_to_ignore():
    subject, html, text = email_templates.password_reset_email("Ada", "482915", 10)
    assert subject == "Reset your LegacyVault password"
    _assert_email_safe_responsive(html)
    assert "Reset your password" in html
    assert "482915" in text
    assert "ignore" in text.lower()
