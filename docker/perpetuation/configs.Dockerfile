# FROM python:3.11

# RUN mkdir -p /Workspace

# COPY Workspace /Workspace

# # COPY . /Workspace

# WORKDIR /Workspace

# RUN pip install --no-cache-dir requests colorama

# # CMD ["python", "your_script.py"]
# CMD ["/bin/bash"]
# 使用 slim 版本可以大幅缩小镜像体积，且包含运行所需的所有基础工具
# FROM python:3.11-slim
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# 设置环境变量，确保 Python 输出直接打印到终端（不缓冲），方便实时查看 Agent 留痕
ENV PYTHONUNBUFFERED=1


COPY Workspace /Workspace
# 设置容器内的工作目录
WORKDIR /Workspace

# 先安装依赖（利用 Docker 缓存机制：只要依赖列表不变，这一步就不会重新执行）
RUN pip install --no-cache-dir \
    pyyaml \
    openai \
    tiktoken \
    colorama \
    requests \
    anthropic \
    google-genai \
    tqdm
# # 设置 tiktoken 缓存目录（防止它默认去 /tmp 找，容器重启后丢失）
# ENV TIKTOKEN_CACHE_DIR=/root/.tiktoken_cache

# # 在构建镜像阶段执行一次下载
# RUN mkdir -p $TIKTOKEN_CACHE_DIR && \
#     python3 -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

CMD ["/bin/bash"]