"""
task_email_lifecycle.py
=======================
Drop this file into your `app/` directory.

Provides:
  1. send_task_created_email(task)   — beautiful HTML email fired on Task creation
  2. run_lifecycle_automation()      — archives inactive clients after follow-up
     (prototype mode: "days" = minutes, so 14 days → 14 minutes)

Wire up in models.py (bottom of file):
─────────────────────────────────────
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    from app.task_email_lifecycle import send_task_created_email

    @receiver(post_save, sender=Task)
    def task_post_save(sender, instance, created, **kwargs):
        if created:
            send_task_created_email(instance)

Wire up lifecycle as a management command or celery beat:
─────────────────────────────────────────────────────────
    from app.task_email_lifecycle import run_lifecycle_automation
    run_lifecycle_automation()
"""

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from app.models import Task, ClientOrganization, CommunicationLog, ChurnAlert


# ══════════════════════════════════════════════════════════════════
#  SECTION 1 — TASK CREATED EMAIL
# ══════════════════════════════════════════════════════════════════

PRIORITY_META = {
    "high":   {"color": "#DC2626", "bg": "#FEF2F2", "border": "#FCA5A5", "label": "HIGH PRIORITY",   "icon": "🔴"},
    "medium": {"color": "#D97706", "bg": "#FFFBEB", "border": "#FCD34D", "label": "MEDIUM PRIORITY", "icon": "🟡"},
    "low":    {"color": "#059669", "bg": "#F0FDF4", "border": "#6EE7B7", "label": "LOW PRIORITY",    "icon": "🟢"},
}

STATUS_META = {
    "pending":     {"color": "#6B7280", "label": "Pending"},
    "in_progress": {"color": "#2563EB", "label": "In Progress"},
    "completed":   {"color": "#059669", "label": "Completed"},
    "overdue":     {"color": "#DC2626", "label": "Overdue"},
}


def _build_task_html(task: Task) -> str:
    p = PRIORITY_META.get(task.priority or "medium", PRIORITY_META["medium"])
    s = STATUS_META.get(task.status or "pending", STATUS_META["pending"])

    assigned_name = (
        task.assigned_to.get_full_name() or task.assigned_to.username
        if task.assigned_to else "Unassigned"
    )
    org_name     = task.related_organization.name if task.related_organization else "—"
    due_str      = task.due_date.strftime("%A, %d %B %Y") if task.due_date else "No deadline set"
    days_left    = task.days_to_deadline()
    urgency_note = ""
    if days_left is not None:
        if days_left < 0:
            urgency_note = f'<span style="color:#DC2626;font-weight:600;">⚠️ Overdue by {abs(days_left)} day(s)</span>'
        elif days_left == 0:
            urgency_note = '<span style="color:#D97706;font-weight:600;">⚡ Due today</span>'
        elif days_left <= 2:
            urgency_note = f'<span style="color:#D97706;font-weight:600;">⏳ Due in {days_left} day(s)</span>'

    description_html = (
        task.description.replace("\n", "<br>") if task.description else "<em>No description provided.</em>"
    )

    crm_url = getattr(settings, "CRM_BASE_URL", "http://localhost:8000")
    task_url = f"{crm_url}/tasks/"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>New Task Assigned</title>
