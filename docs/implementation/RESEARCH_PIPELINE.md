# EdgePrompt Research Pipeline: Implementation Guidance

## 1. Introduction

**Purpose:** This document provides detailed implementation guidance for generating the **Phase 1** Python codebase for the EdgePrompt research framework. The goal is to create a system capable of executing the experiments defined in `docs/specifications/PROMPT_ENGINEERING.md` (referred to as "the Spec") to empirically validate the core methodology presented in the EdgePrompt paper (Syah et al.).

**Target Audience:** AI code generation tools and human developers responsible for implementing the research framework.

**Scope:** This guide focuses solely on the **Phase 1** requirements outlined in the Spec. Phase 2 features (system adaptation, human evaluation, etc.) should be considered for architectural extensibility but are **not** to be implemented at this stage.

**Language:** The implementation shall be in **Python 3.10+**.

**Core Methodology:** The framework validates EdgePrompt's **prompt-engineering-only** approach, using structured prompts and multi-stage validation without model fine-tuning.

**Target Directory:** The resulting codebase should reside within the `/research` directory of the main project, potentially replacing or significantly refining any existing code there.

**Reference Specification:** All implementation details must align with `docs/specifications/PROMPT_ENGINEERING.md`. This document translates that spec into more concrete implementation directives.

## 2. Configuration and Structure

### 2.1. Expected Test Case Schema (within Test Suite JSON)

Each object within the `test_cases` array in a Test Suite JSON file should adhere to the following schema:

```json
{
  "id": "string", // Unique identifier for the test case run (e.g., "valid_answer_multi_stage")
  "description": "string (optional)", // Human-readable description
  "template_ref": "string | null", // ID of the generation template to use (null for unstructured)
  "prompting_style": "string (optional)", // e.g., "structured", "unstructured" (for comparison tests)
  "validation_mode": "string (optional)", // e.g., "multi_stage", "single_stage", "none" (for validation tests)
  "variables": {
    // Key-value pairs matching variables needed by the referenced template OR
    // a single key like "task_description" for unstructured prompts
    "key1": "value1",
    "key2": "value2",
    // ...
  },
  "validation_answer": "string (optional)", // Predefined answer for validation tests (if not generating)
  "evaluation_criteria": "string (optional)", // Instructions for the LLM evaluation proxy
  "expected_outcome_notes": "string (optional)" // Notes for human analysis comparison
}
```

### 2.2. Target Directory Structure

The implementation should follow this structure within the `/research` directory:

```
research/
├── configs/                  # JSON configurations (loaded by ConfigLoader)
│   ├── hardware_profiles.json
│   ├── model_configs.json
│   ├── templates/
│   │   └── *.json            # Template definitions (Tc, As, R', v_i)
│   └── test_suites/
│       └── *.json            # Test suite specifications (containing test_cases)
├── data/                     # Experiment results
│   ├── raw/                  # Raw output logs (JSONL, individual JSONs)
│   │   └── {suite_id}_{timestamp}/ # Subdir per run
│   └── processed/            # Processed data for analysis (CSVs)
├── figures/                  # Generated plots for the paper
├── runner/                   # Core Python modules for the framework
│   ├── __init__.py
│   ├── config_loader.py
│   ├── environment_manager.py
│   ├── evaluation_engine.py
│   ├── metrics_collector.py
│   ├── model_manager.py
│   ├── result_logger.py
│   ├── runner_cli.py         # Command-line entry point
│   ├── runner_core.py        # Main orchestration logic
│   ├── template_engine.py
│   └── test_executor.py
├── scripts/                  # Helper scripts
│   ├── analyze_results.py    # Processes raw data -> processed data (Acts as ResultsAnalyzer)
│   ├── render_figures.py     # Generates plots from processed data
│   └── run_all.sh            # Script to run all test suites
├── notebooks/                # (Optional) Jupyter notebooks for debugging/analysis
├── requirements.txt          # Python dependencies
└── README.md                 # Description of the research module
```

### 2.3 Runtime Configuration

The framework requires configuration for external services and runtime parameters. These should be managed via environment variables or a configuration file (e.g., `.env` loaded by `python-dotenv`).

**Required Configuration:**
*   `LM_STUDIO_URL`: The base URL of the running LM Studio server (e.g., `http://localhost:1234`). Crucial for connecting `TestExecutor` to the local LLM.
*   `ANTHROPIC_API_KEY`: Required **if** using Anthropic models (e.g., Claude 3.5 Sonnet) for the evaluation proxy (Phase 1). Manage securely (e.g., via `.env` file).
*   *(Optional)* API Keys for other evaluation proxy LLMs (e.g., `OPENAI_API_KEY`).
*   *(Optional)* Configuration for mock mode (`MOCK_MODE=true/false`, default is `false`).

