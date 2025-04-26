# EdgePrompt Refactoring Implementation Plan

## Background & Current State

The EdgePrompt research framework has undergone a significant refactoring to align with the revised Phase 1 experimental design. Key changes implemented include:

1.  **Terminology Update:** Renamed "LLM-L" to "CloudLLM" and "LLM-S" to "EdgeLLM" across the codebase and configurations.
2.  **Four-Run Structure:** Replaced the previous Scenario A/B execution with a four-run structure:
    *   **Run 1:** CloudLLM Baseline (SingleTurn_Direct) - Serves as the quality reference.
    *   **Run 2:** CloudLLM EdgePrompt (MultiTurn_EdgePrompt) - Cloud performance with EdgePrompt method.
    *   **Run 3:** EdgeLLM Baseline (SingleTurn_Direct) - Edge baseline performance.
    *   **Run 4:** EdgeLLM EdgePrompt (MultiTurn_EdgePrompt) - Target method for evaluation.
3.  **Configuration Updates:** `model_configs.json` and `test_suites/ab_test_suite.json` reflect the new terminology and run structure.
4.  **Core Runner Update:** `runner/runner_core.py` now orchestrates the four runs.
5.  **Topic Consistency:** Implemented a shared teacher request mechanism per test case to ensure all four runs address the same topic. This was a critical fix from previous iterations.
6.  **Analysis/Visualization Alignment:** `scripts/analyze_results.py` and `scripts/render_figures.py` have been updated to process the four-run data structure and generate the intended comparison outputs (e.g., Run 4 vs Run 3 for efficiency/safety, Runs 3/4 vs Run 1 for quality).
7.  **Initial Template Robustness:** Basic default value handling was added to `template_engine.py`.
8.  **JSON Utilities:** A `json_utils.py` module was added with functions for more robust JSON extraction and validation. Fallback logic using simplified templates and direct JSON generation was added to `evaluation_engine.py`.

**Current Goal:** Address the remaining critical issues identified in `TEST_RESULTS.md` to achieve reliable data generation for Phase 1, focusing on validating the effectiveness and efficiency of the EdgePrompt method (Run 4) compared to the Edge Baseline (Run 3), using the Cloud Baseline (Run 1) as a reference.

**Remaining Critical Issues (As of Last Review):**

1.  **Validation Robustness (JSON Parsing):** Despite improvements and fallbacks (`json_utils.py`), logs indicate persistent failures in reliably parsing JSON outputs from validation steps, especially from EdgeLLM, but occasionally even from CloudLLM. This corrupts results.
2.  **Token Usage Inefficiency:** Run 4 (EdgePrompt) consumes significantly more tokens than Run 3 (Edge Baseline), primarily due to the multi-stage validation process. This needs optimization for practical edge deployment.
3.  **Template Standardization:** While basic defaults exist, warnings for missing variables still occur, indicating potential inconsistencies or incomplete template definitions.

## Implementation Tasks (Prioritized)

### 1. Validation System Overhaul (Highest Priority)

**Goal:** Achieve near 100% reliability in parsing validation results (passed/score/feedback) from both CloudLLM and EdgeLLM outputs.

**Background:** Unreliable JSON parsing is the primary blocker. Models, especially smaller ones, struggle to adhere strictly to JSON-only output formats when embedded within complex prompts.

**Tasks:**

1.  **Simplify Validation Templates:**
    *   **Action:** Review and aggressively simplify `configs/templates/validation_template.json` and `configs/templates/json_focused_validation_template.json`.
    *   **Rationale:** Reduce cognitive load on the LLM. Remove *all* extraneous text, conversational filler, and complex criteria descriptions within the prompt. Focus solely on the input (Question, Answer) and the required JSON output structure. Use extremely direct instructions like "Output ONLY the following JSON structure: ...".
    *   **File:** `configs/templates/validation_template.json`, `configs/templates/json_focused_validation_template.json`

2.  **Enhance JSON Parsing in `json_utils.py`:**
    *   **Action:** Review and potentially add more robust regex patterns to `extract_json_from_text` to handle variations like missing quotes around keys or boolean values, while being careful not to parse *incorrect* structures. Add logging for which extraction method succeeds.
    *   **Rationale:** Capture more near-miss JSON outputs before resorting to repair or failure.
    *   **File:** `runner/json_utils.py`

3.  **Refine JSON Repair Prompt:**
    *   **Action:** Review the repair prompt generated in `model_manager.py::repair_json_with_llm`'s internal `llm_repair_func`. Make it extremely clear that *only* valid JSON is desired, explicitly mentioning the required keys again.
    *   **Rationale:** Improve the success rate of the LLM-based repair mechanism.
    *   **File:** `runner/model_manager.py` (within `repair_json_with_llm`)

4.  **Add Non-LLM Fallback Parsing:**
    *   **Action:** In `evaluation_engine.py`'s `validate_with_sequence`, if all JSON parsing/repair attempts fail for a validation stage result, implement a final *non-LLM* attempt using regex to extract simple signals directly from the raw `generated_text`. Look for patterns like `passed: true`, `score: 0.8`, `decision: pass`, etc. If found, populate the `stage_result` with these extracted values and default feedback, logging a clear warning that fallback parsing was used.
    *   **Rationale:** Extract *some* result even from complete JSON failure, preventing the entire run from being invalidated due to one malformed validation step, while clearly marking the result as potentially less reliable.
    *   **File:** `runner/evaluation_engine.py`

