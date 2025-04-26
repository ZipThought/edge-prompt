# EdgePrompt Refactoring Implementation Plan

This document outlines the specific changes needed to align the codebase with the revised Phase 1 experimental design specified in `docs/specifications/PROMPT_ENGINEERING.md`.

## Overview

The key changes involve:
1. Rename terminology (LLM-L/LLM-S to CloudLLM/EdgeLLM) ✅
2. Refactor the test execution to implement the four-run structure ✅
3. Update configuration files to use the new terminology ✅
4. Modify the result structure to store data according to the new run organization ✅
5. Set up Run 1 as the Phase 1 Proxy Reference for evaluation ✅

## Implementation Tasks

### 1. Configuration File Updates

#### 1.1. `configs/model_configs.json` ✅
- Rename top-level keys:
  - `"llm_l_models"` → `"cloud_llm_models"` ✅
  - `"llm_s_models"` → `"edge_llm_models"` ✅

#### 1.2. `configs/test_suites/ab_test_suite.json` ✅
- Modify the `models` object:
  - Rename `"llm_l"` → `"cloud_llm"` ✅
  - Rename `"llm_s"` → `"edge_llm"` ✅
- Change A/B test structure to use the four run organization:
  - Replace `scenario_a_variants` section with a `run_parameters` section that defines specific parameters for each run ✅
  - Update `analysis_targets` to reflect comparisons between Run 1-4, especially Run 4 vs Run 3 ✅

### 2. Python Module Updates

#### 2.1. `runner/config_loader.py` ✅
- Modify `load_model_config`:
  - Update references to look in `"cloud_llm_models"` and `"edge_llm_models"` in model_configs.json ✅
  - Update logging messages to use the new terminology ✅

#### 2.2. `runner/model_manager.py` ✅
- Rename methods for clarity:
  - `initialize_llm_l` → `initialize_cloud_llm` ✅
  - `initialize_llm_s` → `initialize_edge_llm` ✅
  - `execute_llm_l` → `execute_cloud_llm` ✅
  - `execute_llm_s` → `execute_edge_llm` ✅
- Update internal references and logging to use the CloudLLM/EdgeLLM terminology ✅

#### 2.3. `runner/runner_core.py` ✅
- Major refactoring required:
  - Replace internal uses of "LLM-L"/"LLM-S" with "CloudLLM"/"EdgeLLM" ✅
  - Update method calls to renamed ModelManager methods ✅
  - Rewrite `run_test_suite` to use the 4-run structure instead of Scenario A/B ✅
  - Replace `_run_scenario_a` and `_run_scenario_b` with methods for the four runs: ✅
    - `_run_cloud_baseline` (SingleTurn_Direct with CloudLLM) ✅
    - `_run_cloud_edgeprompt` (MultiTurn_EdgePrompt with CloudLLM) ✅
    - `_run_edge_baseline` (SingleTurn_Direct with EdgeLLM) ✅
    - `_run_edge_edgeprompt` (MultiTurn_EdgePrompt with EdgeLLM) ✅
  - Modify result structure to store data under `run_1`, `run_2`, `run_3`, `run_4` keys ✅
  - Set up quality/agreement metrics calculation in reference to Run 1 ✅

#### 2.4. `runner/result_logger.py` ✅
- Update `log_result` to handle the new nested result structure with run_1 through run_4 ✅

#### 2.5. Other Supporting Files
- Update `constraint_enforcer.py`, `evaluation_engine.py` and other modules for consistency

### 3. Implementation Order 

1. Begin with updating `model_configs.json` to use the new terminology ✅
2. Update `config_loader.py` to work with the new configuration structure ✅
3. Refactor `model_manager.py` to use the new method names and terminology ✅
4. Create a new ab_test_suite.json file with the revised structure ✅
5. Refactor `runner_core.py` to use the 4-run structure ✅
6. Update `result_logger.py` to handle the new result structure ✅
7. Make consistency updates throughout the remaining modules

### 4. Testing Strategy

