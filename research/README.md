# EdgePrompt Research Module (Phase 1)

This module contains the implementation of the EdgePrompt research framework for running Phase 1 validation experiments with the two-tier LLM approach. The framework is designed to test and evaluate structured prompting with A/B comparison testing, multi-stage validation, and resource optimization for edge LLMs in educational contexts.

## Overview of Phase 1 Approach

For Phase 1 validation, the framework uses a simulation strategy involving two tiers of language models:

1. **CloudLLM (Large Models):** API-based models like GPT-4o or Claude used for:
   - Simulating Teacher personas (creating educational content requests)
   - Simulating Student personas (generating sample answers)
   - Performing high-level review of flagged content

2. **EdgeLLM (Small Models):** Local models or smaller API models used for:
   - Edge content generation tasks
   - Multi-stage validation checks
   - Representing what would run on edge devices

Each test case runs two scenarios that are compared:
- **Scenario A (EdgePrompt):** Uses structured prompting, multi-stage validation, and constraint enforcement
- **Scenario B (Baseline):** Uses unstructured prompting and simple validation

## Getting Started

### Prerequisites

- Python 3.10+
- System dependencies for building packages:
  - cmake
  - pkg-config
  - gcc/g++
  - make
- One of the following for running local EdgeLLM models:
  - LM Studio 
  - Ollama
- API keys for CloudLLM models:
  - OpenAI API key (for GPT models)
  - Anthropic API key (for Claude models)

### Quick Setup

We've created automated setup scripts to make environment setup easy:

1. **Install system dependencies** (requires sudo):
   ```sh
   sudo ./setup-system-deps.sh
   ```

2. **Set up Python environment** (interactive):
   ```sh
   ./setup.sh
   ```
   This script will:
   - Create and configure a Python virtual environment
   - Install required Python packages
   - Set up environment variables and API keys interactively
   - Configure PYTHONPATH automatically

3. **Start LM Studio or Ollama** and load your preferred model(s) for the EdgeLLM role.

### Running Experiments

You can run experiments using the provided scripts:

```sh
# Run with actual API calls and local inference
./run_test.sh

# Run in mock mode (no API calls, for testing)
./run_with_mock.sh
```

The scripts accept additional parameters:

```sh
# Example with custom config and output directory
./run_test.sh --config configs/test_suites/my_custom_suite.json --output data/my_test
```

Common options:
- `--config`: Specify a test suite configuration file
- `--output`: Set the output directory for results
- `--skip-verification`: Skip the validation architecture verification

> **Important Notes:** 
> - You must run all commands from the `research` directory
> - Make sure your `.env` file has the correct API keys, LM Studio URL, and/or Ollama URL
> - The system will automatically set PYTHONPATH when using the setup script

## Advanced Setup

If you prefer to set up manually rather than using the provided scripts:

1. Create a Python virtual environment:
   ```sh
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
   
3. Configure environment:
   - Copy `.env.example` to `.env`
   - Add your LM Studio URL (typically `http://localhost:1234`)
   - Add your Ollama URL (typically `http://localhost:11434`)
   - Add your OpenAI and Anthropic API keys

4. Set PYTHONPATH:
   ```sh
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   ```

## Validation Architecture

The EdgePrompt validation architecture is a critical component that ensures content quality and safety. It consists of several interrelated components:

### Key Components:

1. **ConstraintEnforcer** (`constraint_enforcer.py`):
   - Applies logical constraints to generated content
   - Checks for word count limits (min/max)
   - Filters prohibited keywords
   - Ensures required topics are addressed
   - Returns boolean validation results with violation details

2. **EvaluationEngine** (`evaluation_engine.py`):
   - Performs multi-stage validation using edge LLMs (EdgeLLM)
   - Provides proxy evaluation using larger models when needed (CloudLLM)
   - Extracts structured results from unstructured LLM outputs
   - Calculates validation scores and aggregates feedback
   - **Implements strict error handling** that immediately crashes on validation errors rather than silently continuing

3. **RunnerCore** (`runner_core.py`):
   - Orchestrates the end-to-end validation process
   - Implements A/B testing with Scenario A (EdgePrompt) and Scenario B (Baseline)
   - Manages the validation workflow including constraint enforcement and multi-stage validation
   - Collects validation metrics for comparative analysis

4. **TemplateEngine** (`template_engine.py`):
   - Processes templates with variable substitution
   - Handles various data types (strings, numbers, lists) safely
   - Supports persona templates and validation prompt templates

### Validation Workflow:

1. **Content Generation**: A question or answer is generated using EdgeLLM or CloudLLM
2. **Constraint Enforcement**: Basic logical constraints are checked using `ConstraintEnforcer`
3. **Multi-Stage Validation**: Sequential validation stages are applied using EdgeLLM
4. **Teacher Review** (if validation fails): Content failing validation is reviewed by CloudLLM 
5. **Result Logging**: Validation results and metrics are logged for analysis

### Robust JSON Processing:

The system includes robust JSON processing to handle various LLM output formats:
- JSON within markdown code blocks (````json {...} ````)
- Plain JSON objects
- Text with extractable validation fields (bullet-point / YAML format)
- Alternative field names (e.g., "valid" instead of "passed")

The validation system is designed to fail fast with clear error messages rather than continuing silently with invalid data, ensuring data integrity throughout the evaluation process.

### Verifying the Validation Architecture

To verify the validation architecture works correctly, use the included verification script:

```sh
python verify_validation.py
```

This script tests three critical components:
1. JSON processing from LLM responses in various formats
2. Template processing with mixed variable types
3. Validation result extraction from different LLM outputs

All verification checks must pass before running actual experiments.

## Analyzing Results

After running experiments, use the analysis scripts which now focus on A/B comparison:

