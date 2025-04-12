# EdgePrompt Research Module

This module contains the implementation of the EdgePrompt research framework for running experiments to validate the EdgePrompt methodology. The framework is designed to test and evaluate structured prompting, multi-stage validation, and resource optimization for edge LLMs in educational contexts.

## Getting Started

### Prerequisites

- Python 3.10+
- LM Studio (for running local LLMs)
- Anthropic API key (for evaluation proxy)

### Installation

1. Create a Python virtual environment:
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

3. Configure environment:
   - Copy `.env.example` to `.env`
   - Add your LM Studio URL (typically `http://localhost:1234`)
   - Add your Anthropic API key for evaluation proxy

4. Start LM Studio and load your preferred model

### Running Experiments

Run a test suite using the CLI:

```sh
python -m runner.runner_cli --config configs/test_suites/example_suite.json --output data
```

Additional options:
- `--log-level DEBUG`: Increase verbosity
- `--mock-models`: Use mock models instead of real LLMs
- `--lm-studio-url URL`: Override the LM Studio URL from .env

### Analyzing Results

After running experiments, use the analysis scripts:

```sh
python scripts/analyze_results.py --input data/raw/suite_id_timestamp
python scripts/render_figures.py --input data/processed/suite_id_timestamp
```

## Directory Structure

- `configs/`: JSON configuration files for hardware, models, templates, and test suites
- `data/`: Experiment results (raw and processed)
- `figures/`: Generated plots and visualizations
- `runner/`: Core Python modules implementing the framework
- `scripts/`: Helper scripts for analysis and visualization

## Using LM Studio Integration

The framework uses LM Studio's OpenAI-compatible API to run inference on local language models:

1. Start LM Studio application and load your desired model
2. Ensure the API server is running (typically on port 1234)
3. Note the model's API identifier shown in LM Studio
4. Update `configs/model_configs.json` to include the correct `api_identifier` for your model
5. Set `LM_STUDIO_URL` in your `.env` file or use the `--lm-studio-url` flag

## Anthropic Evaluation Proxy

For external evaluation using state-of-the-art models, the framework can use Anthropic's Claude:

1. Obtain an API key from [Anthropic Console](https://console.anthropic.com/)
2. Add your key to the `.env` file as `ANTHROPIC_API_KEY`
3. Use test cases with `evaluation_criteria` defined to trigger proxy evaluation

## Data Cleanup

To keep the research data organized and clean, you can use the `cleanup_data.py` script:

```bash
# Run with default settings
python scripts/cleanup_data.py

# Specify a custom data directory
python scripts/cleanup_data.py --data-dir /path/to/data

# Skip archiving old runs
python scripts/cleanup_data.py --skip-archive

# Skip removing duplicate files
python scripts/cleanup_data.py --skip-duplicates

# Set logging level
python scripts/cleanup_data.py --log-level DEBUG
```

The script performs the following tasks:

1. **Removes duplicate test results:** When multiple test runs generate results for the same test case and model, only the most recent version is kept.

2. **Archives old runs:** Previous test runs are moved to an archive directory, organized by timestamp.

3. **Consolidates results:** Extracts key metrics from test results and saves them in a standardized format in the processed directory.

4. **Removes temporary files:** Cleans up any temporary or backup files in the data directory.

This helps maintain a clean and organized data directory structure while preserving the history of test runs.

## Contributing

Please follow the implementation guidance in `docs/implementation/RESEARCH_PIPELINE.md` when making changes to this module.

## License

See the project's main LICENSE file. 