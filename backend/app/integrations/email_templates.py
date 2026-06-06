"""Email-client-safe HTML templates that reproduce the LegacyVault stitch designs.

The stitch mockups style everything through the Tailwind CDN ``<script>`` + an
icon font, none of which run in email clients (Gmail/Outlook/Apple Mail strip
JS). These templates re-create the same "obsidian + indigo" design using
table-based layout, inline styles, and one media query — so they render
identically on a phone and on a desktop mail client. Icon glyphs are emoji
(the only cross-client icon option that needs no hosted images).

The original stitch HTML is kept verbatim in ``email_assets/`` as the design
reference these were built from.
"""

# ----- Design tokens (from the stitch tailwind theme) -----
BG = "#051424"
SURFACE = "#122131"
SURFACE_LOW = "#0b1a2b"
SURFACE_HIGH = "#1c2b3c"
ON_SURFACE = "#d4e4fa"
ON_SURFACE_VAR = "#c7c6cd"
OUTLINE = "#22303f"
INDIGO = "#c3c0ff"
ON_INDIGO = "#1d00a5"
SECONDARY_CONTAINER = "#3626ce"
ON_SECONDARY_CONTAINER = "#dcd9ff"
TERTIARY = "#4edea3"
ERROR = "#ffb4ab"
ON_ERROR = "#690005"
MUTED = "#6f7d92"
FONT = "'Helvetica Neue',Helvetica,Arial,'Segoe UI',sans-serif"

HERO_IMG = (
    "https://lh3.googleusercontent.com/aida-public/AB6AXuCfbft0Z6S5kk5bu6jUcZzMrNXAGP8TDfptwzBSU2Xo-"
    "3hNFEcJBMqZdUJfD0fpOWEawxmkBIRxaT_Yv1M_luwi5n6V8FGH3CN5C5lxPKxZdA7uom7aSpSXrHBVaf46k7uL26Dcz7i3q5"
    "jcNn-K2xzNIgofWtEyP-97GAko9i6--cI0B5cqsOjsJN82a3d51Ptg6H_EuUmP4xkapH-cZMvlEQEosQEAtNH5EAvR-"
    "D3QKft6LiR1w8eaTZVOuw_khRReLc3rcJhv7Vtr"
)


def _chip(glyph: str, bg: str, size: int = 44, radius: int = 12, font: int = 22) -> str:
    return (
        f'<span style="display:inline-block;width:{size}px;height:{size}px;line-height:{size}px;'
        f'border-radius:{radius}px;background:{bg};text-align:center;font-size:{font}px;">{glyph}</span>'
    )


def _btn(label: str, bg: str, fg: str, *, radius: int = 10, full: bool = False, glyph: str | None = None) -> str:
    inner = (f"{glyph}&nbsp;&nbsp;" if glyph else "") + label
    width = ' width="100%"' if full else ""
    cls = "stack" if full else "stack"
    display = "block" if full else "inline-block"
    return (
        f'<table role="presentation"{width} class="{cls}" cellpadding="0" cellspacing="0" style="margin:0 auto;">'
        f'<tr><td align="center" bgcolor="{bg}" style="border-radius:{radius}px;">'
        f'<a href="#" style="display:{display};padding:15px 30px;font-family:{FONT};font-size:15px;'
        f'font-weight:600;color:{fg};text-align:center;">{inner}</a>'
        "</td></tr></table>"
    )


def _feature_card(glyph: str, chip_bg: str, title: str, desc: str) -> str:
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{SURFACE};border:1px solid {OUTLINE};border-radius:12px;"><tr>'
        f'<td valign="top" style="padding:16px 4px 16px 16px;width:60px;">{_chip(glyph, "#1a2440", radius=10, font=20)}</td>'
        f'<td valign="top" style="padding:16px 16px 16px 8px;font-family:{FONT};">'
        f'<div style="font-size:16px;font-weight:600;color:{ON_SURFACE};margin-bottom:4px;">{title}</div>'
        f'<div style="font-size:14px;line-height:21px;color:{ON_SURFACE_VAR};">{desc}</div>'
        "</td></tr></table>"
    )