</head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- WRAPPER -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F3F4F6;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);
                     border-radius:12px 12px 0 0;padding:36px 40px;text-align:center;">
            <p style="margin:0 0 6px;color:#93C5FD;font-size:13px;letter-spacing:2px;text-transform:uppercase;">
              ClientPulse CRM
            </p>
            <h1 style="margin:0;color:#FFFFFF;font-size:26px;font-weight:700;line-height:1.3;">
              📋 New Task Assigned
            </h1>
            <p style="margin:10px 0 0;color:#BFDBFE;font-size:14px;">
              You have a new task that requires your attention
            </p>
          </td>
        </tr>

        <!-- PRIORITY BADGE -->
        <tr>
          <td style="background:{p['bg']};border-left:4px solid {p['border']};
                     border-right:4px solid {p['border']};padding:14px 40px;text-align:center;">
            <span style="color:{p['color']};font-weight:700;font-size:13px;letter-spacing:1px;">
              {p['icon']}&nbsp;&nbsp;{p['label']}
            </span>
          </td>
        </tr>

        <!-- MAIN CARD -->
        <tr>
          <td style="background:#FFFFFF;border-radius:0 0 12px 12px;
                     padding:36px 40px;border:1px solid #E5E7EB;border-top:none;">

            <!-- TASK TITLE -->
            <h2 style="margin:0 0 24px;color:#111827;font-size:22px;font-weight:700;
                       border-bottom:2px solid #E5E7EB;padding-bottom:16px;">
              {task.title}
            </h2>

            <!-- META GRID -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
              <tr>
                <!-- LEFT COL -->
                <td width="50%" valign="top" style="padding-right:12px;">

                  <table cellpadding="0" cellspacing="0" width="100%">
                    <tr>
                      <td style="padding:10px 14px;background:#F9FAFB;border-radius:8px;margin-bottom:8px;display:block;">
                        <p style="margin:0;color:#6B7280;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                          Assigned To
                        </p>
                        <p style="margin:4px 0 0;color:#111827;font-size:15px;font-weight:600;">
                          👤 {assigned_name}
                        </p>
                      </td>
                    </tr>
                    <tr><td style="height:8px;"></td></tr>
                    <tr>
                      <td style="padding:10px 14px;background:#F9FAFB;border-radius:8px;">
                        <p style="margin:0;color:#6B7280;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                          Organisation
                        </p>
                        <p style="margin:4px 0 0;color:#111827;font-size:15px;font-weight:600;">
                          🏢 {org_name}
                        </p>
                      </td>
                    </tr>
                  </table>

                </td>

                <!-- RIGHT COL -->
                <td width="50%" valign="top" style="padding-left:12px;">

                  <table cellpadding="0" cellspacing="0" width="100%">
                    <tr>
                      <td style="padding:10px 14px;background:#F9FAFB;border-radius:8px;">
                        <p style="margin:0;color:#6B7280;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                          Due Date
                        </p>
                        <p style="margin:4px 0 0;color:#111827;font-size:15px;font-weight:600;">
                          📅 {due_str}
                        </p>
                        {"<p style='margin:4px 0 0;font-size:13px;'>" + urgency_note + "</p>" if urgency_note else ""}
                      </td>
                    </tr>
                    <tr><td style="height:8px;"></td></tr>
                    <tr>
                      <td style="padding:10px 14px;background:#F9FAFB;border-radius:8px;">
                        <p style="margin:0;color:#6B7280;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                          Status
                        </p>
                        <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:{s['color']};">
                          ● {s['label']}
                        </p>
                      </td>
                    </tr>
                  </table>

                </td>
              </tr>
            </table>

            <!-- DESCRIPTION -->
            <div style="background:#F8FAFC;border-left:4px solid #2563EB;
                        border-radius:0 8px 8px 0;padding:18px 20px;margin-bottom:28px;">
              <p style="margin:0 0 8px;color:#6B7280;font-size:11px;
                        text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                Task Description
              </p>
              <div style="color:#374151;font-size:14px;line-height:1.7;">
                {description_html}
              </div>
            </div>

            <!-- CTA BUTTON -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center" style="padding:8px 0 24px;">
                  <a href="{task_url}"
                     style="display:inline-block;background:linear-gradient(135deg,#1E3A5F,#2563EB);
                            color:#FFFFFF;text-decoration:none;font-size:15px;font-weight:700;
                            padding:14px 40px;border-radius:8px;letter-spacing:0.5px;">
                    View Task in CRM →
                  </a>
                </td>
              </tr>
            </table>

            <!-- DIVIDER -->
            <hr style="border:none;border-top:1px solid #E5E7EB;margin:0 0 20px;">

            <!-- FOOTER NOTE -->
            <p style="margin:0;color:#9CA3AF;font-size:12px;text-align:center;line-height:1.6;">
              This notification was sent automatically by ClientPulse CRM.<br>
              Please do not reply directly to this email.
            </p>

          </td>
        </tr>

        <!-- OUTER FOOTER -->
        <tr>
          <td style="padding:20px 0;text-align:center;">
            <p style="margin:0;color:#9CA3AF;font-size:11px;">
              © {timezone.now().year} ClientPulse · Automated Notification
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>
""".strip()


def _build_task_plain(task: Task) -> str:
    assigned_name = (
        task.assigned_to.get_full_name() or task.assigned_to.username
        if task.assigned_to else "Unassigned"
    )
    org_name = task.related_organization.name if task.related_organization else "—"
    due_str  = task.due_date.strftime("%A, %d %B %Y") if task.due_date else "No deadline set"

    return (
        f"NEW TASK ASSIGNED — ClientPulse CRM\n"
        f"{'=' * 50}\n\n"
        f"Task:         {task.title}\n"
        f"Priority:     {(task.priority or 'medium').upper()}\n"
        f"Status:       {task.status}\n"
        f"Assigned To:  {assigned_name}\n"
        f"Organisation: {org_name}\n"
        f"Due Date:     {due_str}\n\n"
        f"Description:\n{task.description or 'No description provided.'}\n\n"
        f"Log in to ClientPulse to view and manage this task.\n"
    )


def send_task_created_email(task: Task) -> bool:
    """
    Send a beautifully formatted HTML email when a Task is created.
    Recipient = task.assigned_to.email  (skipped gracefully if absent).
    Returns True if sent, False otherwise.
    """
    if not task.assigned_to or not task.assigned_to.email:
        return False

    recipient = task.assigned_to.email
    subject   = f"[{(task.priority or 'medium').upper()}] New Task: {task.title}"

    msg = EmailMultiAlternatives(
        subject=subject,
        body=_build_task_plain(task),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@clientpulse.com"),
        to=[recipient],
    )
    msg.attach_alternative(_build_task_html(task), "text/html")

    try:
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        # Log but never crash the request/signal
        import logging
        logging.getLogger(__name__).error("Task email failed for task %s: %s", task.pk, exc)
        return False


# ══════════════════════════════════════════════════════════════════
#  SECTION 2 — CLIENT LIFECYCLE AUTOMATION
#  Prototype mode: INACTIVITY_MINUTES replaces "days" so you can
#  watch the automation fire within minutes during development.
#  Switch PROTOTYPE_MODE = False and it uses real days.
# ══════════════════════════════════════════════════════════════════

PROTOTYPE_MODE = True          # ← set False for production
INACTIVITY_MINUTES = 1       # prototype: 14 minutes  (prod: 14 days)
ARCHIVE_AFTER_MINUTES = 3      # prototype: 3 minutes after follow-up (prod: 3 days)
FOLLOW_UP_COOLDOWN_MINUTES = 2 # don't re-send follow-up if already sent recently


def _proto_delta(minutes: int) -> timedelta:
    """Returns timedelta in minutes (prototype) or days (production)."""
    return timedelta(minutes=minutes) if PROTOTYPE_MODE else timedelta(days=minutes)


def _last_contact_dt(org: ClientOrganization):
    """Latest CommunicationLog timestamp for the org, or None."""
    log = CommunicationLog.objects.filter(organization=org).order_by("-created_at").first()
    return log.created_at if log else None


def _build_followup_html(org: ClientOrganization, inactive_label: str) -> str:
    crm_url   = getattr(settings, "CRM_BASE_URL", "http://localhost:8000")
    reply_url = f"mailto:{org.primary_email}" if org.primary_email else crm_url

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>We miss you!</title>
</head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F3F4F6;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#1E3A5F 0%,#7C3AED 100%);
                     border-radius:12px 12px 0 0;padding:36px 40px;text-align:center;">
            <p style="margin:0 0 6px;color:#C4B5FD;font-size:13px;letter-spacing:2px;text-transform:uppercase;">
              ClientPulse CRM
            </p>
            <h1 style="margin:0;color:#FFFFFF;font-size:26px;font-weight:700;">
              👋 We've Missed You, {org.name}
            </h1>
            <p style="margin:10px 0 0;color:#DDD6FE;font-size:14px;">
              It's been a while — we'd love to reconnect
            </p>
          </td>
        </tr>

        <!-- BODY -->
        <tr>
          <td style="background:#FFFFFF;border-radius:0 0 12px 12px;
                     padding:36px 40px;border:1px solid #E5E7EB;border-top:none;">

            <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 20px;">
              Hi <strong>{org.name}</strong>,
            </p>
            <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 20px;">
              We noticed it's been <strong>{inactive_label}</strong> since we last connected.
              We truly value our relationship and want to make sure you're getting the
              most out of our partnership.
            </p>

            <!-- HIGHLIGHT BOX -->
            <div style="background:#F5F3FF;border-left:4px solid #7C3AED;
                        border-radius:0 8px 8px 0;padding:18px 20px;margin:0 0 28px;">
              <p style="margin:0;color:#5B21B6;font-size:14px;line-height:1.7;">
                <strong>What's new for you:</strong><br>
                ✅ Refreshed training programmes available<br>
                ✅ Dedicated account manager ready to assist<br>
                ✅ Priority onboarding for renewed engagements
              </p>
            </div>

            <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 28px;">
              Simply reply to this email or click the button below — we'll take it from there.
            </p>

            <!-- CTA -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center" style="padding-bottom:28px;">
                  <a href="{reply_url}"
                     style="display:inline-block;background:linear-gradient(135deg,#5B21B6,#7C3AED);
                            color:#FFFFFF;text-decoration:none;font-size:15px;font-weight:700;
                            padding:14px 40px;border-radius:8px;">
                    Let's Reconnect →
                  </a>
                </td>
              </tr>
            </table>

            <hr style="border:none;border-top:1px solid #E5E7EB;margin:0 0 20px;">
            <p style="margin:0;color:#9CA3AF;font-size:12px;text-align:center;line-height:1.6;">
              If you believe you received this in error, please disregard.<br>
              © {timezone.now().year} ClientPulse
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
""".strip()