## 3. Core Component Implementation (`/runner` modules)

Implement the following Python classes, corresponding to the components defined in the Spec (Sec 1 & 2). Ensure classes have clear responsibilities, type hinting, logging, and robust error handling.

### 3.1. `ConfigLoader` (`runner/config_loader.py`)

*   **Responsibility:** Load and validate JSON configuration files (test suites, hardware profiles, model configs, templates). Resolve relative paths.
*   **Key Methods:**
    *   `__init__(config_path)`: Takes path to the main test suite config.
    *   `load_test_suite()`: Loads the main suite JSON, validates basic structure (required fields from Spec Sec 4), and attempts to load referenced hardware/model configs (using other methods). Returns a dictionary.
    *   `load_hardware_profile(profile_id)`: Loads the specific hardware profile JSON from `configs/hardware_profiles.json`. Returns a dict or None.
    *   `load_model_config(model_id)`: Loads the specific model config JSON from `configs/model_configs.json`. **Must ensure the config includes the `api_identifier` key needed for LM Studio API calls.** Returns a dict or None.
    *   `load_template(template_name)`: Loads a specific template JSON from `configs/templates/`. Returns a dict or None.
*   **Implementation Notes:** Use Python's `json` library. Handle `FileNotFoundError` and `JSONDecodeError` gracefully. Resolve paths relative to the `configs/` directory.

### 3.2. `ModelManager` (`runner/model_manager.py`)

*   **Responsibility:** Primarily manages model *configurations* and *metadata* for Phase 1, especially when using LM Studio where the model runs externally. Verifies model accessibility via LM Studio API.
*   **Key Methods:**
    *   `__init__(model_cache_dir=None, lm_studio_url=None)`: Store LM Studio URL if provided.
    *   `initialize_model(model_id, model_config, mock_mode=False)`:
        *   If `mock_mode` is True, return an instance of `MockModel`.
        *   If `mock_mode` is False:
            1.  Verify the model's `api_identifier` is present in `model_config`.
            2.  **(Optional but Recommended):** Call `check_model_availability(api_identifier)` to query the LM Studio `/v1/models` endpoint and ensure the specified model is loaded. Raise `ValueError` if not available.
            3.  Return a simple object or dictionary containing essential metadata needed by `TestExecutor`, specifically `{'api_identifier': model_config['api_identifier']}`. No actual model loading occurs in this class for LM Studio.
    *   `unload_model(model_id)`: For LM Studio, this might be a no-op or simply clear internal references.
    *   `get_model_info(model_id)`: Load model config using `ConfigLoader` and return relevant details (excluding potentially sensitive paths/URLs).
    *   `check_model_availability(api_identifier)`: (Helper method) Uses `requests` or `openai` client (with base_url) to hit `LM_STUDIO_URL/v1/models`. Check if the `api_identifier` is present in the returned list. Return `True` or `False`. Handle connection errors.
*   **Implementation Notes:**
    *   **Mock Model:** Implement a `MockModel` class with a `generate(prompt, **kwargs)` method returning a predictable string (e.g., `f"[Mock output for prompt: {prompt[:30]}...]"`) and placeholder token counts (`'input_tokens': len(prompt.split()), 'output_tokens': 10`).
    *   **LM Studio Focus:** For Phase 1, this class mainly acts as a config validator and provider for the `api_identifier`.
    *   **Model Support:** Support for models specified in model_configs.json, prioritizing:
        - gemma-3-12b-edge (GGUF, from lmstudio-community)
        - gemma-3-4b-edge (GGUF, from lmstudio-community) 
        - llama-3.2-3b-edge (Q8_0, from hugging-quants)
    *   **Adapter Implementation:** Implement adapters for llama.cpp as the primary inference engine
    *   **Resource Management:** Include proper resource management for model loading/unloading
    *   **Context Window:** Support context window management based on model specifications

### 3.3. `TemplateEngine` (`runner/template_engine.py`)

*   **Responsibility:** Process templates by substituting variables and encoding basic constraints. Implements Spec Algo 2.2.
*   **Key Methods:**
    *   `__init__(template_dir)`: Optional directory for templates.
    *   `load_template(template_name)`: Loads template JSON (can delegate to `ConfigLoader`).
    *   `process_template(template, variables)`: Performs variable substitution (e.g., using regex `\[([a-zA-Z_]+)\]`) and basic constraint appending/formatting based on template type. Perform basic whitespace optimization. Raise `ValueError` if required variables are missing. Returns the processed prompt string.
    *   `extract_template_variables(template)`: Utility to list variables in a template pattern.
