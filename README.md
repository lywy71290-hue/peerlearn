# PeerLearn — Peer-to-Peer Learning Platform

منصة تعليمية تفاعلية تعتمد على نظام Peer-to-Peer Learning.

**Stack:** Flask · PostgreSQL · Cloudinary · Render

---

## إعداد Cloudinary (مجاني 100% — بدون بطاقة ائتمان)

### 1 — إنشاء حساب
- اذهب إلى [cloudinary.com](https://cloudinary.com/users/register_free)
- اضغط **Sign Up Free** وسجّل بالإيميل
- لا يحتاج بطاقة ائتمان — الخطة المجانية تشمل 25 GB تخزين

### 2 — الحصول على بيانات الاتصال
بعد تسجيل الدخول ستظهر لك صفحة **Dashboard** مباشرة.
في أعلى الصفحة ستجد مربع **API Environment variable** يحتوي على:

| المتغير | مكانه في Dashboard |
|---|---|
| `CLOUDINARY_CLOUD_NAME` | حقل **Cloud name** |
| `CLOUDINARY_API_KEY` | حقل **API key** |
| `CLOUDINARY_API_SECRET` | حقل **API secret** (اضغط على العين لإظهاره) |

---

## النشر على Render

### 1 — ارفع الكود على GitHub
```bash
git init
git add .
git commit -m "Initial PeerLearn commit"
git remote add origin https://github.com/USERNAME/peerlearn.git
git push -u origin main
```

### 2 — أنشئ قاعدة البيانات
- في [render.com](https://render.com) اضغط **New → PostgreSQL**
- اسمها: `peerlearn-db` ثم **Create Database**
- انسخ **Internal Database URL**

### 3 — أنشئ Web Service
- اضغط **New → Web Service** وربطه بالـ GitHub repo
- اضبط:

| الحقل | القيمة |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `./start.sh` |

### 4 — أضف متغيرات البيئة

| المتغير | القيمة |
|---|---|
| `DATABASE_URL` | Internal URL من Render PostgreSQL |
| `SECRET_KEY` | أي نص عشوائي طويل |
| `CLOUDINARY_CLOUD_NAME` | من Cloudinary Dashboard |
| `CLOUDINARY_API_KEY` | من Cloudinary Dashboard |
| `CLOUDINARY_API_SECRET` | من Cloudinary Dashboard |

### 5 — تهيئة قاعدة البيانات
في Render Shell بعد أول نشر:
```bash
flask db init
flask db migrate -m "Initial"
flask db upgrade
```

---

## التشغيل المحلي

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cat > .env << EOF
SECRET_KEY=dev-secret-key
DATABASE_URL=postgresql://localhost/peerlearning
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
EOF

flask db upgrade
flask run
```