5.  **Investigate CloudLLM (Run 2) Validation Failures:**
    *   **Action:** Add detailed DEBUG logging within `evaluation_engine.py` specifically before and after the CloudLLM call in `_run_cloud_edgeprompt`'s validation step. Log the exact prompt sent and the raw response received when a parsing error occurs.
    *   **Rationale:** Understand why the high-capability model is failing the JSON task to inform prompt refinement.
    *   **File:** `runner/evaluation_engine.py`, `runner/runner_core.py`

**Confirmation:**
*   Run `run_test.sh --config configs/test_suites/ab_test_suite.json --log-level DEBUG`.
*   Check `runner.log.txt` for *any* JSON parsing errors or warnings (including repair attempts and fallback usage). The goal is zero critical parsing errors that stop validation.
*   Check `all_results.jsonl` to ensure `run_2.steps.multi_stage_validation` and `run_4.steps.multi_stage_validation` consistently contain structured `stageResults` with valid `passed`, `score`, and `feedback` fields.

### 2. Token Optimization (High Priority)

**Goal:** Significantly reduce the token footprint of Run 4 (EdgeLLM EdgePrompt), particularly the validation steps, without sacrificing essential guardrail effectiveness.

**Background:** Current results show Run 4 uses ~5x the tokens of Run 3, largely due to multiple validation LLM calls.

**Tasks:**

1.  **Detailed Token Profiling:**
    *   **Action:** Enhance `evaluation_engine.py`'s `validate_with_sequence` loop to log the `input_tokens` and `output_tokens` for *each individual validation stage* call.
    *   **Rationale:** Pinpoint which validation stages are most token-intensive.
    *   **File:** `runner/evaluation_engine.py`

2.  **Optimize Validation Templates (Brevity):**
    *   **Action:** Revisit validation templates (`validation_template.json`, `json_focused_validation_template.json`) identified in Task 1. Further shorten instructions and context where possible, focusing only on the essential information needed for the specific check.
    *   **Rationale:** Directly reduce input tokens per validation call.
    *   **File:** `configs/templates/validation_template.json`, `configs/templates/json_focused_validation_template.json`

3.  **Consolidate Validation Stages:**
    *   **Action:** Analyze the `basic_validation_sequence.json`. Can checks like 'relevance' and 'accuracy' be combined into a single prompt/LLM call without losing effectiveness? Design and test a new, more concise validation sequence (e.g., `consolidated_validation_sequence.json`).
    *   **Rationale:** Reduce the *number* of LLM calls required for validation.
    *   **File:** Create new file in `configs/templates/`

4.  **Implement Progressive Validation (Early Exit):**
    *   **Action:** Verify that `evaluation_engine.py` strictly adheres to the `abortOnFailure` setting in the validation sequence schema. If a high-priority check (like safety) fails, subsequent lower-priority checks should be skipped.
    *   **Rationale:** Avoid unnecessary token usage on answers already deemed invalid.
    *   **File:** `runner/evaluation_engine.py`

**Confirmation:**
*   Run the test suite using both `basic_validation_sequence` and the new `consolidated_validation_sequence` (update `ab_test_suite.json` to test both if needed).
*   Compare `run_4.total_metrics.total_tokens` between the sequences.
*   Analyze logs for per-stage token counts to verify reduction.
*   Manually review results to ensure the consolidated sequence still catches errors effectively (compare `run_4.final_decision` across sequence types).

### 3. Template Standardization (Medium Priority)

**Goal:** Eliminate warnings about missing template variables and ensure all prompts are generated consistently using defined defaults.

**Background:** While basic defaults were added, some variables used in patterns might still lack defaults in the template definitions.

**Tasks:**

1.  **Audit & Update Template Defaults:**
    *   **Action:** Systematically review *every* template file in `configs/templates/`. For each variable placeholder `[var_name]` found in the `"pattern"`, ensure `var_name` exists as a key within the `"variables"` object in that template file. Provide a sensible default value (even if an empty string `""`). Pay special attention to `direct_constraint_template.json`.
    *   **Rationale:** Guarantees that `template_engine.py` can always find a value (either provided or default) for substitution.
    *   **Files:** All files in `configs/templates/`

2.  **Refine Template Engine Logging:**
    *   **Action:** Modify the logging in `template_engine.py::process_template` to clearly distinguish between: a) using a provided variable, b) using a default variable from the template, and c) a variable in the pattern missing both provided and default values (this case should be eliminated by step 1, but log an ERROR if it occurs).
    *   **Rationale:** Improve debuggability and confirm defaults are working as expected.
    *   **File:** `runner/template_engine.py`

**Confirmation:**
*   Run the test suite with `--log-level DEBUG`.
*   Scrutinize `runner.log.txt` for any template processing warnings or errors. The goal is zero warnings related to missing variables that have defaults defined. Verify DEBUG logs show correct usage of defaults.

## Implementation Order

1.  **Validation System Overhaul:** Fix the core reliability issues first.
2.  **Token Optimization:** Improve efficiency once validation is reliable.
3.  **Template Standardization:** Clean up warnings and ensure consistency.

## Analysis and Documentation

*   **Update Analysis Scripts:** Ensure `analyze_results.py` and `render_figures.py` correctly process and visualize the data generated *after* the validation and token optimizations are complete.
*   **Update Documentation:** Update `IMPLEMENTATION_PLAN.md`, `TEST_RESULTS.md`, and `README.md` to reflect the final state after these tasks are completed. Document the effectiveness of the JSON repair/fallback mechanisms and the achieved token savings.

This plan prioritizes fixing the blocking validation issues, then addresses efficiency, and finally cleans up template handling. Completing these steps should result in a reliable framework capable of generating the necessary data for Phase 1 analysis.