*   **Implementation Notes:**
    *   **Multiline Patterns:** The `pattern` field in template JSON files **must** support multiline strings (standard JSON behavior).
    *   **Constraint Encoding:** Append constraints under a clear heading (e.g., "CONSTRAINTS:") as shown in Spec examples.

### 3.4. `EnvironmentManager` (`runner/environment_manager.py`)

*   **Responsibility:** Simulate hardware constraints. Implements Spec Algo 2.1.
*   **Key Methods:**
    *   `configure_environment(hardware_profile)`: Attempts to apply resource limits (memory, CPU cores) based on the profile's `simulation_config`. Use `subprocess` to call system tools like `cgcreate`/`echo` (Linux cgroups) or `docker run` commands specified in the profile. Log warnings if constraints cannot be applied on the current OS.
    *   `reset_environment()`: Attempts to remove applied constraints (e.g., remove cgroups, stop Docker container).
    *   *(Context Manager)*: Implement `__enter__` and `__exit__` to allow usage like `with environment_manager.apply(profile): ...`. `__enter__` calls `configure_environment`, `__exit__` calls `reset_environment`.
*   **Implementation Notes:** This is platform-dependent. Prioritize Linux cgroups support. Use Docker as a cross-platform alternative if feasible. Gracefully handle cases where simulation is not possible.

### 3.5. `MetricsCollector` (`runner/metrics_collector.py`)

*   **Responsibility:** Collect performance metrics during test execution. Implements Spec Algo 2.4.
*   **Key Methods:**
    *   `__init__(sampling_interval_ms)`: Set sampling rate.
    *   `start_collection()`: Start background thread for sampling. Record start time.
    *   `stop_collection()`: Stop background thread. Calculate duration, average/peak metrics. Return results dict.
    *   `_collection_loop()`: (Private) Background thread function. Uses `psutil` (CPU/RAM) and `pynvml` (NVIDIA GPU usage/memory/power, if available) to sample metrics at intervals. Store data in lists.
*   **Implementation Notes:** Make `psutil` and `pynvml` optional dependencies. Handle `ImportError` and gracefully disable detailed metrics if libraries are missing or permissions are insufficient (e.g., for power usage). Ensure thread safety if needed (though likely not critical for this structure). Report consistent units (ms, MB).

### 3.6. `TestExecutor` (`runner/test_executor.py`)

*   **Responsibility:** Execute a single LLM inference task against the configured LM Studio instance. Implements the core inference part of Spec Algo 2.5 using the OpenAI-compatible API.
*   **Key Methods:**
    *   `__init__(lm_studio_url)`: Store the base URL for LM Studio.
    *   `execute_test(model_metadata, prompt, generation_params)`:
        1.  Takes model metadata (containing `api_identifier`), prompt string, and generation parameters.
        2.  Instantiate `openai.OpenAI` client: `client = OpenAI(base_url=self.lm_studio_url, api_key="lm-studio")`.
        3.  Construct `messages` list: `[{"role": "system", ...}, {"role": "user", "content": prompt}]`. (System prompt can be generic or configured).
        4.  Call `client.chat.completions.create(...)` within a `try...except` block, passing `model=model_metadata['api_identifier']`, `messages`, and relevant `generation_params` (temperature, max_tokens, etc.).
        5.  Extract `output_text = completion.choices[0].message.content`.
        6.  Extract `input_tokens = completion.usage.prompt_tokens`.
        7.  Extract `output_tokens = completion.usage.completion_tokens`.
        8.  Return `{'output': output_text, 'input_tokens': input_tokens, 'output_tokens': output_tokens}`. Handle API errors (connection, status) and return an error state if necessary.
*   **Implementation Notes:** Requires the `openai` library. Handle potential errors from the API call robustly.

### 3.7. `EvaluationEngine` (`runner/evaluation_engine.py`)

