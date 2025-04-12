# EdgePrompt Research Pipeline: Implementation Guidance

## 1. Introduction

**Purpose:** This document provides detailed implementation guidance for generating the **Phase 1** Python codebase for the EdgePrompt research framework. The goal is to create a system capable of executing the experiments defined in `docs/specifications/PROMPT_ENGINEERING.md` (referred to as "the Spec") to empirically validate the core methodology presented in the EdgePrompt paper (Syah et al.).

**Target Audience:** AI code generation tools and human developers responsible for implementing the research framework.

**Scope:** This guide focuses solely on the **Phase 1** requirements outlined in the Spec. Phase 2 features (system adaptation, human evaluation, etc.) should be considered for architectural extensibility but are **not** to be implemented at this stage.

**Language:** The implementation shall be in **Python 3.10+**.

**Core Methodology:** The framework validates EdgePrompt's **prompt-engineering-only** approach, using structured prompts and multi-stage validation without model fine-tuning.

**Target Directory:** The resulting codebase should reside within the `/research` directory of the main project, potentially replacing or significantly refining any existing code there.

**Reference Specification:** All implementation details must align with `docs/specifications/PROMPT_ENGINEERING.md`. This document translates that spec into more concrete implementation directives.

## 2. Target Directory Structure

The implementation should follow this structure within the `/research` directory:

```
research/
├── configs/                  # JSON configurations (loaded by ConfigLoader)
│   ├── hardware_profiles.json
│   ├── model_configs.json
│   ├── templates/
│   │   └── *.json            # Template definitions (Tc, As, R', v_i)
│   └── test_suites/
│       └── *.json            # Test suite specifications
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
│   ├── analyze_results.py    # Processes raw data -> processed data
│   ├── render_figures.py     # Generates plots from processed data
│   └── run_all.sh            # Script to run all test suites
├── notebooks/                # (Optional) Jupyter notebooks for debugging/analysis
├── requirements.txt          # Python dependencies
└── README.md                 # Description of the research module
```

## 3. Core Component Implementation (`/runner` modules)

Implement the following Python classes, corresponding to the components defined in the Spec (Sec 1 & 2). Ensure classes have clear responsibilities, type hinting, logging, and robust error handling.

### 3.1. `ConfigLoader` (`runner/config_loader.py`)

*   **Responsibility:** Load and validate JSON configuration files (test suites, hardware profiles, model configs, templates). Resolve relative paths.
*   **Key Methods:**
    *   `__init__(config_path)`: Takes path to the main test suite config.
    *   `load_test_suite()`: Loads the main suite JSON, validates basic structure (required fields from Spec Sec 4), and attempts to load referenced hardware/model configs (using other methods). Returns a dictionary.
    *   `load_hardware_profile(profile_id)`: Loads the specific hardware profile JSON from `configs/hardware_profiles.json`. Returns a dict or None.
    *   `load_model_config(model_id)`: Loads the specific model config JSON from `configs/model_configs.json`. Returns a dict or None.
    *   `load_template(template_name)`: Loads a specific template JSON from `configs/templates/`. Returns a dict or None.
*   **Implementation Notes:** Use Python's `json` library. Handle `FileNotFoundError` and `JSONDecodeError` gracefully. Resolve paths relative to the `configs/` directory.

### 3.2. `ModelManager` (`runner/model_manager.py`)

*   **Responsibility:** Manage LLM loading, initialization, and caching. Abstract different model backends (initially support simulation/mock, then add e.g., `llama-cpp-python` or `transformers`). Implements parts of Spec Algo 2.5.
*   **Key Methods:**
    *   `__init__(model_cache_dir)`: Set up model caching location.
    *   `initialize_model(model_id, model_config)`: Loads model weights (potentially downloading/simulating download if not cached), applies basic quantization (as per `model_config`), moves to device (CPU initially, GPU if available/configured). Returns a model object (or mock object). Handle potential loading errors.
    *   `unload_model(model_id)`: Releases model from memory/cache.
    *   `get_model_info(model_id)`: Returns details about a configured model.
*   **Implementation Notes:** For Phase 1, a mock model returning predictable outputs is acceptable for testing the pipeline structure. Implementations for actual backends (like `llama.cpp`) should be added later but designed for. Use a dictionary to cache loaded models (`self.loaded_models`).

### 3.3. `TemplateEngine` (`runner/template_engine.py`)

*   **Responsibility:** Process templates by substituting variables and encoding basic constraints. Implements Spec Algo 2.2.
*   **Key Methods:**
    *   `__init__(template_dir)`: Optional directory for templates.
    *   `load_template(template_name)`: Loads template JSON (can delegate to `ConfigLoader`).
    *   `process_template(template, variables)`: Performs variable substitution (e.g., using regex `\[([a-zA-Z_]+)\]`) and basic constraint appending/formatting based on template type. Perform basic whitespace optimization. Raise `ValueError` if required variables are missing. Returns the processed prompt string.
    *   `extract_template_variables(template)`: Utility to list variables in a template pattern.
