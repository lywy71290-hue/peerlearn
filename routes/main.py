from flask import Blueprint, render_template, request, jsonify
from models.video import Video
from models.user import User

main_bp = Blueprint("main", __name__)

TERMS = ["Term 1", "Term 2", "Term 3", "Term 4"]
LEVELS = ["Beginner", "Elementary", "Pre-Intermediate", "Intermediate", "Upper-Intermediate", "Advanced"]
UNITS = [f"Unit {i}" for i in range(1, 13)]


@main_bp.route("/")
def index():
    latest = Video.query.order_by(Video.created_at.desc()).limit(8).all()
    return render_template("main/index.html", latest=latest, terms=TERMS, levels=LEVELS, units=UNITS)


@main_bp.route("/browse")
def browse():
    term = request.args.get("term", "")
    level = request.args.get("level", "")
    unit = request.args.get("unit", "")
    sort = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)

    query = Video.query
    if term:
        query = query.filter_by(term=term)
    if level:
        query = query.filter_by(level=level)
    if unit:
        query = query.filter_by(unit=unit)

    if sort == "top_rated":
        videos_all = query.all()
        videos_all.sort(key=lambda v: v.avg_rating, reverse=True)
        total = len(videos_all)
        per_page = 9
        start = (page - 1) * per_page
        videos_page = videos_all[start: start + per_page]

        class FakePagination:
            def __init__(self, items, total, page, per_page):
                self.items = items
                self.total = total
                self.page = page
                self.per_page = per_page
                self.pages = max(1, (total + per_page - 1) // per_page)
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1
                self.next_num = page + 1

        pagination = FakePagination(videos_page, total, page, per_page)
    else:
        query = query.order_by(Video.created_at.desc())
        pagination = query.paginate(page=page, per_page=9, error_out=False)

    return render_template(
        "main/browse.html",
        pagination=pagination,
        terms=TERMS,
        levels=LEVELS,
        units=UNITS,
        current_term=term,
        current_level=level,
        current_unit=unit,
        current_sort=sort,
    )


@main_bp.route("/api/stats")
def api_stats():
    return jsonify({
        "videos": Video.query.count(),
        "users": User.query.count(),
    })
