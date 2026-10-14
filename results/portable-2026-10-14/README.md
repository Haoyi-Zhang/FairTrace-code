# Portable one-worker scientific replay

This directory retains an actual Windows/Python 3.12.14 execution of all 22
reviewed finite stages through the portable CLI. All 60 deterministic scientific
files match the original retained results. This is a same-source local replay
of authored finite domains, not independent replication or production evidence.

The recorded stage totals are 71.289695 wall seconds and 70.656250 CPU seconds.
They are accounting records, not a speedup comparison with a different host.
Every resource record names `portable-no-posix-limit`; address-space limit and
peak RSS are null. The POSIX backend was unavailable and unexecuted on this host.
Default POSIX execution still requires and applies its resource limit.

`environment.json` contains the actual runtime/platform/argv;
`source-bindings.json` pins the unchanged stage sources and comparator outcome.
The original result trees remain unchanged. Reproduce into a new directory:

```sh
python -B reproduce.py --portable --output NEW_DIRECTORY
python -B check_reproduction.py results NEW_DIRECTORY
```

Do not use `-O` for the campaign: its existing assertion guard still rejects
optimized execution. Ordinary and optimized unittest receipts are separate.
