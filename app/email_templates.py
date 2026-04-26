"""
bulk_messaging/email_templates.py
-----------------------------------
Renders polished, responsive HTML email templates for each campaign type.
Each template is a self-contained function returning a full HTML string.

Usage:
    from .email_templates import render_email_template

    html = render_email_template(
        campaign_type="discount",
        subject="20% Off This Week!",
        body="Dear Valued Client,\n\nHere is your exclusive offer…",
        unsubscribe_url="https://mtb.co.zw/unsubscribe/",
    )
"""

from __future__ import annotations
import textwrap


# ─────────────────────────────────────────────────────────────────────────────
# SHARED CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BRAND_COLOR   = "#2563EB"
BRAND_NAME    = "MTB Training"
BRAND_TAGLINE = "Empowering People. Enabling Excellence."
BRAND_WEBSITE = "https://mtb.co.zw"
BRAND_PHONE   = "+263 242 XXXXXX"
BRAND_EMAIL   = "info@mtb.co.zw"
BRAND_LOGO_URL = "https://mtb.co.zw/static/app/assets/images/logo.png"  # fallback text logo used if img fails

SOCIAL_LINKS = {
    "LinkedIn":  "https://linkedin.com/company/mtb",
    "Twitter":   "https://twitter.com/mtbtraining",
    "Facebook":  "https://facebook.com/mtbtraining",
}

# ─────────────────────────────────────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def render_email_template(
    campaign_type: str,
    subject: str,
    body: str,
    unsubscribe_url: str = "#",
) -> str:
    """
    Return a full HTML email string for the given campaign_type.

    campaign_type values: promotion | discount | announcement | reminder | seasonal
    Falls back to the promotion template for unknown types.
    """
    plain_body = _body_to_html_paras(body)

    builders = {
        "promotion":    _build_promotion,
        "discount":     _build_discount,
        "announcement": _build_announcement,
        "reminder":     _build_reminder,
        "seasonal":     _build_seasonal,
    }
    builder = builders.get(campaign_type, _build_promotion)
    return builder(subject=subject, body_html=plain_body, unsubscribe_url=unsubscribe_url)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _body_to_html_paras(text: str) -> str:
    """Convert plain-text body (newline-separated) to <p> tags."""
    lines = text.strip().split("\n")
    paras = []
    for line in lines:
        line = line.strip()
        if not line:
            paras.append("<br/>")
        else:
            paras.append(f"<p style='margin:0 0 12px 0;line-height:1.7'>{line}</p>")
    return "\n".join(paras)


def _footer(unsubscribe_url: str, accent: str = BRAND_COLOR) -> str:
    social_html = " &nbsp;|&nbsp; ".join(
        f"<a href='{url}' style='color:{accent};text-decoration:none'>{name}</a>"
        for name, url in SOCIAL_LINKS.items()
    )
    return f"""
    <!-- FOOTER -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:32px">
      <tr>
        <td style="background:#F1F5F9;border-radius:0 0 12px 12px;padding:28px 40px;text-align:center">
          <p style="margin:0 0 8px 0;font-size:13px;font-weight:700;color:#334155">
            {BRAND_NAME}
          </p>
          <p style="margin:0 0 12px 0;font-size:12px;color:#64748B;line-height:1.6">
            {BRAND_TAGLINE}<br/>
            <a href="mailto:{BRAND_EMAIL}" style="color:{accent};text-decoration:none">{BRAND_EMAIL}</a>
            &nbsp;·&nbsp; {BRAND_PHONE}
          </p>
          <p style="margin:0 0 14px 0;font-size:12px">
            {social_html}
          </p>
          <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.6">
            You received this email because you are a client of {BRAND_NAME}.<br/>
            <a href="{unsubscribe_url}" style="color:#94A3B8;text-decoration:underline">Unsubscribe</a>
            &nbsp;·&nbsp;
            <a href="{BRAND_WEBSITE}/privacy" style="color:#94A3B8;text-decoration:underline">Privacy Policy</a>
          </p>
        </td>
      </tr>
    </table>"""


