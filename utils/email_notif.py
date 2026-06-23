"""
Email notification utility for NITI Learn.
Uses Python's smtplib with Gmail SMTP (or any SMTP server).

Required environment variables:
  MAIL_SERVER   — e.g. smtp.gmail.com
  MAIL_PORT     — e.g. 587
  MAIL_USERNAME — sender email address
  MAIL_PASSWORD — app password (not the account password)
  ADMIN_EMAIL   — recipient email for new video notifications
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _get_smtp_config():
    return {
        "server":   os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
        "port":     int(os.environ.get("MAIL_PORT", 587)),
        "username": os.environ.get("MAIL_USERNAME", ""),
        "password": os.environ.get("MAIL_PASSWORD", ""),
    }


def send_email(to: str, subject: str, html_body: str):
    """Send a single HTML email. Returns True on success, False on failure."""
    cfg = _get_smtp_config()
    if not cfg["username"] or not cfg["password"]:
        logger.warning("Email not configured — skipping send.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"NITI Learn <{cfg['username']}>"
        msg["To"]      = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(cfg["server"], cfg["port"], timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(cfg["username"], cfg["password"])
            smtp.sendmail(cfg["username"], to, msg.as_string())
        logger.info(f"Email sent to {to}: {subject}")
        return True
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