def _send_followup_email(org: ClientOrganization, inactive_label: str) -> bool:
    """Send the re-engagement follow-up to the organisation's primary contact."""
    recipient = org.primary_email
    if not recipient:
        # try first primary contact
        contact = org.contacts.filter(primary_contact=True).first() or org.contacts.first()
        if contact:
            recipient = contact.email
    if not recipient:
        return False

    subject = f"Checking in — we'd love to reconnect, {org.name}"
    plain = (
        f"Hi {org.name},\n\n"
        f"It's been {inactive_label} since we last connected. "
        f"We'd love to catch up and explore how we can continue supporting you.\n\n"
        f"Please reply to this email or contact your account manager.\n\n"
        f"Warm regards,\nClientPulse Team"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@clientpulse.com"),
        to=[recipient],
    )
    msg.attach_alternative(_build_followup_html(org, inactive_label), "text/html")

    try:
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Follow-up email failed for org %s: %s", org.pk, exc)
        return False


def _archive_org(org: ClientOrganization):
    """Mark the org as churned / archived and log it."""
    org.relationship_status = "churned"
    org.save(update_fields=["relationship_status", "updated_at"])

    CommunicationLog.objects.create(
        organization=org,
        channel="other",
        subject="[SYSTEM] Organisation archived — no response to follow-up",
        interaction_summary=(
            "Automated lifecycle engine archived this organisation after "
            "the inactivity threshold was exceeded and no response was received "
            "to the follow-up email."
        ),
        response_received=False,
        follow_up_required=False,
    )


