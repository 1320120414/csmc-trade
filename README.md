# CSMC 饰品交易平台

CSMC（MC版CS服务器）饰品交易**纯撮合看板**。平台仅发布/展示交易信息，买卖双方通过 QQ 私聊自行完成点券/金币/饰品的交割，平台不碰钱、不碰货、不做担保。

## 功能一览

| 模块 | 说明 |
|:---|:---|
| 注册登录 | 填写 QQ号、游戏ID、密码；QQ号或游戏ID 均可登录 |
| 注册审核 | 管理员手动审核（可在 `config.py` 中关闭） |
| 主页 | 交易卡片网格，支持筛选：交易目的、饰品名搜索、StatTrak、货币、价格排序、磨损范围 |
| 交易卡片 | 游戏ID（主）+ QQ号（小字）、交易目的、饰品名、StatTrak、磨损、售价、货币、心理预期价格 |
| 发布交易 | 9 项必填 + 1 项选填描述，对应原 QQ 群填表全部字段 |
| 交易详情 | 完整信息展示 + 复制QQ号 + 发起QQ会话 + 发布者管理操作 |
| 交易状态 | 上架中 / 已完成 / 已下架；可记录成交价、买家 |
| 个人页面 | 我的资料、上架中、已完成、已下架交易；修改密码 |
| 管理后台 | 审核注册、封禁/解封、重置密码、设管理员、下架违规交易 |
| 移动端 | 响应式适配，手机浏览器友好 |

## 技术栈

- **后端**：Flask 3 + Flask-SQLAlchemy
- **数据库**：SQLite（单文件，无需额外服务）
- **前端**：Jinja2 模板 + 原生 CSS + 原生 JS
- **部署**：Gunicorn + Nginx

## 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动（自动初始化数据库 + 创建管理员）
python app.py

# 3. 访问 http://127.0.0.1:5000
```

## 部署到 Linux 服务器

```bash
# 1. 上传项目到服务器
scp -r csmc-trade/ user@your-server:/opt/csmc-trade

# 2. 安装依赖（建议用虚拟环境）
cd /opt/csmc-trade
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 配置密钥（务必修改）
export CSMC_SECRET_KEY="生成一个随机长字符串"

# 4. 初始化数据库（首次）
python -c "from app import init_db; init_db()"

# 5. 安装 systemd 服务
sudo cp deploy/csmc-trade.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable csmc-trade
sudo systemctl start csmc-trade

# 6. 配置 Nginx
sudo cp deploy/nginx_csmc.conf /etc/nginx/conf.d/
# 编辑 nginx_csmc.conf 修改 server_name 和路径
sudo nginx -t && sudo nginx -s reload
```

## 管理员账号

首次启动自动创建：
- QQ号：`10000`
- 游戏ID：`admin`
- 密码：`admin123456`

**上线后请立即登录管理后台修改密码**（个人中心 → 修改密码）。

## 配置说明（config.py）

| 配置项 | 说明 | 默认值 |
|:---|:---|:---|
| `SECRET_KEY` | 会话密钥（生产必改） | 占位符 |
| `REQUIRE_APPROVAL` | 注册是否需审核 | `True` |
| `PLATFORM_NAME` | 平台名称 | CSMC 饰品交易平台 |
| `TRADES_PER_PAGE` | 每页交易数 | 24 |
| `PURPOSE_OPTIONS` | 交易目的选项 | 求购/出租/出售/交换 |
| `CURRENCY_OPTIONS` | 货币选项 | 点券/金币 |

## 后续扩展规划

- [ ] 饰品图片上传
- [ ] 交易留言/评论
- [ ] 收藏/关注
- [ ] 通知系统（站内信）
