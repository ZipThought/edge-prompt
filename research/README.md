# EdgePrompt Research Module

This directory contains the experimental backbone for validating the EdgePrompt methodology through structured test suites, edge simulation, and multi-stage evaluation. It is separate from the main application and is designed for reproducible research, paper integration, and algorithmic benchmarking.

## Structure Overview

- `runner/` — Core modules that orchestrate test execution.
- `configs/` — JSON-based templates, validation schemas, and hardware profiles.
- `data/` — Raw logs and processed data used for analysis.
- `figures/` — Generated visualizations and tables for the conference paper.
- `scripts/` — CLI wrappers for running experiments and rendering results.
- `notebooks/` — (Optional) Interactive exploration/debugging of test outcomes.

## Usage

1. Define or edit test suite in `configs/test_suites/`.
2. Run experiments using the main runner (`scripts/run_all.sh` or a Python entrypoint).
3. View logs in `data/raw/`, and derived insights in `data/processed/`.
4. Use `scripts/analyze_results.py` to produce paper-ready visualizations.
5. Regenerate figures into `figures/`.

## Requirements

- Python 3.10+
- Docker (for edge profile simulation)
- NVIDIA drivers (for CUDA-accelerated backends)
- Access to GPT-4 / Claude / Gemini APIs for evaluation stages

## Notes

This module is aligned with:
- `SYSTEM_VISION.md` for philosophical grounding
- `paper.pdf` for formalism and mathematical framing 