def run_lifecycle_automation():
    """
    Scans all active / at-risk organisations and applies the lifecycle rules:

    1. If inactive > INACTIVITY_MINUTES and no pending follow-up churn alert:
       → send follow-up email + create ChurnAlert (trigger=lifecycle_followup)

    2. If inactive > INACTIVITY_MINUTES + ARCHIVE_AFTER_MINUTES and
       there IS a pending lifecycle_followup alert (meaning we already emailed):
       → archive the organisation

    Prototype mode uses minutes; flip PROTOTYPE_MODE=False for production days.
    """
    import logging
    log = logging.getLogger(__name__)

    now = timezone.now()
    inactivity_cutoff   = now - _proto_delta(INACTIVITY_MINUTES)
    archive_cutoff      = now - _proto_delta(INACTIVITY_MINUTES + ARCHIVE_AFTER_MINUTES)

    active_orgs = ClientOrganization.objects.filter(
        is_deleted=False,
        relationship_status__in=["active", "at_risk", "prospect"],
    )

    sent_followups  = 0
    archived        = 0

    for org in active_orgs:
        last_contact = _last_contact_dt(org)

        # Determine effective "last seen" — use org creation if no comms at all
        last_seen = last_contact or org.created_at

        pending_followup_alert = ChurnAlert.objects.filter(
            organization=org,
            resolved=False,
            trigger_reason__icontains="lifecycle_followup",
        ).order_by("-created_at").first()

        # ── STAGE 2: Archive if follow-up was sent and still no reply ──────────
        if pending_followup_alert and last_seen <= archive_cutoff:
            # Check if a new communication arrived AFTER the alert (= they replied)
            replied = last_contact and (
                last_contact > pending_followup_alert.created_at
            )
            if not replied:
                _archive_org(org)
                pending_followup_alert.resolved = True
                pending_followup_alert.save(update_fields=["resolved"])
                log.info("LIFECYCLE: Archived org '%s' (no response to follow-up).", org.name)
                archived += 1
                continue  # skip to next org

        # ── STAGE 1: Send follow-up if inactive and not yet followed up ────────
        if last_seen <= inactivity_cutoff and not pending_followup_alert:
            # Cooldown guard — don't re-fire if recently done
            recent_alert = ChurnAlert.objects.filter(
                organization=org,
                trigger_reason__icontains="lifecycle_followup",
                created_at__gte=now - _proto_delta(FOLLOW_UP_COOLDOWN_MINUTES),
            ).exists()
            if recent_alert:
                continue

            unit   = "minute(s)" if PROTOTYPE_MODE else "day(s)"
            period = INACTIVITY_MINUTES
            inactive_label = f"{period} {unit}"

            emailed = _send_followup_email(org, inactive_label)

            ChurnAlert.objects.create(
                organization=org,
                risk_score=0.65,
                trigger_reason=(
                    f"[lifecycle_followup] Organisation inactive for {inactive_label}. "
                    f"Follow-up email {'sent' if emailed else 'FAILED (no email address)'}."
                ),
                recommended_action=(
                    "Monitor for a response. If none received within "
                    f"{ARCHIVE_AFTER_MINUTES} {unit}, the organisation will be "
                    "automatically archived."
                ),
            )

            # Also update org status to at_risk if still active
            if org.relationship_status == "active":
                org.relationship_status = "at_risk"
                org.save(update_fields=["relationship_status", "updated_at"])

            log.info(
                "LIFECYCLE: Follow-up sent to '%s' (inactive %s). Email sent: %s",
                org.name, inactive_label, emailed,
            )
            sent_followups += 1

    return {"followups_sent": sent_followups, "orgs_archived": archived}