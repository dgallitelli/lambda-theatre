FROM ubuntu:24.04

# Layer 1: OS packages (rarely changes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3-pip curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Layer 2: Playwright + Chromium + system deps (changes on version bumps)
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt && \
    playwright install chromium --with-deps && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* && \
    find /opt/playwright-browsers -name "*.pak" ! -name "en-US.pak" \
        ! -name "resources.pak" ! -name "chrome_100_percent.pak" \
        -delete 2>/dev/null; \
    rm -rf /opt/playwright-browsers/*/chrome-linux*/locales && \
    rm -rf /usr/share/doc /usr/share/man /usr/share/info && \
    rm -rf /root/.cache/pip /tmp/requirements.txt

# Layer 3: Lambda runtime (rarely changes)
RUN pip3 install --no-cache-dir --break-system-packages awslambdaric && \
    rm -rf /root/.cache/pip

RUN curl -fsSL \
    "https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie" \
    -o /usr/local/bin/aws-lambda-rie && \
    chmod +x /usr/local/bin/aws-lambda-rie

COPY entry.sh /entry.sh
RUN chmod +x /entry.sh

# Layer 4: Handler code (changes most often — LAST)
COPY handler.py /var/task/

WORKDIR /var/task
ENV HOME=/tmp

ENTRYPOINT ["/entry.sh"]
CMD ["handler.handler"]
