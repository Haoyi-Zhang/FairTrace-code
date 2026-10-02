# Clean reproduction record

This directory records a clean-copy replay in the same execution environment. It is not an independent external replication and it does not replace review of the mathematical proofs.

The standalone repository copy was created without Python caches or prior reproduced output. All **45** unit tests passed. The **22** scientific stages were then executed exactly once through the documented `--stage` interface into one fresh `reproduced/` directory. The resulting `summary.json` contains all 22 stages. `check_reproduction.py` matched **60** deterministic scientific files against the retained results with zero mismatches; CPU time, wall time, and peak RSS are excluded from semantic comparison because they are machine-dependent. The retained graph certificate was accepted by the command-line checker.

The clean scientific replay used one worker under the repository's 3 GiB address-space limit. Summed per-stage measurements were **72.587 CPU seconds** and **72.593 wall seconds**; the maximum per-stage peak RSS was **104,752 KiB**. These are accounting measurements, not performance claims.

The replay includes **1,980** direct stateless invalid-floor formula checks, **3,960** independent fixed-bound reflection checks at `R-1` and `R`, and **1,980** checked lasso witnesses at `R`. It also retains the output-only scope of the **47,104** finite composition checks and the stable-edge-identity expansion regressions.

The paper was copied without `main.pdf` or LaTeX auxiliary files and rebuilt with `python3 build.py`. It produced exactly **50 pages** and **40 bibliography entries**. `paper-warning-scan.txt` is empty: no undefined citation/reference, overfull box, LaTeX error, fatal error, or rerun warning matched the scan. `paper-fonts.txt` records that all fonts are embedded. The source-only build used 7.27 user CPU seconds, 0.16 system seconds, 7.12 wall seconds, and 92,204 KiB maximum RSS.

`paper-visual-audit.json` records a 220-DPI render of all 50 pages, five ten-page contact-sheet inspections, and full-size checks of pages 7 and 24. No outer-20-pixel ink, blank page, clipping, overlap, missing figure, or unreadable contact-sheet anomaly was observed.

`commands.txt` records the executed order. The ordinary command `python3 reproduce.py --output reproduced` is supported, but stage mode was used here so each bounded stage has its own completion record within the execution interface.

No experiment or obligation named `F3` exists in the supplied manuscript or artifact, so this record makes no unrun `F3` claim.