def _spacer(height: int = 14) -> str:
    return f'<div style="line-height:{height}px;height:{height}px;font-size:1px;">&nbsp;</div>'


def _header() -> str:
    return (
        f'<tr><td class="px" style="background:{SURFACE_LOW};padding:18px 28px;border-bottom:1px solid {OUTLINE};'
        'border-top-left-radius:16px;border-top-right-radius:16px;">'
        '<table role="presentation" width="100%"><tr>'
        f'<td style="font-family:{FONT};font-size:20px;font-weight:700;color:{ON_SURFACE};letter-spacing:-0.01em;">LegacyVault</td>'
        f'<td align="right" style="font-family:{FONT};font-size:12px;font-weight:600;color:{INDIGO};">'
        f'{_chip("&#128737;&#65039;", "#16233a", size=30, radius=8, font=14)}</td>'
        "</tr></table></td></tr>"
    )


def _footer(note: str, links: list[str], copyright_: str) -> str:
    link_html = " &nbsp;&middot;&nbsp; ".join(
        f'<a href="#" style="color:{ON_SURFACE_VAR};text-decoration:none;">{label}</a>' for label in links
    )
    links_row = (
        f'<p style="margin:0 0 10px 0;font-family:{FONT};font-size:12px;color:{ON_SURFACE_VAR};">{link_html}</p>'
        if links
        else ""
    )
    return (
        f'<tr><td class="px" style="background:{SURFACE_LOW};padding:22px 28px;border-top:1px solid {OUTLINE};'
        'border-bottom-left-radius:16px;border-bottom-right-radius:16px;text-align:center;">'
        f'<p style="margin:0 0 10px 0;font-family:{FONT};font-size:12px;line-height:18px;color:{ON_SURFACE_VAR};opacity:0.85;">{note}</p>'
        f"{links_row}"
        f'<p style="margin:0;font-family:{FONT};font-size:11px;color:{MUTED};">{copyright_}</p>'
        "</td></tr>"
    )


def _doc(title: str, preheader: str, container_rows: str) -> str:
    style = (
        "body{margin:0;padding:0;background:#051424;}"
        "table{border-collapse:collapse;}"
        "img{border:0;line-height:100%;outline:none;text-decoration:none;}"
        "a{text-decoration:none;}"
        ".container{width:600px;max-width:600px;}"
        "@media only screen and (max-width:620px){"
        ".container{width:100%!important;}"
        ".px{padding-left:22px!important;padding-right:22px!important;}"
        ".h1{font-size:26px!important;line-height:32px!important;}"
        ".stack{width:100%!important;}"
        "}"
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<meta name="x-apple-disable-message-reformatting">'
        '<meta name="color-scheme" content="dark light">'
        f"<title>{title}</title>"
        f"<style>{style}</style></head>"
        '<body style="margin:0;padding:0;background:#051424;">'
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:#051424;font-size:1px;line-height:1px;">{preheader}</div>'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#051424;">'
        '<tr><td align="center" style="padding:24px 12px;">'
        '<table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" '
        f'style="background:{SURFACE};border:1px solid {OUTLINE};border-radius:16px;overflow:hidden;">'
        f"{container_rows}"
        "</table></td></tr></table></body></html>"
    )


def _h1(text: str) -> str:
    return (
        f'<h1 class="h1" style="margin:0;font-family:{FONT};font-size:30px;line-height:38px;'
        f'font-weight:700;color:{ON_SURFACE};">{text}</h1>'
    )


def _p(text: str, *, size: int = 16) -> str:
    return (
        f'<p style="margin:0;font-family:{FONT};font-size:{size}px;line-height:26px;color:{ON_SURFACE_VAR};">{text}</p>'
    )


# ---------------------------------------------------------------------------
# Stitch-design emails
# ---------------------------------------------------------------------------