After implementing the changes:
1. Run a small test case end-to-end
2. Verify the structure of the output JSONL file
3. Check that each run (1-4) executes correctly
4. Validate that Run 1 results are properly used as reference for comparing Run 3 and Run 4

## Completed Refactoring

The implementation of the four-run structure is now complete:

1. Configuration files have been updated with the new terminology and structure:
   - `configs/model_configs.json` now uses `cloud_llm_models` and `edge_llm_models`
   - `configs/test_suites/ab_test_suite.json` now uses the four-run structure with `run_parameters`

2. Core modules have been refactored:
   - `config_loader.py` loads models from the correct sections
   - `model_manager.py` uses the new method names and executes models correctly
   - `result_logger.py` handles the new result structure with run_1 through run_4
   - `runner_core.py` has been completely rewritten to implement the four-run structure

3. The new structure implements:
   - Run 1: CloudLLM executor with SingleTurn_Direct method (baseline reference)
   - Run 2: CloudLLM executor with MultiTurn_EdgePrompt method
   - Run 3: EdgeLLM executor with SingleTurn_Direct method
   - Run 4: EdgeLLM executor with MultiTurn_EdgePrompt method (target improvement)

4. Placeholder for quality metrics comparing against Run 1 (reference) has been added

## Next Steps

1. Update the analysis scripts to process the new result structure
2. Test the implementation with a small end-to-end test case
3. Verify the output JSONL structure is correct
4. Test the system with both mock mode and real API calls
5. Implement detailed quality/agreement metrics calculation in the analysis phase

## Run Methods Structure

The four run methods have been implemented in `runner_core.py`:

```python
def _run_cloud_baseline(self, test_case, cloud_llm_model_data):
    """
    Execute Run 1 (Cloud Baseline):
    CloudLLM executor with SingleTurn_Direct method.
    """
    # Generate simple question, simulate student answer, evaluate, and enforce constraints
    pass

def _run_cloud_edgeprompt(self, test_case, cloud_llm_model_data, validation_sequence_id):
    """
    Execute Run 2 (Cloud EdgePrompt):
    CloudLLM executor with MultiTurn_EdgePrompt method.
    """
    # Generate structured question with constraints, simulate student answer, 
    # perform multistage validation, enforce constraints, and review if needed
    pass

def _run_edge_baseline(self, test_case, edge_llm_model_data):
    """
    Execute Run 3 (Edge Baseline):
    EdgeLLM executor with SingleTurn_Direct method.
    """
    # Generate simple question, simulate student answer, evaluate, and enforce constraints
    # Quality compared to Run 1 reference in analysis phase
    pass

def _run_edge_edgeprompt(self, test_case, edge_llm_model_data, validation_sequence_id):
    """
    Execute Run 4 (Edge EdgePrompt):
    EdgeLLM executor with MultiTurn_EdgePrompt method.
    """
    # Generate structured question with constraints, simulate student answer, 
    # perform multistage validation, enforce constraints
    # Quality compared to Run 1 reference in analysis phase
    pass
```

## Result Structure

The new result structure includes quality metrics compared to Run 1 (reference):

```json
{
  "id": "run_123",
  "timestamp": "2025-04-26T12:34:56.789Z",
  "test_case_id": "simple_math_question",
  "cloud_llm_model_id": "gpt-4o",
  "edge_llm_model_id": "gemma-3-4b-it",
  "hardware_profile": "sim_unconstrained",
  "input_stimulus": {...},
  "run_1": {
    "output": "...",
    "status": "completed",
    "steps": {...},
    "final_decision": {...},
    "total_metrics": {...}
  },
  "run_2": {
    "output": "...",
    "status": "completed",
    "steps": {...},
    "final_decision": {...},
    "total_metrics": {...},
    "quality_vs_ref": {...}
  },
  "run_3": {
    "output": "...",
    "status": "completed",
    "steps": {...},
    "final_decision": {...},
    "total_metrics": {...},
    "quality_vs_ref": {...}
  },
  "run_4": {
    "output": "...",
    "status": "completed",
    "steps": {...},
    "final_decision": {...},
    "total_metrics": {...},
    "quality_vs_ref": {...}
  }
}
```