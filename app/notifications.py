from django.core.mail import send_mail
from django.conf import settings


def send_churn_alert_email(organization, risk_score):
    subject = f"⚠ High Churn Risk Detected — {organization.name}"

    message = f"""
Client: {organization.name}
Risk Score: {risk_score}

The system detected behavioral signals indicating possible disengagement.

Recommended Action:
• Contact account stakeholder
• Review satisfaction trends
• Offer customized training intervention
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [organization.account_manager.email] if organization.account_manager else [],
        fail_silently=True
    )