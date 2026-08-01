# 云核软件资产治理平台 —— 后端镜像
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# git 用于克隆代码仓
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# 数据目录（挂载持久化卷）
ENV DATA_DIR=/data
ENV DATABASE_URL=
RUN mkdir -p /data

EXPOSE 8000

# 生产模式：gunicorn + uvicorn worker
# 注意：进程内异步任务队列只在单个 worker 内执行，
# 建议 APP_WORKERS=1（默认）；如需多 worker，可配合 Redis/RQ 扩展（见 docs/DESIGN.md）
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers ${APP_WORKERS:-1} --timeout 300 --access-logfile - --error-logfile -"]
