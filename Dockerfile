# syntax=docker/dockerfile:1
# 基础镜像可用 --build-arg BASE_IMAGE=... 覆盖：
#   国内拉不动 docker.io 时：docker.m.daocloud.io/library/python:3.11-slim
#   离线/已缓存时：python@sha256:<本机镜像 digest>
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai \
    APP_ENV=docker \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# 依赖单独一层：改代码不必重装依赖。
# 国内网络慢时用 --build-arg PIP_INDEX_URL=https://pypi.org/simple 切回官方源。
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
COPY requirements.txt ./
RUN pip install --no-cache-dir -i "${PIP_INDEX_URL}" -r requirements.txt

# OCR 依赖修正：rapidocr 默认拉 opencv-python（GUI 版），在 slim 里缺 libGL/libxcb 会 import 失败。
# 换成 headless 版（无 GUI 依赖），并在构建期做一次 import 自检，失败就早点炸而不是等到运行。
RUN pip uninstall -y opencv-python \
    && pip install --no-cache-dir -i "${PIP_INDEX_URL}" --no-deps opencv-python-headless \
    && python -c "import cv2, pypdfium2, rapidocr_onnxruntime; print('ocr deps ok:', cv2.__version__)"

# 代码分层复制：VERSION / agent.json / prompt.md 是运行时配置，必须一起进镜像
COPY VERSION agent.json prompt.md ./
COPY api ./api
COPY web ./web
COPY data ./data
COPY mcps ./mcps
COPY knowledge ./knowledge

# 上传目录先建好，compose 会把宿主机 ./data 挂上来
RUN mkdir -p data/uploads

EXPOSE 8000

# 健康检查只用标准库，不额外装 curl（slim 镜像里没有）
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)"

# 说明：容器以默认 root 运行，是为了兼容 Linux 宿主机上 ./data 绑定挂载的写权限
# （上传文件要落盘）。若需非 root，请先 chown 宿主机 data 目录再改 USER。
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