def welcome_email(full_name: str) -> tuple[str, str, str]:
    steps = (
        _feature_card("&#128274;", "#1a2440", "1. Secure your assets",
                      "Upload legal documents, private keys, and encrypted memories into your fortified vault.")
        + _spacer(12)
        + _feature_card("&#128106;", "#1a2440", "2. Assign your heirs",
                        "Designate the specific individuals who will inherit your digital and physical estate.")
        + _spacer(12)
        + _feature_card("&#128220;", "#1a2440", "3. Set your rules",
                        "Configure precise conditions for the release of your assets, ensuring your intent is executed.")
    )
    badge = (
        f'<table role="presentation" align="center" cellpadding="0" cellspacing="0" style="margin:0 auto;">'
        f'<tr><td style="background:#0e2236;border-radius:999px;padding:8px 16px;font-family:{FONT};'
        f'font-size:12px;color:{ON_SURFACE_VAR};">&#128274;&nbsp; End-to-End Encryption Enabled</td></tr></table>'
    )
    body = (
        f'<tr><td class="px" style="padding:34px 28px;text-align:center;">'
        f"{_h1('Your legacy is now secure.')}"
        f"{_spacer(20)}"
        f'<img src="{HERO_IMG}" alt="Secure Digital Vault" width="544" '
        f'style="display:block;width:100%;max-width:544px;height:auto;border-radius:12px;border:1px solid {OUTLINE};">'
        f"{_spacer(22)}"
        f'<div style="text-align:left;">'
        f"{_p('Welcome to a new era of digital stewardship. LegacyVault was built for individuals who understand that true wealth isn&rsquo;t just about the assets you hold, but how you protect and pass them on.')}"
        f"{_spacer(14)}"
        f"{_p('In an increasingly fragmented digital world, your final wishes and most sensitive assets deserve a sanctuary as permanent as your legacy. We are honored to be your chosen guardians.', size=15)}"
        "</div>"
        f"{_spacer(22)}"
        f'<div style="text-align:left;">{steps}</div>'
        f"{_spacer(26)}"
        f'{_btn("Enter the Vault", INDIGO, ON_INDIGO, radius=999)}'
        f"{_spacer(20)}"
        f"{badge}"
        "</td></tr>"
    )
    container = _header() + body + _footer(
        "Your data is protected by military-grade encryption. Access is restricted solely to you and your verified heirs upon the meeting of your specified conditions.",
        ["Privacy Policy", "Terms of Service", "Security Whitepaper"],
        "&copy; 2026 LegacyVault Global. All rights reserved.",
    )
    text = (
        f"Welcome to LegacyVault, {full_name}.\n\n"
        "Your legacy is now secure. Next steps:\n"
        "1. Secure your assets\n2. Assign your heirs\n3. Set your rules\n"
    )
    return "Welcome to LegacyVault", _doc("Welcome to LegacyVault", "Your legacy is now secure.", container), text