```sh
python scripts/analyze_results.py --input data/validation_test/
python scripts/render_figures.py --input data/processed/validation_test/
```

The analysis outputs will include comparison metrics like:
- Safety effectiveness (Scenario A vs. B)
- Constraint adherence (Scenario A vs. B)
- Token usage comparison
- Latency comparison

## Directory Structure

- `configs/`: JSON configuration files for models, templates, and test suites
  - `templates/`: Contains structured prompts including persona templates
  - `test_suites/`: Test suite configurations for A/B testing
- `data/`: Experiment results (raw and processed)
- `figures/`: Generated plots and visualizations
- `runner/`: Core Python modules implementing the framework
- `scripts/`: Helper scripts for analysis and visualization

## Using Local Inference for EdgeLLM

The framework supports two backends for running local language models for the EdgeLLM role:

### LM Studio Backend

1. Start LM Studio application and load your desired model(s)
2. Ensure the API server is running (typically on port 1234)
3. Note the model's API identifier shown in LM Studio
4. Update `configs/model_configs.json` to include models with `runner_type` set to `lmstudio`
5. Set `LM_STUDIO_URL` in your `.env` file or use the `--lm-studio-url` flag

### Ollama Backend

1. Install and start Ollama
2. Pull your desired models: `ollama pull gemma3:4b`, `ollama pull llama3.2:3b`, etc.
3. Ensure the Ollama server is running (typically on port 11434)
4. Update `configs/model_configs.json` to include models with `runner_type` set to `ollama` and the appropriate `ollama_tag`
5. Set `OLLAMA_URL` in your `.env` file or use the `--ollama-url` flag

### Model Configuration

Each model in the `edge_llm_models` section of `configs/model_configs.json` requires a `runner_type` field:

```json
{
  "model_id": "gemma-3-4b-it-lmstudio",
  "client_type": "local_gguf",
  "runner_type": "lmstudio",
  ...other fields...
}
```

```json
{
  "model_id": "gemma-3-4b-it-ollama",
  "client_type": "local_gguf",
  "runner_type": "ollama",
  "ollama_tag": "gemma3:4b",
  ...other fields...
}
```

For Ollama models, the `ollama_tag` field is required to specify the exact model name as used in Ollama.

### Recommended Models

The following models work well with the framework:
- Gemma 3 12B: [LM Studio download link](https://model.lmstudio.ai/download/lmstudio-community/gemma-3-12b-it-GGUF) or `ollama pull gemma3:12b`
- Gemma 3 4B: [LM Studio download link](https://model.lmstudio.ai/download/lmstudio-community/gemma-3-4b-it-GGUF) or `ollama pull gemma3:4b`
- LLaMa 3.2 3B: [LM Studio download link](https://model.lmstudio.ai/download/hugging-quants/Llama-3.2-3B-Instruct-Q8_0-GGUF) or `ollama pull llama3.2:3b`

## Using API Models for CloudLLM

For the CloudLLM role (persona simulation and review), the framework uses cloud API models:

1. Obtain API keys from:
   - [OpenAI Platform](https://platform.openai.com/api-keys) for GPT models
   - [Anthropic Console](https://console.anthropic.com/) for Claude models
2. Add your keys to the `.env` file or provide them via CLI flags
3. Configure the desired CloudLLM model(s) in the `cloud_llm_models` section of `configs/model_configs.json`

## Mock Mode for Testing

During development or when API access is limited, you can use mock mode:

```sh
# Using the convenience script
./run_with_mock.sh

# Or directly with environment variable
MOCK_MODE=true ./run_test.sh

# Or with the CLI directly
python -m runner.runner_cli --config configs/test_suites/example_suite.json --mock-models
```

This replaces both CloudLLM and EdgeLLM calls with simulated responses, allowing you to test the framework without incurring API costs or requiring local models.

## Troubleshooting

### Common Issues:

1. **Building Package Errors**:
   - **Symptom**: Errors when building packages like sentencepiece or bitsandbytes
   - **Solution**: Install system dependencies with `sudo ./setup-system-deps.sh`

2. **JSON Parsing Errors**:
   - **Symptom**: Error messages about invalid JSON from LLM responses
   - **Solution**: The system includes robust JSON extraction for various formats. If issues persist, check the LLM response format and update extraction patterns.

3. **Template Processing Errors**:
   - **Symptom**: Type errors in template processing, particularly with numeric variables
   - **Solution**: Ensure templates use `[variable_name]` format for placeholders.

4. **Missing API Keys**:
   - **Symptom**: Warnings about missing API keys or LM Studio/Ollama URL
   - **Solution**: Run the interactive setup script or manually edit the `.env` file.

5. **Missing Dependencies**:
   - **Symptom**: Errors like `ModuleNotFoundError: No module named 'openai'`
   - **Solution**: Run `./setup.sh` which will install required packages.

6. **Validation Failures**:
   - **Symptom**: All validation stages fail with parsing errors
   - **Solution**: Verify that your EdgeLLM models can understand and respond to the validation prompts.

7. **Import Errors**:
   - **Symptom**: "ModuleNotFoundError" when running scripts
   - **Solution**: Make sure the virtual environment is activated and PYTHONPATH is set correctly.

8. **Backend Selection Issues**:
   - **Symptom**: Errors about missing LM Studio URL or Ollama URL
   - **Solution**: Make sure your `.env` file has the correct URL for the backend you're using and that all model entries have the correct `runner_type`.

### Verification:

If you suspect issues with the validation architecture, run the verification script:

```sh
python verify_validation.py
```

If any verification checks fail, review and fix the corresponding components before proceeding.

## Contributing

Please follow the implementation guidance in `docs/specifications/PROMPT_ENGINEERING.md` when making changes to this module.

## License

See the project's main LICENSE file.