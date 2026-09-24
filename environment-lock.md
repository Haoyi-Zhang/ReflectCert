# Environment and Dependency Contract

The artifact intentionally avoids mandatory third-party Python packages. It requires a supported CPython 3 interpreter and a JDK that provides `javac` and the compiler Tree API. The paper build additionally requires the ACM LaTeX class and the packages imported by `paper/main.tex`; `paper/build.sh` is the authoritative build entry point.

`results/environment-audit.json` records the toolchain used for the frozen run without host names or user paths. Exact tool versions are provenance, not semantic equality keys. Different conforming Python/JDK/TeX versions should reproduce the deterministic JSON results; PDF binary metadata may differ, so the release compares extracted text and rendered pages when auditing paper stability.