*   **Responsibility:** Perform multi-stage validation (using edge LLM via `TestExecutor`) and proxy LLM evaluation (using Anthropic Claude). Implements Spec Algo 2.3 and 2.6.
*   **Key Methods:**
    *   `validate_result(question, answer, validation_sequence, edge_llm_engine_func)`: Implements the multi-stage loop (Algo 2.3). Takes the question/answer, the loaded validation sequence definition, and a *function* (or callable object) that represents the `TestExecutor.execute_test` interface (to run the validation prompts on the edge LLM). Uses `TemplateEngine` to process each stage's prompt. Parses the structured JSON output from each stage's LLM response robustly (handle errors, retries). Aggregates results, score, and feedback. Returns the final `validation_result` dictionary.
    *   `evaluate_with_llm_proxy(content_to_evaluate, reference_criteria, evaluation_role, evaluation_llm_config)`:
        *   Implements Algo 2.6 using the `anthropic` Python library.
        *   Requires `ANTHROPIC_API_KEY` in `evaluation_llm_config`.
        *   Instantiates `anthropic.Anthropic` client.
        *   Constructs `system` and `user` prompts, explicitly requesting JSON output.
        *   Calls `client.messages.create(...)` with appropriate model (e.g., `"claude-3-5-sonnet-latest"`), low temperature, prompts.
        *   Robustly extracts and parses the JSON object from the response text (handling potential preamble/postamble).
        *   Handles `anthropic.APIError` exceptions.
        *   Returns parsed evaluation dictionary or error state.
*   **Implementation Notes:** Robust JSON parsing from LLM responses is critical. Implement retry logic or default values for failed parsing. Ensure interaction with external APIs (for proxy eval) handles network errors and API key management (via configuration).

### 3.8. `ResultLogger` (`runner/result_logger.py`)

*   **Responsibility:** Save individual and aggregate results to the filesystem. Aligns with Spec Sec 6.1.
*   **Key Methods:**
    *   `__init__(output_dir)`: Set the base output directory.
    *   `log_result(result_dict, suite_id, timestamp_str)`: Saves a single test run dictionary to two places: an individual timestamped JSON file and appended as a single line to `all_results.jsonl` within a run-specific subdirectory (e.g., `data/raw/{suite_id}_{timestamp_str}/`).
    *   `log_aggregate_results(analysis_summary, suite_id, timestamp_str)`: Saves the final analysis summary dictionary (from `RunnerCore`) to a summary JSON file in the run-specific subdirectory.
*   **Implementation Notes:** Ensure run-specific subdirectories are created under `data/raw/`. Use Python's `json` library. Handle file I/O errors. Append to JSONL safely.

### 3.9. `RunnerCore` (`runner/runner_core.py`)

*   **Responsibility:** Orchestrate the entire test suite execution. Implements Spec Algo 2.7 (Phase 1).
*   **Key Methods:**
    *   `__init__(config_path, output_dir, log_level)`: Initialize all other components (`ConfigLoader`, `ModelManager`, `TemplateEngine`, etc.), passing `LM_STUDIO_URL` to `TestExecutor`.
    *   `run_test_suite()`: The main execution loop.
        1.  Loads the test suite using `ConfigLoader`.
        2.  Performs LM Studio availability check before starting loops.
        3.  Iterates through specified `hardware_profiles`.
        4.  Iterates through specified `models`.
        5.  Iterates through `test_cases` in the suite.
        6.  For each combination:
            *   Use `EnvironmentManager` context manager (`with em.apply(profile):`) to configure/reset the environment.
            *   Use `ModelManager` to initialize the required model.
            *   Use `TemplateEngine` to process the necessary template(s) with `test_case['variables']`.
            *   Use `MetricsCollector` to start/stop timing and resource monitoring around the core task(s).
            *   Use `TestExecutor` to run the primary generation task.
            *   If needed by the test case/suite:
                *   Use `EvaluationEngine.validate_result` (passing `TestExecutor.execute_test` as the engine func) for multi-stage validation.
                *   Use `EvaluationEngine.evaluate_with_llm_proxy` for proxy evaluation.
            *   Consolidate all results (generation, validation, evaluation, metrics, config info, token counts) into a result dictionary.
            *   Use `ResultLogger` to save the individual result.
            *   Use `ModelManager` to unload model if necessary (optional optimization).
        7.  After all loops, calculate aggregate summary statistics.
        8.  Use `ResultLogger` to save the aggregate summary.
        9.  Return the aggregate summary.
*   **Implementation Notes:** This class ties everything together. Manage component dependencies (e.g., pass `TestExecutor` instance/method to `EvaluationEngine`). Implement clear logging for each step. Handle exceptions within the loops gracefully to allow the suite to continue if one test case fails.

## 4. Configuration Handling