def _wrapper(content: str, bg: str = "#F8FAFC") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<meta http-equiv="X-UA-Compatible" content="IE=edge"/>
<title>MTB Training</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background:{bg};font-family:'Segoe UI',Helvetica,Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{bg};padding:32px 16px">
  <tr>
    <td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#FFFFFF;border-radius:12px;
                    box-shadow:0 4px 24px rgba(0,0,0,.08)">
        <tr><td>{content}</td></tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE 1 — PROMOTION  (bold blue hero)
# ─────────────────────────────────────────────────────────────────────────────

def _build_promotion(subject: str, body_html: str, unsubscribe_url: str) -> str:
    accent = "#2563EB"
    content = f"""
    <!-- HEADER -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="background:linear-gradient(135deg,#2563EB 0%,#1D4ED8 100%);
                   border-radius:12px 12px 0 0;padding:40px;text-align:center">
          <p style="margin:0 0 8px 0;font-size:13px;font-weight:600;
                    color:rgba(255,255,255,.75);letter-spacing:.08em;text-transform:uppercase">
            {BRAND_NAME}
          </p>
          <h1 style="margin:0;font-size:26px;font-weight:700;color:#FFFFFF;line-height:1.3">
            {subject}
          </h1>
          <p style="margin:16px 0 0 0;font-size:13px;color:rgba(255,255,255,.7)">
            {BRAND_TAGLINE}
          </p>
        </td>
      </tr>
    </table>

    <!-- BODY -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:36px 40px;font-size:15px;color:#334155">
          {body_html}
        </td>
      </tr>
    </table>

    <!-- CTA -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 36px;text-align:center">
          <a href="{BRAND_WEBSITE}"
             style="display:inline-block;background:{accent};color:#FFFFFF;
                    font-weight:700;font-size:15px;padding:14px 36px;
                    border-radius:8px;text-decoration:none;letter-spacing:.02em">
            Explore Our Programmes →
          </a>
          <p style="margin:16px 0 0 0;font-size:12px;color:#94A3B8">
            Or reply to this email to speak with our team
          </p>
        </td>
      </tr>
    </table>

    {_footer(unsubscribe_url, accent)}
    """
    return _wrapper(content, bg="#EFF6FF")


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE 2 — DISCOUNT  (urgency-driven, purple accent + countdown badge)
# ─────────────────────────────────────────────────────────────────────────────

def _build_discount(subject: str, body_html: str, unsubscribe_url: str) -> str:
    accent = "#7C3AED"
    content = f"""
    <!-- TOP BANNER -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="background:{accent};border-radius:12px 12px 0 0;
                   padding:10px;text-align:center">
          <p style="margin:0;font-size:12px;font-weight:700;color:#FFFFFF;
                    letter-spacing:.1em;text-transform:uppercase">
            ⏰ &nbsp; Limited Time Offer — Act Now!
          </p>
        </td>
      </tr>
    </table>

    <!-- HERO -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="background:linear-gradient(135deg,#7C3AED,#5B21B6);padding:40px;text-align:center">
          <!-- Discount badge -->
          <table align="center" cellpadding="0" cellspacing="0">
            <tr>
              <td style="background:#FFFFFF;border-radius:999px;
                         padding:12px 28px;display:inline-block">
                <span style="font-size:34px;font-weight:900;color:{accent};line-height:1">
                  SAVE NOW
                </span>
              </td>
            </tr>
          </table>
          <h1 style="margin:20px 0 0 0;font-size:24px;font-weight:700;
                     color:#FFFFFF;line-height:1.3">
            {subject}
          </h1>
        </td>
      </tr>
    </table>

    <!-- BODY -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:36px 40px;font-size:15px;color:#334155">
          {body_html}
        </td>
      </tr>
    </table>

    <!-- OFFER BOX -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 16px">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="background:#FDF4FF;border:2px dashed {accent};
                        border-radius:10px;padding:20px">
            <tr>
              <td style="text-align:center">
                <p style="margin:0 0 6px 0;font-size:12px;font-weight:600;
                           color:{accent};text-transform:uppercase;letter-spacing:.06em">
                  Your Discount Code
                </p>
                <p style="margin:0;font-size:28px;font-weight:900;color:{accent};
                           font-family:monospace;letter-spacing:.1em">
                  MTB2024
                </p>
                <p style="margin:8px 0 0 0;font-size:12px;color:#64748B">
                  Use this code when enquiring · Offer subject to availability
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>

    <!-- CTA -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:16px 40px 36px;text-align:center">
          <a href="{BRAND_WEBSITE}"
             style="display:inline-block;background:{accent};color:#FFFFFF;
                    font-weight:700;font-size:15px;padding:14px 36px;
                    border-radius:8px;text-decoration:none">
            Claim Your Discount →
          </a>
        </td>
      </tr>
    </table>

    {_footer(unsubscribe_url, accent)}
    """
    return _wrapper(content, bg="#FAF5FF")


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE 3 — ANNOUNCEMENT  (clean, editorial green)
# ─────────────────────────────────────────────────────────────────────────────

