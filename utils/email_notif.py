"""
Email notification utility for NITI Learn.
Uses Brevo (formerly Sendinblue) Transactional Email API.

Required environment variables:
  BREVO_API_KEY   — Brevo API key (starts with xkeysib-)
  BREVO_SENDER_EMAIL — sender email address (verified in Brevo)
  BREVO_SENDER_NAME  — sender display name (default: NITI Learn)
  ADMIN_EMAIL     — recipient email for new video notifications
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to: str, subject: str, html_body: str):
    """Send a single HTML email via Brevo API. Returns True on success, False on failure."""
    api_key = os.environ.get("BREVO_API_KEY", "")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "NITI Learn")

    if not api_key or not sender_email:
        logger.warning("Brevo email not configured — skipping send.")
        return False

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html_body
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=15)
        if response.status_code in (200, 201):
            logger.info(f"Email sent via Brevo to {to}: {subject}")
            return True
        else:
            logger.error(f"Brevo API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


def notify_admin_new_video(video_title: str, uploader_name: str,
                           uploader_email: str, video_id: int,
                           term: str, level: str, unit: str):
    """Send an email to all admins when a new video is uploaded for review."""
    admin_email = os.environ.get("ADMIN_EMAIL", "")
    if not admin_email:
        logger.warning("ADMIN_EMAIL not set — skipping admin email notification.")
        return

    review_url = f"{os.environ.get('APP_URL', 'https://peerlearn-n3qi.onrender.com')}/admin/pending"

    subject = f"[NITI Learn] فيديو جديد ينتظر مراجعتك: {video_title}"
    html = f"""
    <div dir="rtl" style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto; background:#f4f6fb; padding:24px; border-radius:12px;">
      <div style="background:#0a1628; padding:20px 24px; border-radius:10px 10px 0 0; text-align:center;">
        <h2 style="color:#c9a84c; margin:0; font-size:1.4rem;">NITI Learn</h2>
        <p style="color:rgba(255,255,255,.6); margin:4px 0 0; font-size:.85rem;">نظام إشعارات المراجعة</p>
      </div>
      <div style="background:#fff; padding:28px 24px; border-radius:0 0 10px 10px; border:1px solid #e5e7eb; border-top:none;">
        <h3 style="color:#0a1628; margin-top:0;">📹 فيديو جديد ينتظر مراجعتك</h3>
        <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
          <tr><td style="padding:8px 0; color:#6b7280; width:120px;">العنوان:</td>
              <td style="padding:8px 0; font-weight:700; color:#0a1628;">{video_title}</td></tr>
          <tr><td style="padding:8px 0; color:#6b7280;">الرافع:</td>
              <td style="padding:8px 0;">{uploader_name} &lt;{uploader_email}&gt;</td></tr>
          <tr><td style="padding:8px 0; color:#6b7280;">الترم:</td>
              <td style="padding:8px 0;">{term}</td></tr>
          <tr><td style="padding:8px 0; color:#6b7280;">المستوى:</td>
              <td style="padding:8px 0;">{level}</td></tr>
          <tr><td style="padding:8px 0; color:#6b7280;">الوحدة:</td>
              <td style="padding:8px 0;">{unit}</td></tr>
        </table>
        <div style="text-align:center; margin-top:24px;">
          <a href="{review_url}"
             style="background:#c9a84c; color:#0a1628; text-decoration:none; padding:12px 32px;
                    border-radius:8px; font-weight:700; font-size:1rem; display:inline-block;">
            مراجعة الفيديو الآن
          </a>
        </div>
        <p style="color:#9ca3af; font-size:.78rem; text-align:center; margin-top:24px; margin-bottom:0;">
          هذا إشعار تلقائي من منصة NITI Learn. لا ترد على هذا البريد.
        </p>
      </div>
    </div>
    """
    send_email(admin_email, subject, html)


def notify_uploader_approved(uploader_email: str, uploader_name: str,
                              video_title: str, video_id: int):
    """Notify the uploader that their video was approved."""
    video_url = f"{os.environ.get('APP_URL', 'https://peerlearn-n3qi.onrender.com')}/videos/{video_id}"
    subject = f"[NITI Learn] ✅ تمت الموافقة على فيديوك: {video_title}"
    html = f"""
    <div dir="rtl" style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto; background:#f4f6fb; padding:24px; border-radius:12px;">
      <div style="background:#0a1628; padding:20px 24px; border-radius:10px 10px 0 0; text-align:center;">
        <h2 style="color:#c9a84c; margin:0; font-size:1.4rem;">NITI Learn</h2>
      </div>
      <div style="background:#fff; padding:28px 24px; border-radius:0 0 10px 10px; border:1px solid #e5e7eb; border-top:none;">
        <h3 style="color:#16a34a; margin-top:0;">✅ تمت الموافقة على فيديوك!</h3>
        <p style="color:#374151;">مرحباً <strong>{uploader_name}</strong>،</p>
        <p style="color:#374151;">تمت مراجعة فيديوك <strong>«{video_title}»</strong> والموافقة عليه. يمكن لجميع المتدربين الآن مشاهدته.</p>
        <div style="text-align:center; margin-top:24px;">
          <a href="{video_url}"
             style="background:#c9a84c; color:#0a1628; text-decoration:none; padding:12px 32px;
                    border-radius:8px; font-weight:700; font-size:1rem; display:inline-block;">
            مشاهدة الفيديو
          </a>
        </div>
      </div>
    </div>
    """
    send_email(uploader_email, subject, html)


def notify_uploader_rejected(uploader_email: str, uploader_name: str,
                              video_title: str, reason: str = ""):
    """Notify the uploader that their video was rejected."""
    subject = f"[NITI Learn] ❌ تم رفض فيديوك: {video_title}"
    reason_html = f"<p style='color:#374151;'><strong>السبب:</strong> {reason}</p>" if reason else ""
    html = f"""
    <div dir="rtl" style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto; background:#f4f6fb; padding:24px; border-radius:12px;">
      <div style="background:#0a1628; padding:20px 24px; border-radius:10px 10px 0 0; text-align:center;">
        <h2 style="color:#c9a84c; margin:0; font-size:1.4rem;">NITI Learn</h2>
      </div>
      <div style="background:#fff; padding:28px 24px; border-radius:0 0 10px 10px; border:1px solid #e5e7eb; border-top:none;">
        <h3 style="color:#dc2626; margin-top:0;">❌ تم رفض فيديوك</h3>
        <p style="color:#374151;">مرحباً <strong>{uploader_name}</strong>،</p>
        <p style="color:#374151;">للأسف، تم رفض فيديوك <strong>«{video_title}»</strong> من قِبل المشرف.</p>
        {reason_html}
        <p style="color:#374151;">يمكنك رفع فيديو جديد بعد مراجعة الملاحظات.</p>
      </div>
    </div>
    """
    send_email(uploader_email, subject, html)


def send_otp_email(to_email: str, trainee_name: str, otp_code: str):
    """Send OTP login code to trainee email."""
    subject = "[NITI Learn] Your Login Code"
    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif; max-width:520px; margin:0 auto; background:#f4f6fb; padding:24px; border-radius:12px;">
      <div style="background:#0a1628; padding:20px 24px; border-radius:10px 10px 0 0; text-align:center;">
        <h2 style="color:#c9a84c; margin:0; font-size:1.5rem; letter-spacing:1px;">NITI Learn</h2>
        <p style="color:rgba(255,255,255,.6); margin:4px 0 0; font-size:.85rem;">National Industrial Training Institute</p>
      </div>
      <div style="background:#fff; padding:32px 24px; border-radius:0 0 10px 10px; border:1px solid #e5e7eb; border-top:none; text-align:center;">
        <p style="color:#374151; font-size:1rem; margin-top:0;">Hello <strong>{trainee_name}</strong>,</p>
        <p style="color:#374151; font-size:.95rem;">Your one-time login code for NITI Learn is:</p>
        <div style="background:#f4f6fb; border:2px dashed #c9a84c; border-radius:12px; padding:20px 0; margin:24px 0;">
          <span style="font-size:2.8rem; font-weight:900; letter-spacing:12px; color:#0a1628; font-family:monospace;">{otp_code}</span>
        </div>
        <p style="color:#6b7280; font-size:.88rem;">This code is valid for <strong>10 minutes</strong>. Do not share it with anyone.</p>
        <hr style="border:none; border-top:1px solid #e5e7eb; margin:24px 0;">
        <p style="color:#9ca3af; font-size:.78rem; margin:0;">
          If you did not request this code, please ignore this email.<br>
          This is an automated message from NITI Learn — do not reply.
        </p>
      </div>
    </div>
    """
    return send_email(to_email, subject, html)