def security_alert_email(full_name: str, device: str | None, ip_address: str | None, timestamp: str) -> tuple[str, str, str]:
    device_label = device or "Unknown device"
    ip_label = ip_address or "Unknown IP"

    def detail_row(glyph: str, label: str, value: str) -> str:
        return (
            '<tr><td valign="middle" style="padding:12px 0;width:52px;">'
            f'{_chip(glyph, "#16233a", size=38, radius=10, font=18)}</td>'
            f'<td valign="middle" style="padding:12px 0;font-family:{FONT};">'
            f'<div style="font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:{ON_SURFACE_VAR};opacity:0.7;">{label}</div>'
            f'<div style="font-size:15px;font-weight:600;color:{ON_SURFACE};">{value}</div></td></tr>'
        )

    banner = (
        f'<tr><td class="px" style="background:#1f1416;padding:38px 28px;text-align:center;">'
        f'<div style="margin-bottom:16px;">{_chip("&#9888;&#65039;", "#2a1416", size=64, radius=999, font=30)}</div>'
        f'<h1 class="h1" style="margin:0 0 6px 0;font-family:{FONT};font-size:26px;line-height:32px;font-weight:700;color:{ON_SURFACE};">New Security Alert: Action Required</h1>'
        f'<p style="margin:0;font-family:{FONT};font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:{ERROR};">High Priority Notification</p>'
        "</td></tr>"
    )
    device_card = (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{SURFACE_LOW};border:1px solid {OUTLINE};border-radius:14px;">'
        f'<tr><td style="padding:6px 20px;">'
        '<table role="presentation" width="100%">'
        + detail_row("&#128241;", "Device Information", device_label)
        + detail_row("&#127760;", "IP Address", ip_label)
        + detail_row("&#128338;", "Timestamp", timestamp)
        + "</table></td></tr></table>"
    )
    body = (
        f'<tr><td class="px" style="padding:30px 28px;">'
        f"{_p(f'Hello {full_name}, we detected a login attempt from a new device. If this wasn&rsquo;t you, please secure your vault immediately to prevent unauthorized access.')}"
        f"{_spacer(20)}"
        f"{device_card}"
        f"{_spacer(24)}"
        f'{_btn("Secure My Account", ERROR, ON_ERROR, full=True, glyph="&#128737;&#65039;")}'
        f"{_spacer(12)}"
        f'{_btn("I Recognize This Device", "transparent", ON_SURFACE_VAR, full=True)}'
        "</td></tr>"
    )
    container = _header() + banner + body + _footer(
        "This is an automated security notification. For your protection, our team cannot bypass vault encryption.",
        ["Help Center", "Privacy Policy", "Vault Security Guide"],
        "&copy; 2026 LegacyVault Digital Assets S.A. All rights reserved.",
    )
    text = (
        f"Security alert for {full_name}.\n"
        f"Device: {device_label}\nIP: {ip_label}\nTime: {timestamp}\n"
        "If this was not you, secure your account immediately."
    )
    return "New Security Alert: Action Required", _doc(
        "Security alert", f"New sign-in detected: {device_label}", container
    ), text


def heir_designation_email(heir_name: str, owner_name: str) -> tuple[str, str, str]:
    info_card = (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{SURFACE_LOW};border:1px solid {OUTLINE};border-radius:12px;"><tr>'
        f'<td valign="top" style="padding:18px 4px 18px 18px;width:44px;">{_chip("&#8505;&#65039;", "#10241b", size=32, radius=8, font=16)}</td>'
        f'<td valign="top" style="padding:18px 18px 18px 10px;font-family:{FONT};">'
        f'<div style="font-size:16px;font-weight:600;color:{ON_SURFACE};margin-bottom:4px;">Notice of Status</div>'
        f'<div style="font-size:14px;line-height:21px;color:{ON_SURFACE_VAR};">No action is required now. You will be notified if your access is ever needed. Your role as an heir is a position of trust, ensuring digital assets, memories, and legal documents remain secure for the future.</div>'
        "</td></tr></table>"
    )
    features = (
        _feature_card("&#128274;", "#1a2440", "Unshakeable Security",
                      "All data is encrypted using military-grade protocols, ensuring access is granted only when conditions are met.")
        + _spacer(12)
        + _feature_card("&#128065;&#65039;", "#1a2440", "Clear Directives",
                        "Heirs receive clear, step-by-step instructions on how to manage and receive the intended digital assets.")
    )
    body = (
        f'<tr><td class="px" style="padding:36px 28px;">'
        f'<div style="margin-bottom:18px;">{_chip("&#128106;", SECONDARY_CONTAINER, size=64, radius=999, font=30)}</div>'
        f"{_h1('You have been designated as a Legacy Heir')}"
        f"{_spacer(16)}"
        f"{_p(f'<span style=\"color:{ON_SURFACE};font-weight:600;\">{owner_name}</span> has designated you as a trusted beneficiary for their digital estate. This ensures that their legacy is preserved and transitioned to you according to their specific directives.')}"
        f"{_spacer(22)}"
        f"{info_card}"
        f"{_spacer(24)}"
        f'{_btn("Learn More About Being an Heir", INDIGO, ON_INDIGO, full=True)}'
        f"{_spacer(12)}"
        f'{_btn("View FAQs", "transparent", ON_SURFACE_VAR, full=True)}'
        f"{_spacer(24)}"
        f"{features}"
        f"{_spacer(22)}"
        f'<p style="margin:0;text-align:center;font-family:{FONT};font-size:11px;letter-spacing:0.14em;'
        f'text-transform:uppercase;color:{ON_SURFACE_VAR};opacity:0.6;">Generational Wealth &middot; Digital Sanctuary</p>'
        "</td></tr>"
    )
    container = _header() + body + _footer(
        "This is an automated notification from LegacyVault. If you believe you received this in error or wish to be removed as an heir, please contact our support team.",
        [],
        "&copy; 2026 LegacyVault International.",
    )
    text = (
        f"{owner_name} has designated you ({heir_name}) as a Legacy Heir on LegacyVault. "
        "No action is required now; you will be notified if your access is ever needed."
    )
    return "You have been designated as a Legacy Heir", _doc(
        "Legacy Heir designation", f"{owner_name} designated you as an heir.", container
    ), text