*   **Implementation Notes:** Focus on correct substitution and basic constraint formatting (e.g., appending "CONSTRAINTS:" section). Advanced optimizations are Phase 2.

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

*   **Responsibility:** Execute a single LLM inference task (generation or validation stage). Implements the core inference part of Spec Algo 2.5.
*   **Key Methods:**
    *   `execute_test(model, prompt, generation_params)`: Takes an initialized model object (from `ModelManager`), a processed prompt string, and generation parameters. Calls the model's generation method (e.g., `model.generate(...)`). Returns a dictionary containing the raw output text, token counts (if available from model/tokenizer), and execution time (can be measured here or passed from `MetricsCollector`).
*   **Implementation Notes:** This class focuses purely on the inference call. It does *not* handle metrics collection or hardware simulation itself (those wrap around calls to this).

### 3.7. `EvaluationEngine` (`runner/evaluation_engine.py`)

*   **Responsibility:** Perform multi-stage validation and proxy LLM evaluation. Implements Spec Algo 2.3 and 2.6.
*   **Key Methods:**
    *   `validate_result(question, answer, validation_sequence, edge_llm_engine_func)`: Implements the multi-stage loop (Algo 2.3). Takes the question/answer, the loaded validation sequence definition, and a *function* (or callable object) that represents the `TestExecutor.execute_test` interface (to run the validation prompts on the edge LLM). Uses `TemplateEngine` to process each stage's prompt. Parses the structured JSON output from each stage's LLM response robustly (handle errors, retries). Aggregates results, score, and feedback. Returns the final `validation_result` dictionary.
    *   `evaluate_with_llm_proxy(content_to_evaluate, reference_criteria, evaluation_role, evaluation_llm_config)`: Implements the proxy evaluation (Algo 2.6). Constructs the prompt. Uses an API client (e.g., `openai`, `anthropic` libraries) to call the specified SOTA LLM. Parses the structured JSON response robustly. Returns the `evaluation_result` dictionary.
*   **Implementation Notes:** Robust JSON parsing from LLM responses is critical. Implement retry logic or default values for failed parsing. Ensure interaction with external APIs (for proxy eval) handles network errors and API key management (via configuration).

### 3.8. `ResultLogger` (`runner/result_logger.py`)

*   **Responsibility:** Save individual and aggregate results to the filesystem. Aligns with Spec Sec 6.1.
*   **Key Methods:**
    *   `__init__(output_dir)`: Set the base output directory.
    *   `log_result(result_dict)`: Saves a single test run dictionary to two places: an individual timestamped JSON file and appended as a single line to `all_results.jsonl` within a run-specific subdirectory (e.g., `data/raw/{suite_id}_{timestamp}/`).
    *   `log_aggregate_results(analysis_summary, suite_id)`: Saves the final analysis summary dictionary (from `RunnerCore`) to a summary JSON file in the run-specific subdirectory.
*   **Implementation Notes:** Ensure run-specific subdirectories are created under `data/raw/`. Use Python's `json` library. Handle file I/O errors. Append to JSONL safely.

### 3.9. `RunnerCore` (`runner/runner_core.py`)

*   **Responsibility:** Orchestrate the entire test suite execution. Implements Spec Algo 2.7 (Phase 1).
*   **Key Methods:**
    *   `__init__(config_path, output_dir, log_level)`: Initialize all other components (`ConfigLoader`, `ModelManager`, `TemplateEngine`, etc.).
    *   `run_test_suite()`: The main execution loop.
        1.  Loads the test suite using `ConfigLoader`.
        2.  Iterates through specified `hardware_profiles`.
        3.  Iterates through specified `models`.
        4.  Iterates through `test_cases` in the suite.
        5.  For each combination:
            *   Use `EnvironmentManager` context manager (`with em.apply(profile):`) to configure/reset the environment.
            *   Use `ModelManager` to initialize the required model.
            *   Use `TemplateEngine` to process the necessary template(s) with `test_case['variables']`.
            *   Use `MetricsCollector` to start/stop timing and resource monitoring around the core task(s).
            *   Use `TestExecutor` to run the primary generation task.
            *   If needed by the test case/suite:
                *   Use `EvaluationEngine.validate_result` (passing `TestExecutor.execute_test` as the engine func) for multi-stage validation.
                *   Use `EvaluationEngine.evaluate_with_llm_proxy` for proxy evaluation.
            *   Consolidate all results (generation, validation, evaluation, metrics, config info) into a result dictionary.
            *   Use `ResultLogger` to save the individual result.
            *   Use `ModelManager` to unload model if necessary (optional optimization).
        6.  After all loops, calculate aggregate summary statistics.
        7.  Use `ResultLogger` to save the aggregate summary.
        8.  Return the aggregate summary.
