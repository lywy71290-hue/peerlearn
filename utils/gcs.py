"""
Cloudinary Storage Helper
=========================
مجاني 100% — لا يحتاج بطاقة ائتمان.
الخطة المجانية: 25 GB تخزين + CDN عالمي.

متغيرات البيئة المطلوبة:
  CLOUDINARY_CLOUD_NAME  → اسم الـ Cloud (من Dashboard)
  CLOUDINARY_API_KEY     → API Key
  CLOUDINARY_API_SECRET  → API Secret
"""

import os
import uuid
import cloudinary
import cloudinary.uploader
from flask import current_app


def _configure():
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )


def upload_video_to_gcs(file_stream, original_filename: str) -> str:
    """
    يرفع الفيديو إلى Cloudinary ويُعيد الرابط العام.
    الاسم القديم (gcs) محفوظ لعدم كسر باقي الكود.
    """
    _configure()
    public_id = f"peerlearn/videos/{uuid.uuid4().hex}"

    result = cloudinary.uploader.upload_large(
        file_stream,
        resource_type="video",
        public_id=public_id,
        overwrite=False,
        chunk_size=6 * 1024 * 1024,   # 6 MB chunks
    )
    return result["secure_url"]


def delete_blob_from_gcs(public_url: str) -> bool:
    """يحذف الفيديو من Cloudinary بناءً على رابطه."""
    try:
        _configure()
        # استخراج public_id من الرابط
        # مثال: https://res.cloudinary.com/demo/video/upload/v123/peerlearn/videos/abc.mp4
        parts = public_url.split("/upload/")
        if len(parts) < 2:
            return False
        # إزالة رقم الإصدار (v123/) إذا وُجد
        path = parts[1]
        if path.startswith("v") and "/" in path:
            path = path.split("/", 1)[1]
        # إزالة الامتداد
        public_id = os.path.splitext(path)[0]
        cloudinary.uploader.destroy(public_id, resource_type="video")
        return True
    except Exception as e:
        current_app.logger.warning(f"Cloudinary delete failed: {e}")
        return False
