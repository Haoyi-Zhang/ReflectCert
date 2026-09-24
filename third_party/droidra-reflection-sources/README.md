# Redistributed DroidRA reflection sources

This directory contains nine unmodified Java source files from
`serval-snt-uni-lu/DroidRA` at commit
`b766a32a23178a54d095fb0a473e6ec77aad2166`. They are the exact files consumed
by the source-frontend experiment for Reflection5 through Reflection13. Each
file retains its upstream header. The enclosing DroidRA repository identifies
its license as GNU LGPL 2.1; a verbatim copy is included as
`LICENSE-LGPL-2.1.txt`.

`frontend/public-gold.json` records the upstream path and Git blob identity for
each accepted reflection event. `rrc/java_frontend.py` recomputes Git blob
identities before running the extractor. The sources are not modified, compiled
as Android apps, executed, or represented as a whole-program benchmark.
