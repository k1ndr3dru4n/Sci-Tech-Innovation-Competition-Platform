# Gunicorn 配置文件
# 位置: /opt/stic/gunicorn_config.py

import multiprocessing
import os

# 服务器 socket
bind = "127.0.0.1:8000"
backlog = 2048

# 工作进程数（建议设置为 CPU 核心数 * 2 + 1）
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 日志配置
accesslog = "/opt/stic/logs/gunicorn_access.log"
errorlog = "/opt/stic/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程命名
proc_name = "stic"

# 服务器机制
daemon = False
pidfile = "/opt/stic/gunicorn.pid"
umask = 0
user = "stic"
group = "stic"
tmp_upload_dir = None

# SSL 配置（如果需要）
# keyfile = None
# certfile = None

# 性能调优
max_requests = 1000
max_requests_jitter = 50
preload_app = True

