# SPDX-License-Identifier: GPL-3.0-or-later
# rfpgen 실행 이미지: Python·Node 사이드카·Chromium·LibreOffice·한글 글꼴을 모두 담아 설치 없이 쓴다.
#
#   docker build -t rfpgen .
#   docker run --rm -v "$PWD:/work" rfpgen start 제안요청서.hwp 공고문.pdf
#
# 결과는 현재 폴더의 projects/ 아래에 생긴다. LLM을 쓰려면 -e RFP_ANTHROPIC_API_KEY 를 넘긴다.
FROM python:3.13-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs npm libreoffice-impress fonts-noto-cjk fontconfig \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev

COPY sidecars ./sidecars
RUN cd sidecars/node \
 && npm ci \
 && npx playwright install --with-deps chromium \
 && rm -rf /root/.npm /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH" \
    RFPGEN_SIDECAR_DIR=/app/sidecars/node

WORKDIR /work
ENTRYPOINT ["rfpgen"]
CMD ["--help"]
