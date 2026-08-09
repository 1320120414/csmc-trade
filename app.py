"""CSMC 饰品交易平台 - 主应用"""
import os
from functools import wraps
from flask import (
    Flask, render_template, redirect, url_for, request, flash,
    session, jsonify, abort
)
from werkzeug.security import generate_password_hash

from config import Config
from models import db, User, Trade

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


# ==================== 初始化 ====================
def init_db():
    """创建数据库表 + 初始管理员账号"""
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role="admin").first():
            admin = User(
                qq=Config.ADMIN_QQ,
                game_id=Config.ADMIN_GAME_ID,
                role="admin",
                status="approved",
            )
            admin.set_password(Config.ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f"[初始化] 已创建管理员账号：QQ={Config.ADMIN_QQ} 游戏ID={Config.ADMIN_GAME_ID} 密码={Config.ADMIN_PASSWORD}（请立即修改）")


# ==================== 装饰器 ====================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("请先登录", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("请先登录", "warning")
            return redirect(url_for("login", next=request.url))
        user = User.query.get(session["user_id"])
        if not user or user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def approved_required(f):
    """需要已通过审核"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("请先登录", "warning")
            return redirect(url_for("login", next=request.url))
        user = User.query.get(session["user_id"])
        if not user:
            session.clear()
            return redirect(url_for("login"))
        if user.status == "banned":
            flash("账号已被封禁，请联系管理员", "danger")
            session.clear()
            return redirect(url_for("login"))
        if user.status == "pending":
            flash("账号待审核，请耐心等待管理员通过", "warning")
            return redirect(url_for("pending"))
        if user.status == "rejected":
            flash("注册申请已被拒绝，请联系管理员", "danger")
            session.clear()
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None


# ==================== 上下文处理器：注入全局变量 ====================
@app.context_processor
def inject_globals():
    return {
        "PLATFORM_NAME": Config.PLATFORM_NAME,
        "PURPOSE_OPTIONS": Config.PURPOSE_OPTIONS,
        "CURRENCY_OPTIONS": Config.CURRENCY_OPTIONS,
        "current_user": current_user(),
    }


# ==================== 路由：首页（交易列表 + 筛选） ====================
@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = Config.TRADES_PER_PAGE

    q = Trade.query.filter_by(status="listing")

    # 筛选：交易目的
    purpose = request.args.getlist("purpose")
    if purpose:
        # 任一目的匹配
        conds = []
        for p in purpose:
            conds.append(Trade.purpose.contains(p))
        from sqlalchemy import or_
        q = q.filter(or_(*conds))

    # 筛选：饰品名搜索
    keyword = request.args.get("q", "").strip()
    if keyword:
        q = q.filter(Trade.item_name.contains(keyword))

    # 筛选：StatTrak
    st = request.args.get("stattrak", "")
    if st in ("0", "1"):
        q = q.filter(Trade.stattrak == int(st))

    # 筛选：接受的货币
    currency = request.args.getlist("currency")
    if currency:
        from sqlalchemy import or_
        conds = [Trade.accepted_currency.contains(c) for c in currency]
        q = q.filter(or_(*conds))

    # 筛选：磨损范围
    wear_min = request.args.get("wear_min", type=float)
    wear_max = request.args.get("wear_max", type=float)
    if wear_min is not None:
        q = q.filter(Trade.wear >= wear_min)
    if wear_max is not None:
        q = q.filter(Trade.wear <= wear_max)

    # 排序
    sort = request.args.get("sort", "newest")
    if sort == "price_asc":
        q = q.order_by(Trade.market_price.asc())
    elif sort == "price_desc":
        q = q.order_by(Trade.market_price.desc())
    elif sort == "wear_asc":
        q = q.order_by(Trade.wear.asc())
    elif sort == "wear_desc":
        q = q.order_by(Trade.wear.desc())
    else:
        q = q.order_by(Trade.created_at.desc())

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    trades = pagination.items

    return render_template(
        "index.html",
        trades=trades,
        pagination=pagination,
        filters={
            "purpose": purpose,
            "q": keyword,
            "stattrak": st,
            "currency": currency,
            "wear_min": request.args.get("wear_min", ""),
            "wear_max": request.args.get("wear_max", ""),
            "sort": sort,
        },
    )


# ==================== 路由：注册 ====================
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        qq = request.form.get("qq", "").strip()
        game_id = request.form.get("game_id", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not qq or not game_id or not password:
            flash("QQ号、游戏ID、密码均为必填", "danger")
            return render_template("register.html")
        if not qq.isdigit():
            flash("QQ号必须为纯数字", "danger")
            return render_template("register.html")
        if password != password2:
            flash("两次密码不一致", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("密码长度至少6位", "danger")
            return render_template("register.html")
        if User.query.filter((User.qq == qq) | (User.game_id == game_id)).first():
            flash("QQ号或游戏ID已被注册", "danger")
            return render_template("register.html")

        status = "pending" if Config.REQUIRE_APPROVAL else "approved"
        user = User(qq=qq, game_id=game_id, status=status)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        if status == "pending":
            flash("注册成功！请等待管理员审核通过后登录。", "success")
            return redirect(url_for("pending"))
        else:
            flash("注册成功！请登录。", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


# ==================== 路由：待审核提示页 ====================
@app.route("/pending")
def pending():
    return render_template("pending.html")


# ==================== 路由：登录 ====================
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        account = request.form.get("account", "").strip()
        password = request.form.get("password", "")

        # QQ号或游戏ID 均可登录
        user = User.query.filter((User.qq == account) | (User.game_id == account)).first()
        if not user or not user.check_password(password):
            flash("账号或密码错误", "danger")
            return render_template("login.html")

        session["user_id"] = user.id

        if user.status == "banned":
            flash("账号已被封禁，请联系管理员", "danger")
            session.clear()
            return render_template("login.html")
        if user.status == "pending":
            return redirect(url_for("pending"))
        if user.status == "rejected":
            flash("注册申请已被拒绝，请联系管理员", "danger")
            session.clear()
            return render_template("login.html")

        next_url = request.args.get("next") or url_for("index")
        flash("登录成功", "success")
        return redirect(next_url)

    return render_template("login.html")


# ==================== 路由：登出 ====================
@app.route("/logout")
def logout():
    session.clear()
    flash("已退出登录", "info")
    return redirect(url_for("index"))


# ==================== 路由：发布交易 ====================
@app.route("/publish", methods=["GET", "POST"])
@approved_required
def publish():
    if request.method == "POST":
        user = current_user()
        purpose_list = request.form.getlist("purpose")
        item_name = request.form.get("item_name", "").strip()
        stattrak = request.form.get("stattrak", "0")
        wear = request.form.get("wear", "").strip()
        market_price = request.form.get("market_price", "").strip()
        currency_list = request.form.getlist("currency")
        expected_price = request.form.get("expected_price", "").strip()
        description = request.form.get("description", "").strip()

        # 校验
        if not purpose_list:
            flash("请选择交易目的", "danger")
            return render_template("publish.html")
        if not item_name:
            flash("请填写饰品名字", "danger")
            return render_template("publish.html")
        try:
            wear_val = float(wear)
            if wear_val < 0 or wear_val > 1:
                raise ValueError
        except (ValueError, TypeError):
            flash("磨损度需为 0~1 之间的数字（精确到小数点后6位）", "danger")
            return render_template("publish.html")
        try:
            price_val = float(market_price)
            if price_val < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("市场建议售价需为数字", "danger")
            return render_template("publish.html")
        if not currency_list:
            flash("请选择接受的货币", "danger")
            return render_template("publish.html")
        if not expected_price:
            flash("请填写心理预期价格", "danger")
            return render_template("publish.html")

        trade = Trade(
            user_id=user.id,
            purpose=",".join(purpose_list),
            item_name=item_name,
            stattrak=1 if stattrak == "1" else 0,
            wear=wear_val,
            market_price=price_val,
            game_id=user.game_id,
            qq=user.qq,
            accepted_currency=",".join(currency_list),
            expected_price=expected_price,
            description=description or None,
            status="listing",
        )
        db.session.add(trade)
        db.session.commit()
        flash("交易发布成功！", "success")
        return redirect(url_for("detail", trade_id=trade.id))

    return render_template("publish.html")


# ==================== 路由：交易详情 ====================
@app.route("/trade/<int:trade_id>")
def detail(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    return render_template("detail.html", trade=trade)


# ==================== 路由：编辑交易 ====================
@app.route("/trade/<int:trade_id>/edit", methods=["GET", "POST"])
@approved_required
def edit_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    user = current_user()
    if trade.user_id != user.id:
        abort(403)
    if trade.status != "listing":
        flash("只有上架中的交易才能编辑", "warning")
        return redirect(url_for("detail", trade_id=trade.id))

    if request.method == "POST":
        purpose_list = request.form.getlist("purpose")
        item_name = request.form.get("item_name", "").strip()
        stattrak = request.form.get("stattrak", "0")
        wear = request.form.get("wear", "").strip()
        market_price = request.form.get("market_price", "").strip()
        currency_list = request.form.getlist("currency")
        expected_price = request.form.get("expected_price", "").strip()
        description = request.form.get("description", "").strip()

        if not purpose_list or not item_name or not currency_list or not expected_price:
            flash("请填写所有必填项", "danger")
            return render_template("publish.html", edit_mode=True, trade=trade)
        try:
            wear_val = float(wear)
            if not (0 <= wear_val <= 1):
                raise ValueError
        except (ValueError, TypeError):
            flash("磨损度需为 0~1 之间的数字", "danger")
            return render_template("publish.html", edit_mode=True, trade=trade)
        try:
            price_val = float(market_price)
            if price_val < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("市场建议售价需为数字", "danger")
            return render_template("publish.html", edit_mode=True, trade=trade)

        trade.purpose = ",".join(purpose_list)
        trade.item_name = item_name
        trade.stattrak = 1 if stattrak == "1" else 0
        trade.wear = wear_val
        trade.market_price = price_val
        trade.accepted_currency = ",".join(currency_list)
        trade.expected_price = expected_price
        trade.description = description or None
        db.session.commit()
        flash("交易已更新", "success")
        return redirect(url_for("detail", trade_id=trade.id))

    return render_template("publish.html", edit_mode=True, trade=trade)


# ==================== 路由：标记交易完成 ====================
@app.route("/trade/<int:trade_id>/complete", methods=["POST"])
@approved_required
def complete_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    user = current_user()
    if trade.user_id != user.id:
        abort(403)
    if trade.status != "listing":
        flash("该交易不在上架状态", "warning")
        return redirect(url_for("detail", trade_id=trade.id))

    buyer_game_id = request.form.get("buyer_game_id", "").strip()
    deal_price = request.form.get("deal_price", "").strip()

    from datetime import datetime
    trade.status = "done"
    trade.completed_at = datetime.now()
    trade.buyer_game_id = buyer_game_id or None
    trade.deal_price = deal_price or None
    db.session.commit()
    flash("已标记为完成", "success")
    return redirect(url_for("detail", trade_id=trade.id))


# ==================== 路由：下架交易 ====================
@app.route("/trade/<int:trade_id>/remove", methods=["POST"])
@approved_required
def remove_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    user = current_user()
    if trade.user_id != user.id and user.role != "admin":
        abort(403)
    trade.status = "removed"
    db.session.commit()
    flash("交易已下架", "info")
    return redirect(url_for("profile"))


# ==================== 路由：删除交易 ====================
@app.route("/trade/<int:trade_id>/delete", methods=["POST"])
@approved_required
def delete_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    user = current_user()
    if trade.user_id != user.id:
        abort(403)
    db.session.delete(trade)
    db.session.commit()
    flash("交易已删除", "info")
    return redirect(url_for("profile"))


# ==================== 路由：个人页面 ====================
@app.route("/profile")
@approved_required
def profile():
    user = current_user()
    my_listings = Trade.query.filter_by(user_id=user.id, status="listing").order_by(Trade.created_at.desc()).all()
    my_done = Trade.query.filter_by(user_id=user.id, status="done").order_by(Trade.completed_at.desc()).all()
    my_removed = Trade.query.filter_by(user_id=user.id, status="removed").order_by(Trade.created_at.desc()).all()
    return render_template("profile.html", user=user, my_listings=my_listings, my_done=my_done, my_removed=my_removed)


# ==================== 路由：修改自己的密码 ====================
@app.route("/profile/password", methods=["POST"])
@approved_required
def change_password():
    user = current_user()
    old = request.form.get("old_password", "")
    new = request.form.get("new_password", "")
    new2 = request.form.get("new_password2", "")
    if not user.check_password(old):
        flash("原密码错误", "danger")
        return redirect(url_for("profile"))
    if len(new) < 6:
        flash("新密码至少6位", "danger")
        return redirect(url_for("profile"))
    if new != new2:
        flash("两次新密码不一致", "danger")
        return redirect(url_for("profile"))
    user.set_password(new)
    db.session.commit()
    flash("密码修改成功", "success")
    return redirect(url_for("profile"))


# ==================== 路由：管理员页面 ====================
@app.route("/admin")
@admin_required
def admin():
    tab = request.args.get("tab", "pending")
    if tab == "pending":
        users = User.query.filter_by(status="pending").order_by(User.created_at.desc()).all()
    elif tab == "all":
        users = User.query.order_by(User.created_at.desc()).all()
    else:
        users = []
    trades = Trade.query.order_by(Trade.created_at.desc()).limit(50).all()
    return render_template("admin.html", tab=tab, users=users, trades=trades)


@app.route("/admin/user/<int:user_id>/approve", methods=["POST"])
@admin_required
def admin_approve(user_id):
    u = User.query.get_or_404(user_id)
    u.status = "approved"
    db.session.commit()
    flash(f"已通过用户 {u.game_id} 的注册", "success")
    return redirect(url_for("admin", tab="pending"))


@app.route("/admin/user/<int:user_id>/reject", methods=["POST"])
@admin_required
def admin_reject(user_id):
    u = User.query.get_or_404(user_id)
    u.status = "rejected"
    db.session.commit()
    flash(f"已拒绝用户 {u.game_id} 的注册", "warning")
    return redirect(url_for("admin", tab="pending"))


@app.route("/admin/user/<int:user_id>/ban", methods=["POST"])
@admin_required
def admin_ban(user_id):
    u = User.query.get_or_404(user_id)
    if u.role == "admin":
        flash("不能封禁管理员", "danger")
        return redirect(url_for("admin", tab="all"))
    u.status = "banned"
    db.session.commit()
    flash(f"已封禁用户 {u.game_id}", "warning")
    return redirect(url_for("admin", tab="all"))


@app.route("/admin/user/<int:user_id>/unban", methods=["POST"])
@admin_required
def admin_unban(user_id):
    u = User.query.get_or_404(user_id)
    u.status = "approved"
    db.session.commit()
    flash(f"已解封用户 {u.game_id}", "success")
    return redirect(url_for("admin", tab="all"))


@app.route("/admin/user/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(user_id):
    u = User.query.get_or_404(user_id)
    new_pwd = request.form.get("new_password", "").strip()
    if not new_pwd:
        flash("请输入新密码", "danger")
        return redirect(url_for("admin", tab="all"))
    u.set_password(new_pwd)
    db.session.commit()
    flash(f"已重置用户 {u.game_id} 的密码", "success")
    return redirect(url_for("admin", tab="all"))


@app.route("/admin/user/<int:user_id>/set-admin", methods=["POST"])
@admin_required
def admin_set_admin(user_id):
    u = User.query.get_or_404(user_id)
    u.role = "admin" if u.role != "admin" else "user"
    db.session.commit()
    flash(f"已{'设为管理员' if u.role == 'admin' else '取消管理员'}：{u.game_id}", "success")
    return redirect(url_for("admin", tab="all"))


@app.route("/admin/trade/<int:trade_id>/remove", methods=["POST"])
@admin_required
def admin_remove_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    trade.status = "removed"
    db.session.commit()
    flash("已下架该交易", "info")
    return redirect(url_for("admin", tab="all"))


# ==================== 错误页 ====================
@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="无权访问"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="页面不存在"), 404


# ==================== 启动 ====================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    # gunicorn 入口
    init_db()