def _build_announcement(subject: str, body_html: str, unsubscribe_url: str) -> str:
    accent = "#059669"
    content = f"""
    <!-- LOGO BAR -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:24px 40px 0;text-align:center">
          <p style="margin:0;font-size:18px;font-weight:800;color:{accent};letter-spacing:-.01em">
            {BRAND_NAME}
          </p>
          <p style="margin:2px 0 0 0;font-size:11px;color:#94A3B8;text-transform:uppercase;letter-spacing:.1em">
            {BRAND_TAGLINE}
          </p>
        </td>
      </tr>
    </table>

    <!-- DIVIDER -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:20px 40px">
          <div style="height:3px;background:linear-gradient(to right,{accent},#34D399,transparent)"></div>
        </td>
      </tr>
    </table>

    <!-- ANNOUNCEMENT LABEL -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 8px">
          <span style="background:#ECFDF5;color:{accent};font-size:11px;font-weight:700;
                       text-transform:uppercase;letter-spacing:.08em;
                       padding:4px 12px;border-radius:99px">
            📢 Announcement
          </span>
        </td>
      </tr>
    </table>

    <!-- SUBJECT -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 24px">
          <h1 style="margin:0;font-size:26px;font-weight:700;color:#0F172A;line-height:1.3">
            {subject}
          </h1>
        </td>
      </tr>
    </table>

    <!-- BODY -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 32px;font-size:15px;color:#334155;line-height:1.7">
          {body_html}
        </td>
      </tr>
    </table>

    <!-- CTA -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 36px;text-align:center">
          <a href="{BRAND_WEBSITE}"
             style="display:inline-block;background:{accent};color:#FFFFFF;
                    font-weight:700;font-size:15px;padding:14px 36px;
                    border-radius:8px;text-decoration:none">
            Learn More →
          </a>
        </td>
      </tr>
    </table>

    {_footer(unsubscribe_url, accent)}
    """
    return _wrapper(content, bg="#F0FDF4")


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE 4 — REMINDER  (warm amber, professional nudge)
# ─────────────────────────────────────────────────────────────────────────────

