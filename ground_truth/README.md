# Sealed ground truth (do not let the scanner read this)

`expected_pii.json` is a hand-labelled answer key for the synthetic sample
schema. It exists only to measure how well the scanner does. It was written by a
human reviewing the schema by eye, independently of the classifier rules, and it
deliberately disagrees with the scanner in three places so the reported metrics
are honest rather than circular:

- `patients.notes` is real PII (free text) that the name-based scanner misses (a
  false negative, so recall is below 1.0).
- `cities.city_name` and `analytics_events.geo_region` are reference-grade
  columns the scanner over-flags (false positives, so precision is below 1.0).

## The firewall

The scanning pipeline (`schema_scanner`, `code_scanner`, `classifier`,
`flow_graph`, `article30`, `pipeline`) is provably forbidden to open anything in
this directory. Enforcement is two-layer:

1. Static scan (`firewall.check_static`): the pipeline source is scanned for any
   textual reference to this directory. Any reference fails the build.
2. Runtime audit (`firewall.sealed`): while the pipeline runs, a Python audit
   hook watches every file `open` and raises if this directory is touched. A
   booby-trap unit test proves the hook actually fires.

Only `evaluate.py` may open this file, and only after `pipeline.py` has already
written its artifacts. This mirrors the control a Technology Risk reviewer wants
to see: the thing being measured cannot see its own answer key.
