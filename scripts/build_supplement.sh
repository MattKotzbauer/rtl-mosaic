#!/bin/bash
# Build the final report supplement zip per Canvas naming convention.
# Run from repo root.
set -e

OUT="Team_11__Leonardo_Ferreira__Matthew_Kotzbauer__Warren_Zhu.zip"
TMPDIR=$(mktemp -d)
PKG="$TMPDIR/Team_11__Leonardo_Ferreira__Matthew_Kotzbauer__Warren_Zhu"
mkdir -p "$PKG"

# code we want included
rsync -a \
    --exclude='__pycache__' --exclude='.git' --exclude='.venv' \
    --exclude='.pytest_cache' --exclude='.deepeval' --exclude='*.pyc' \
    eval harness mcp docs scripts \
    "$PKG/"

# copy top-level docs
cp README.md CONTEXT.md PROGRESS.md "$PKG/"

# results JSON (keep summary + per-provider, drop large per-problem .sv outputs)
mkdir -p "$PKG/results/multi_routing" "$PKG/results/multi" \
         "$PKG/results/multi_routing_embed" "$PKG/results/multi_seed"
cp results/multi_routing/*.json          "$PKG/results/multi_routing/"       2>/dev/null || true
cp results/multi_routing_embed/*.json    "$PKG/results/multi_routing_embed/" 2>/dev/null || true
cp results/multi_seed/*.json             "$PKG/results/multi_seed/"          2>/dev/null || true
for d in results/multi/*/; do
    name=$(basename "$d")
    if [ -f "$d/results.json" ]; then
        mkdir -p "$PKG/results/multi/$name"
        cp "$d/results.json" "$PKG/results/multi/$name/"
    fi
done

# include INTEGRITY.md
cp docs/INTEGRITY.md "$PKG/docs/" 2>/dev/null || true

# slides + figures (the submitted deck + figs)
mkdir -p "$PKG/slides"
cp slides/*.tex slides/*.md slides/*.pdf "$PKG/slides/" 2>/dev/null || true
cp -r slides/figs "$PKG/slides/"

# report
mkdir -p "$PKG/report"
cp report/*.tex report/*.pdf report/*.py "$PKG/report/" 2>/dev/null || true
cp -r report/figs "$PKG/report/"

# README pointer at the top of the package so reviewers know where to start
cat > "$PKG/SUPPLEMENT_README.md" <<'EOF'
# Team 11 Final Report Supplement — rtl-mosaic

Read these in order:
1. `report/report.pdf` — the 3-page IEEE submission
2. `CONTEXT.md` — full project context, current state, open TODOs
3. `README.md` — repo overview + how to reproduce
4. `PROGRESS.md` — detailed status log + delta tables across eval revisions

To reproduce the headline numbers:
```bash
cd <package>
source ~/school/.env  # OPENAI_API_KEY, GEMINI_API_KEY, AWS creds
python3 eval/multi_routing.py --workers 16
python3 eval/make_figures.py
```

Layout:
- `eval/`     multi-LLM routing eval, scratch baseline, gold labels, figure pipeline
- `harness/`  planner + IP router + codegen + integrator
- `mcp/`      IP-search MCP server + 30-IP corpus + per-IP self-tests
- `slides/`   Beamer source + PDF + figures + spoken script (presentation 2026-04-27)
- `report/`   IEEE 2-col final report source + figures
- `results/`  Frozen JSON snapshot of headline numbers
EOF

# build the zip
cd "$TMPDIR"
zip -rq "$OUT" "Team_11__Leonardo_Ferreira__Matthew_Kotzbauer__Warren_Zhu/"

# move zip back to repo root
mv "$OUT" "$OLDPWD/" 2>/dev/null || mv "$OUT" "$(dirs -p | head -2 | tail -1)/" 2>/dev/null
echo "wrote $OUT"
ls -lh "$OUT" 2>/dev/null

rm -rf "$TMPDIR"
