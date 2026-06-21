#!/usr/bin/env bash
# PeerLearn — Render start script
# متغيرات Cloudinary تُضاف مباشرة في Render Dashboard — لا حاجة لأي ملف إضافي
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
