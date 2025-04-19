# EdgePrompt Research Module (Phase 1)

This module contains the implementation of the EdgePrompt research framework for running Phase 1 validation experiments with the two-tier LLM approach. The framework is designed to test and evaluate structured prompting with A/B comparison testing, multi-stage validation, and resource optimization for edge LLMs in educational contexts.

## Overview of Phase 1 Approach

For Phase 1 validation, the framework uses a simulation strategy involving two tiers of language models:

1. **LLM-L (Large Models):** API-based models like GPT-4o or Claude used for:
   - Simulating Teacher personas (creating educational content requests)
   - Simulating Student personas (generating sample answers)
   - Performing high-level review of flagged content

2. **LLM-S (Small Models):** Local models or smaller API models used for:
   - Edge content generation tasks
   - Multi-stage validation checks
   - Representing what would run on edge devices

Each test case runs two scenarios that are compared:
- **Scenario A (EdgePrompt):** Uses structured prompting, multi-stage validation, and constraint enforcement
- **Scenario B (Baseline):** Uses unstructured prompting and simple validation

## Getting Started

### Prerequisites

- Python 3.10+
- LM Studio (for running local LLM-S models)
- API keys for LLM-L models:
  - OpenAI API key (for GPT models)
  - Anthropic API key (for Claude models)

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
   - Add your LM Studio URL (typically `http://localhost:1234`) for LLM-S models
   - Add your OpenAI and/or Anthropic API keys for LLM-L models

4. Start LM Studio and load your preferred model(s) for the LLM-S role

### Running Experiments

Run a test suite using the CLI:

```sh
python -m runner.runner_cli --config configs/test_suites/structured_prompting_guardrails.json --output data
```

Additional options:
- `--log-level DEBUG`: Increase verbosity
- `--mock-models`: Use mock models instead of real LLMs
- `--lm-studio-url URL`: Override the LM Studio URL from .env
- `--openai-api-key KEY`: Override the OpenAI API key from .env
- `--anthropic-api-key KEY`: Override the Anthropic API key from .env

> **Important Note:** 
> - You must run the CLI from the `research` directory
> - Make sure the `model_configs.json` file exists in the `configs` directory and contains both `llm_l_models` and `llm_s_models` sections
> - The Python path must be set up correctly to find the modules. If you encounter import errors, try:
>   ```sh
>   export PYTHONPATH=$PYTHONPATH:$(pwd)  # On Windows: set PYTHONPATH=%PYTHONPATH%;%CD%
>   ```

### Analyzing Results

After running experiments, use the analysis scripts which now focus on A/B comparison:

```sh
python scripts/analyze_results.py --input data/raw/suite_id_timestamp
python scripts/render_figures.py --input data/processed/suite_id_timestamp
```

The analysis outputs will include comparison metrics like:
- Safety effectiveness (Scenario A vs. B)
- Constraint adherence (Scenario A vs. B)
- Token usage comparison
- Latency comparison

## Directory Structure

- `configs/`: JSON configuration files for hardware profiles, models, templates, and test suites
  - `templates/`: Contains structured prompts including new persona templates
  - `test_suites/`: Test suite configurations for A/B testing
- `data/`: Experiment results (raw and processed)
- `figures/`: Generated plots and visualizations
- `runner/`: Core Python modules implementing the framework
- `scripts/`: Helper scripts for analysis and visualization

## Using LM Studio for LLM-S

The framework uses LM Studio's OpenAI-compatible API to run inference on local language models for the LLM-S role:

1. Start LM Studio application and load your desired model(s)
2. Ensure the API server is running (typically on port 1234)
3. Note the model's API identifier shown in LM Studio
4. Update `configs/model_configs.json` to include the correct models in the `llm_s_models` section
5. Set `LM_STUDIO_URL` in your `.env` file or use the `--lm-studio-url` flag

## Using API Models for LLM-L

For the LLM-L role (persona simulation and review), the framework uses cloud API models:

1. Obtain API keys from:
   - [OpenAI Platform](https://platform.openai.com/api-keys) for GPT models
   - [Anthropic Console](https://console.anthropic.com/) for Claude models
2. Add your keys to the `.env` file or provide them via CLI flags
3. Configure the desired LLM-L model(s) in the `llm_l_models` section of `configs/model_configs.json`

## Mock Mode for Testing

During development or when API access is limited, you can use mock mode:

```sh
python -m runner.runner_cli --config configs/test_suites/example_suite.json --mock-models
```

This replaces both LLM-L and LLM-S calls with simulated responses, allowing you to test the framework without incurring API costs or requiring local models.

## Contributing

Please follow the implementation guidance in `docs/specifications/PROMPT_ENGINEERING.md` when making changes to this module.

## License

See the project's main LICENSE file. 