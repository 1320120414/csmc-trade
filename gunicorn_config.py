"""Gunicorn 配置"""
bind = "127.0.0.1:5000"
workers = 3
timeout = 30
accesslog = "-"
errorlog = "-"