*   **Implementation Notes:** This class ties everything together. Implement clear logging for each step. Handle exceptions within the loops gracefully to allow the suite to continue if one test case fails.

## 4. Configuration Handling

*   All configurations (hardware, models, templates, test suites) reside as JSON files within the `/research/configs` directory.
*   `ConfigLoader` is responsible for loading these files.
*   API keys for external evaluation LLMs should be managed securely, ideally via environment variables or a `.env` file (loaded using `python-dotenv`), not checked into version control. `ConfigLoader` or `EvaluationEngine` should read these.

## 5. Data Flow and Orchestration

The primary data flow for a single test run within `RunnerCore.run_test_suite()` is:

1.  `RunnerCore` selects Hardware Profile, Model Config, Test Case.
2.  `ConfigLoader` provides details for these selections.
3.  `EnvironmentManager` applies hardware simulation constraints.
4.  `ModelManager` loads/initializes the target edge LLM.
5.  `TemplateEngine` processes the relevant prompt template using `test_case['variables']`.
6.  `MetricsCollector` starts monitoring.
7.  `TestExecutor` runs the main inference task (e.g., generation) using the model and processed prompt.
8.  *(If validation task)* `EvaluationEngine.validate_result` is called:
    *   It uses `TemplateEngine` for each validation stage prompt.
    *   It calls the *edge* LLM via `TestExecutor` for each stage's inference.
    *   It parses results and aggregates.
9.  *(If evaluation proxy task)* `EvaluationEngine.evaluate_with_llm_proxy` is called:
    *   It uses `TemplateEngine` for the evaluation prompt.
    *   It calls the *external SOTA LLM API*.
    *   It parses results.
10. `MetricsCollector` stops monitoring.
11. `RunnerCore` collects all outputs (generation, validation, evaluation, metrics) into a single result dictionary.
12. `ResultLogger` saves the result dictionary.
13. `EnvironmentManager` resets constraints.

## 6. Results and Logging

*   **Raw Results:** Individual test run results are saved by `ResultLogger` into `data/raw/{suite_id}_{timestamp}/` as both individual JSON files and appended to `all_results.jsonl`.
*   **Processed Results:** `scripts/analyze_results.py` reads the raw JSONL file(s), performs aggregation (e.g., grouping by model/hardware, calculating means/stds), and saves processed dataframes to CSV files in `data/processed/`.
*   **Figures:** `scripts/render_figures.py` reads the processed CSV files and generates plots (`.png`) saved to `figures/`.
*   **Logging:** Use Python's standard `logging` module. Configure via `runner_cli.py` (or `RunnerCore`). Log informative messages at INFO level and detailed debug information at DEBUG level. Include timestamps, module names, and log levels.

## 7. Analysis and Visualization (`/scripts` modules)

*   `scripts/analyze_results.py`: Implement functions to load the raw `all_results.jsonl` using `pandas`, perform groupby operations, calculate aggregates (mean, std, pass rates), and save results to CSV files in `data/processed/`. Mirror the analysis needed for the `analysis_targets` in the test suite specs.
*   `scripts/render_figures.py`: Implement functions using `matplotlib` and `seaborn` to load the processed CSVs and generate the specific plots (bar, line, scatter) defined in the `analysis_targets`. Save figures to the `figures/` directory.

## 8. Getting Started / Execution

*   **Dependencies:** List all required Python packages in `requirements.txt`. Include `psutil` and `pynvml` as optional (or handle their absence gracefully).
*   **Environment:** Strongly recommend using a Python virtual environment (`venv` or `conda`).
*   **Entry Point:** `runner/runner_cli.py` serves as the command-line interface. It uses `argparse` to handle arguments (`--config`, `--output`, `--log-level`).
*   **Execution Script:** `scripts/run_all.sh` provides a convenience wrapper to run multiple test suites sequentially and trigger analysis/rendering afterwards.

## 9. Phase 2 Considerations (For Phase 1 Design)

While implementing Phase 1, keep the following in mind for easier Phase 2 extension:

*   **Modularity:** Design components (classes) with clear, single responsibilities.
*   **Interfaces:** Define clear inputs/outputs for key methods.
*   **Configuration-Driven:** Rely on configuration files rather than hardcoding parameters.
*   **Extensibility:** Consider how new validation stages, models, hardware profiles, or adaptation logic might be added later. For example, `EvaluationEngine` might need methods to load/use human feedback data in Phase 2. `ModelManager` might need to support different inference backends.

---
This document provides the necessary blueprint to generate the Phase 1 Python code for the EdgePrompt research framework, ensuring alignment with the high-level specification and enabling the collection of data required for the paper.
