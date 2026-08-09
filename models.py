"""CSMC 饰品交易平台 - 数据模型"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """用户表"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    qq = db.Column(db.String(20), unique=True, nullable=False, index=True)
    game_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # 角色：user 普通用户 / admin 管理员
    role = db.Column(db.String(16), nullable=False, default="user")
    # 状态：pending 待审核 / approved 已通过 / rejected 已拒绝 / banned 已封禁
    status = db.Column(db.String(16), nullable=False, default="pending")

    created_at = db.Column(db.DateTime, default=datetime.now)

    trades = db.relationship("Trade", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "qq": self.qq,
            "game_id": self.game_id,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }


class Trade(db.Model):
    """交易表"""
    __tablename__ = "trades"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # 交易目的：逗号分隔多选，如 "出售,交换"
    purpose = db.Column(db.String(64), nullable=False)
    # 饰品名字
    item_name = db.Column(db.String(128), nullable=False)
    # 是否 StatTrak：0 否 / 1 是
    stattrak = db.Column(db.Integer, nullable=False, default=0)
    # 磨损度（浮点，保留6位小数）
    wear = db.Column(db.Float, nullable=False)
    # 市场建议售价（数字）
    market_price = db.Column(db.Float, nullable=False)
    # 玩家游戏 ID（发布时冗余记录，即 user.game_id）
    game_id = db.Column(db.String(64), nullable=False)
    # QQ号（发布时冗余记录，即 user.qq）
    qq = db.Column(db.String(20), nullable=False)
    # 接受的货币：逗号分隔多选，如 "点券,金币"
    accepted_currency = db.Column(db.String(64), nullable=False)
    # 心理预期价格（文本，可填范围）
    expected_price = db.Column(db.String(128), nullable=False)
    # 补充描述（选填）
    description = db.Column(db.Text, nullable=True)
    # 状态：listing 上架中 / done 已完成 / removed 已下架
    status = db.Column(db.String(16), nullable=False, default="listing", index=True)

    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    # 成交时记录（选填）
    buyer_game_id = db.Column(db.String(64), nullable=True)
    deal_price = db.Column(db.String(128), nullable=True)

    def purpose_list(self):
        return [p for p in (self.purpose or "").split(",") if p]

    def currency_list(self):
        return [c for c in (self.accepted_currency or "").split(",") if c]

    def wear_str(self):
        """磨损格式化为6位小数"""
        return f"{self.wear:.6f}"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "purpose": self.purpose_list(),
            "item_name": self.item_name,
            "stattrak": bool(self.stattrak),
            "wear": self.wear_str(),
            "market_price": self.market_price,
            "game_id": self.game_id,
            "qq": self.qq,
            "accepted_currency": self.currency_list(),
            "expected_price": self.expected_price,
            "description": self.description or "",
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M") if self.completed_at else "",
            "buyer_game_id": self.buyer_game_id or "",
            "deal_price": self.deal_price or "",
        }
