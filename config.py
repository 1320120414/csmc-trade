"""CSMC 饰品交易平台 - 配置文件"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 密钥（生产环境请修改为随机长字符串）
    SECRET_KEY = os.environ.get("CSMC_SECRET_KEY", "csmc-change-this-secret-key-in-production")

    # 数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "CSMC_DB_URI", "sqlite:///" + os.path.join(BASE_DIR, "csmc.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ===== 业务配置 =====
    # 注册是否需要审核：True=需要管理员审核，False=注册即通过
    REQUIRE_APPROVAL = True

    # 平台名称（显示在导航栏）
    PLATFORM_NAME = "CSMC 饰品交易平台"

    # 每页交易数量
    TRADES_PER_PAGE = 24

    # 交易目的选项
    PURPOSE_OPTIONS = ["求购", "出租", "出售", "交换"]

    # 接受的货币选项
    CURRENCY_OPTIONS = ["点券", "金币"]

    # 管理员初始账号（首次初始化时创建，请上线后立即修改密码）
    ADMIN_QQ = "10000"
    ADMIN_GAME_ID = "admin"
    ADMIN_PASSWORD = "admin123456"
