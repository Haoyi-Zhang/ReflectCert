FROM eclipse-temurin:17-jdk
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /artifact
COPY . /artifact
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["sh", "run_release_gate.sh"]
