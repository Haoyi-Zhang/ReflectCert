FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 openjdk-17-jdk-headless ca-certificates time \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /artifact
COPY . /artifact
CMD ["sh", "-c", "python3 -m unittest discover -s tests -v && python3 verify_inputs.py && python3 reproduce.py --output results/reproduced && python3 compare_results.py results/measured results/reproduced && python3 release_gate.py --artifact-root ."]