# ---------------------------------------------------------------------------
# Code emails (verification + password reset) — same design language
# ---------------------------------------------------------------------------

def _code_email(*, eyebrow: str, heading: str, intro: str, code: str, ttl_minutes: int, eyebrow_color: str) -> str:
    spaced = "&nbsp;".join(list(code))
    code_card = (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{SURFACE_LOW};border:1px solid {INDIGO};border-radius:14px;">'
        f'<tr><td align="center" style="padding:26px 16px;">'
        f'<div class="code" style="font-family:{FONT};font-size:40px;font-weight:700;letter-spacing:12px;color:{INDIGO};">{spaced}</div>'
        f'<div style="margin-top:10px;font-family:{FONT};font-size:13px;color:{ON_SURFACE_VAR};">This code expires in {ttl_minutes} minutes.</div>'
        "</td></tr></table>"
    )
    return (
        f'<tr><td class="px" style="padding:34px 28px;">'
        f'<div style="font-family:{FONT};font-size:12px;font-weight:700;letter-spacing:0.08em;color:{eyebrow_color};margin-bottom:8px;">{eyebrow}</div>'
        f"{_h1(heading)}"
        f"{_spacer(16)}"
        f"{_p(intro)}"
        f"{_spacer(22)}"
        f"{code_card}"
        "</td></tr>"
    )


def verification_code_email(full_name: str, code: str, ttl_minutes: int) -> tuple[str, str, str]:
    body = _code_email(
        eyebrow="VERIFICATION CODE",
        heading="Confirm it&rsquo;s you",
        intro=f"Hello {full_name}, enter this code in the LegacyVault app to verify your identity. Never share this code &mdash; our team will never ask for it.",
        code=code,
        ttl_minutes=ttl_minutes,
        eyebrow_color=INDIGO,
    )
    container = _header() + body + _footer(
        "If you didn&rsquo;t request this code, you can safely ignore this email.",
        [],
        "&copy; 2026 LegacyVault. Store once. Protect forever.",
    )
    text = (
        f"Hello {full_name}, your LegacyVault verification code is {code}. "
        f"It expires in {ttl_minutes} minutes. Never share this code."
    )
    return "Your LegacyVault verification code", _doc(
        "Verification code", f"Your verification code is {code}", container
    ), text


def password_reset_email(full_name: str, code: str, ttl_minutes: int) -> tuple[str, str, str]:
    body = _code_email(
        eyebrow="PASSWORD RESET",
        heading="Reset your password",
        intro=f"Hello {full_name}, enter this code in the LegacyVault app to set a new password. If you did not request a reset, you can safely ignore this email &mdash; your password will not change.",
        code=code,
        ttl_minutes=ttl_minutes,
        eyebrow_color=INDIGO,
    )
    container = _header() + body + _footer(
        "For your security, this code can be used once and expires shortly.",
        [],
        "&copy; 2026 LegacyVault. Store once. Protect forever.",
    )
    text = (
        f"Hello {full_name}, your LegacyVault password reset code is {code}. "
        f"It expires in {ttl_minutes} minutes. If you did not request this, ignore this email."
    )
    return "Reset your LegacyVault password", _doc(
        "Password reset", "Your password reset code", container
    ), text