*   Use JSON files in `/research/configs` for static configurations.
*   Use environment variables or a `.env` file (via `python-dotenv`) for runtime secrets/URLs (`LM_STUDIO_URL`, `ANTHROPIC_API_KEY`).
*   Include a `--mock-models` CLI flag (handled by `runner_cli.py`) to enable mock mode in `ModelManager`.
*   `ConfigLoader` is responsible for loading JSON files.
*   API keys for external evaluation LLMs should be managed securely, not checked into version control.

## 5. Data Flow and Orchestration

The primary data flow for a single test run within `RunnerCore.run_test_suite()` is:

1.  `RunnerCore` selects Hardware Profile, Model Config, Test Case.
2.  `ConfigLoader` provides details for these selections.
3.  `EnvironmentManager` applies hardware simulation constraints.
4.  `ModelManager` initializes/verifies the target model (via LM Studio).
5.  `TemplateEngine` processes the relevant prompt template using `test_case['variables']`.
6.  `MetricsCollector` starts monitoring.
7.  `TestExecutor` runs the main inference task using the LM Studio API.
8.  *(If validation task)* `EvaluationEngine.validate_result` is called:
    *   It uses `TemplateEngine` for each validation stage prompt.
    *   It calls the *edge* LLM via `TestExecutor` for each stage's inference.
    *   It parses results and aggregates.
9.  *(If evaluation proxy task)* `EvaluationEngine.evaluate_with_llm_proxy` is called:
    *   It uses the `anthropic` Python library.
    *   It calls the *external SOTA LLM API* (Claude).
    *   It parses results.
10. `MetricsCollector` stops monitoring.
11. `RunnerCore` collects all outputs (generation, validation, evaluation, metrics, token counts) into a single result dictionary.
12. `ResultLogger` saves the result dictionary.
13. `EnvironmentManager` resets constraints.

## 6. Results and Logging

*   **Raw Results:** Individual test run results are saved by `ResultLogger` into `data/raw/{suite_id}_{timestamp}/` as both individual JSON files and appended to `all_results.jsonl`.
*   **Processed Results:** `scripts/analyze_results.py` reads the raw JSONL file(s), performs aggregation (e.g., grouping by model/hardware, calculating means/stds), and saves processed dataframes to CSV files in `data/processed/`.
*   **Figures:** `scripts/render_figures.py` reads the processed CSV files and generates plots (`.png`) saved to `figures/`.
*   **Logging:** Initialize in `runner_cli.py` using `logging.basicConfig` with format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`. Modules use `logging.getLogger(...)`. Log informative messages at INFO level and detailed debug information at DEBUG level.

## 7. Analysis and Visualization (`/scripts` modules)

*   `scripts/analyze_results.py`: Load the raw `all_results.jsonl` using `pandas`, perform groupby operations, calculate aggregates (mean, std, pass rates), and save results to CSV files in `data/processed/`. Mirror the analysis needed for the `analysis_targets` in the test suite specs. Acts as the "ResultsAnalyzer".
*   `scripts/render_figures.py`: Implement functions using `matplotlib` and `seaborn` to load the processed CSVs and generate the specific plots (bar, line, scatter) defined in the `analysis_targets`. Save figures to the `figures/` directory.

## 8. Getting Started / Execution

*   **Dependencies:** `requirements.txt` must include `psutil`, `python-dotenv`, `openai>=1.0.0`, `anthropic>=0.20.0`. Make `pynvml` optional.
*   **Environment:** Strongly recommend using a Python virtual environment (`venv` or `conda`).
*   **Entry Point:** `runner/runner_cli.py` handles CLI arguments (`--config`, `--output`, `--log-level`, `--mock-models`, `--lm-studio-url`). Initializes and runs `RunnerCore`.
*   **Execution Script:** `scripts/run_all.sh` provides a convenience wrapper to run multiple test suites sequentially and trigger analysis/rendering afterwards.

## 9. Phase 2 Considerations (For Phase 1 Design)

While implementing Phase 1, keep the following in mind for easier Phase 2 extension:

*   **Modularity:** Design components (classes) with clear, single responsibilities.
*   **Interfaces:** Define clear inputs/outputs for key methods.
*   **Configuration-Driven:** Rely on configuration files rather than hardcoding parameters.
*   **Extensibility:** Consider how new validation stages, models, hardware profiles, or adaptation logic might be added later. For example, `EvaluationEngine` might need methods to load/use human feedback data in Phase 2. `ModelManager` might need to support different inference backends.

## 10. Optional Enhancements (Beyond Phase 1 Scope)

*   **Dockerfile:** Define for reproducible environment.
*   **CI/CD:** Basic checks (linting, config validation).
*   **Unit Tests:** Stub tests for core utilities (`pytest`).