def _build_reminder(subject: str, body_html: str, unsubscribe_url: str) -> str:
    accent = "#D97706"
    content = f"""
    <!-- HEADER -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="background:linear-gradient(135deg,#F59E0B,#D97706);
                   border-radius:12px 12px 0 0;padding:36px 40px">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <p style="margin:0 0 4px 0;font-size:12px;font-weight:700;
                           color:rgba(255,255,255,.8);text-transform:uppercase;letter-spacing:.08em">
                  {BRAND_NAME}
                </p>
                <h1 style="margin:0;font-size:24px;font-weight:700;color:#FFFFFF;line-height:1.3">
                  {subject}
                </h1>
              </td>
              <td width="64" valign="middle" align="right">
                <div style="width:56px;height:56px;background:rgba(255,255,255,.2);
                             border-radius:50%;display:flex;align-items:center;justify-content:center;
                             font-size:28px;text-align:center;line-height:56px">
                  ⏰
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>

    <!-- BODY -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:36px 40px;font-size:15px;color:#334155">
          {body_html}
        </td>
      </tr>
    </table>

    <!-- HIGHLIGHT BOX -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 24px">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="background:#FFFBEB;border-left:4px solid {accent};
                        border-radius:0 8px 8px 0;padding:16px 20px">
            <tr>
              <td>
                <p style="margin:0;font-size:14px;font-weight:600;color:#92400E">
                  Don't let your training momentum stall.
                </p>
                <p style="margin:6px 0 0 0;font-size:13px;color:#B45309;line-height:1.5">
                  Renewing early may qualify you for our loyalty discount.
                  Contact us today to discuss your options.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>

    <!-- CTA -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 36px;text-align:center">
          <a href="mailto:{BRAND_EMAIL}?subject=Renewal Enquiry"
             style="display:inline-block;background:{accent};color:#FFFFFF;
                    font-weight:700;font-size:15px;padding:14px 36px;
                    border-radius:8px;text-decoration:none">
            Discuss Renewal →
          </a>
        </td>
      </tr>
    </table>

    {_footer(unsubscribe_url, accent)}
    """
    return _wrapper(content, bg="#FFFBEB")


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE 5 — SEASONAL  (festive, warm red-green gradient)
# ─────────────────────────────────────────────────────────────────────────────

def _build_seasonal(subject: str, body_html: str, unsubscribe_url: str) -> str:
    accent = "#DC2626"
    content = f"""
    <!-- FESTIVE HEADER -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="background:linear-gradient(135deg,#DC2626 0%,#B91C1C 50%,#166534 100%);
                   border-radius:12px 12px 0 0;padding:44px 40px;text-align:center">
          <p style="margin:0 0 6px 0;font-size:32px">🎄🎁✨</p>
          <h1 style="margin:0;font-size:26px;font-weight:700;color:#FFFFFF;line-height:1.3">
            {subject}
          </h1>
          <p style="margin:12px 0 0 0;font-size:13px;color:rgba(255,255,255,.75)">
            From the entire team at {BRAND_NAME}
          </p>
        </td>
      </tr>
    </table>

    <!-- BODY -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:36px 40px;font-size:15px;color:#334155">
          {body_html}
        </td>
      </tr>
    </table>

    <!-- OFFER BADGE -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 24px">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="background:linear-gradient(135deg,#FEF2F2,#FFF7ED);
                        border:2px solid #FECACA;border-radius:10px;padding:24px;text-align:center">
            <tr>
              <td>
                <p style="margin:0 0 4px 0;font-size:12px;font-weight:700;color:{accent};
                           text-transform:uppercase;letter-spacing:.08em">
                  Year-End Special
                </p>
                <p style="margin:0 0 8px 0;font-size:36px;font-weight:900;color:{accent}">
                  25% OFF
                </p>
                <p style="margin:0;font-size:13px;color:#7F1D1D;font-weight:500">
                  All programmes booked before 31 December 2024
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>

    <!-- CTA -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 40px 36px;text-align:center">
          <a href="{BRAND_WEBSITE}"
             style="display:inline-block;background:{accent};color:#FFFFFF;
                    font-weight:700;font-size:15px;padding:14px 36px;
                    border-radius:8px;text-decoration:none">
            Book Before Year End →
          </a>
        </td>
      </tr>
    </table>

    {_footer(unsubscribe_url, accent)}
    """
    return _wrapper(content, bg="#FFF1F2")