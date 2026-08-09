#!/bin/bash
# CSMC 饰品交易平台 - 一键部署脚本
# 使用方法：
#   1. 上传此脚本和项目到服务器（或直接在服务器上 git clone）
#   2. chmod +x deploy.sh && sudo ./deploy.sh
# 前置条件：服务器已安装 python3、nginx
set -e

# ============ 配置区（按需修改）============
APP_DIR="/opt/csmc-trade"
APP_USER="www-data"
DOMAIN_OR_IP="你的域名或IP"        # ← 改成你的域名或IP
SECRET_KEY="$(head -c 32 /dev/urandom | base64)"  # 自动生成随机密钥
REPO_URL="https://github.com/1320120414/csmc-trade.git"
# ==========================================

echo "=========================================="
echo "  CSMC 饰品交易平台 - 部署脚本"
echo "=========================================="

# 1. 安装系统依赖
echo "[1/7] 安装系统依赖..."
if command -v apt-get &> /dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip nginx git > /dev/null
elif command -v yum &> /dev/null; then
    yum install -y -q python3 python3-devel nginx git
fi
echo "  ✓ 系统依赖已安装"

# 2. 克隆/更新代码
echo "[2/7] 获取代码..."
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR"
    git pull -q origin main || echo "  ! git pull 失败，使用现有代码"
else
    git clone -q "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi
echo "  ✓ 代码已就位: $APP_DIR"

# 3. 创建虚拟环境并安装依赖
echo "[3/7] 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "  ✓ Python 依赖已安装"

# 4. 配置密钥并初始化数据库
echo "[4/7] 初始化数据库..."
export CSMC_SECRET_KEY="$SECRET_KEY"
python -c "from app import init_db; init_db()"
# 设置目录权限
chown -R $APP_USER:$APP_USER "$APP_DIR"
echo "  ✓ 数据库已初始化"

# 5. 配置 Gunicorn systemd 服务
echo "[5/7] 配置 systemd 服务..."
SERVICE_FILE="/etc/systemd/system/csmc-trade.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=CSMC Trade Platform
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="CSMC_SECRET_KEY=$SECRET_KEY"
ExecStart=$APP_DIR/venv/bin/gunicorn -c gunicorn_config.py "app:app"
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable csmc-trade
systemctl restart csmc-trade
echo "  ✓ systemd 服务已启动"

# 6. 配置 Nginx
echo "[6/7] 配置 Nginx..."
NGINX_FILE="/etc/nginx/conf.d/csmc-trade.conf"
cat > "$NGINX_FILE" << EOF
server {
    listen 80;
    server_name $DOMAIN_OR_IP;
    client_max_body_size 10m;

    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

nginx -t 2>/dev/null
systemctl reload nginx
systemctl enable nginx
echo "  ✓ Nginx 已配置并重载"

# 7. 检查状态
echo "[7/7] 检查服务状态..."
sleep 2
if systemctl is-active --quiet csmc-trade; then
    echo "  ✓ csmc-trade 服务运行中"
else
    echo "  ✗ csmc-trade 服务异常，请检查: journalctl -u csmc-trade -e"
    exit 1
fi

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  访问地址:  http://$DOMAIN_OR_IP"
echo "  管理员:    QQ=10000  游戏ID=admin  密码=admin123456"
echo "  密钥已保存: $SECRET_KEY"
echo ""
echo "  常用命令:"
echo "    查看日志:   journalctl -u csmc-trade -f"
echo "    重启服务:   systemctl restart csmc-trade"
echo "    查看状态:   systemctl status csmc-trade"
echo ""
echo "  ⚠️  请立即登录管理后台修改管理员密码！"
echo ""
