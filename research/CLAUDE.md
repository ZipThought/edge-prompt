# EdgePrompt Development Guidelines for Claude

This document provides specific guidance for Claude when working with the EdgePrompt research codebase. Always review this document at the beginning of sessions to ensure consistent, effective work with this project.

## Path Management

1. **Always use absolute paths, never relative paths** in commands and code:
   - ✅ Use `$HOME/edge-prompt/research/configs/test_suites/ab_test_suite.json`
   - ❌ Avoid `configs/test_suites/ab_test_suite.json`

2. **Check for the existence of directories before referencing them** using the LS tool.

3. **Use the Glob tool for exploratory searching** rather than trying multiple possible paths.

## Environment Setup

1. **Run all commands from the research directory**:
   ```bash
   cd $HOME/edge-prompt/research
   ./run_test.sh
   ```

2. **Use the provided shell scripts** for standard operations:
   - `./run_test.sh` - Run with real API keys
   - `./run_with_mock.sh` - Run without API calls

3. **API keys are available in `.env`** and automatically loaded by the scripts.

4. **The EdgePrompt Python environment** uses a venv that is activated by the scripts automatically.

## Testing Practices

1. **Follow the testing strategy from IMPLEMENTATION_PLAN.md** which involves:
   - Environment setup
   - Test execution
   - Results analysis
   - Error handling validation

2. **Use the log level flags appropriately**:
   ```bash
   ./run_test.sh --log-level DEBUG
   ```

3. **When analyzing test results**, check for:
   - Topic consistency across runs
   - Metrics data
   - Validation results
   - Token usage

4. **Results are saved to the specified output directory** (default: `data/validation_test`).

## Meta-Dialectical Approach

When encountering complex issues or making important design decisions, apply the Meta-Dialectical Methodology:

1. **Establish the initial thesis** (proposed solution)
2. **Apply devil's advocate challenge** to identify assumptions and weaknesses
3. **Steelman the original thesis** to strengthen it against criticism
4. **Develop a synthetic reconciliation** that addresses the strongest criticisms
5. **Verify symbolic integrity** to ensure consistent meaning of terms
6. **Project across contexts** to test how the solution performs in different situations
7. **Evaluate or iterate** until a robust solution is found

This approach is particularly valuable for complex issues like the topic inconsistency problem.

## Code Structure

1. **Core modules live in `runner/`**:
   - `runner_core.py` - Main orchestration
   - `model_manager.py` - Model interaction
   - `template_engine.py` - Prompt template processing
   - `evaluation_engine.py` - Multi-stage validation
   - `constraint_enforcer.py` - Content constraint checking
   - `result_logger.py` - Results logging and storage
   - `config_loader.py` - Configuration loading

2. **Configuration files in `configs/`**:
   - `model_configs.json` - CloudLLM and EdgeLLM model definitions
   - `templates/` - Prompt templates
   - `test_suites/` - Test configurations

3. **Results stored in `data/`**:
   - JSON output files with detailed run information
   - Log files with execution traces

## Terminology

Always use the current terminology in code and discussions:

- CloudLLM 
- EdgeLLM
- Four-run framework (Runs 1-4)

## Four-Run Structure

Understand the four runs and their purposes:

1. **Run 1 (Cloud Baseline)**: CloudLLM with SingleTurn_Direct method
2. **Run 2 (Cloud EdgePrompt)**: CloudLLM with MultiTurn_EdgePrompt method
3. **Run 3 (Edge Baseline)**: EdgeLLM with SingleTurn_Direct method
4. **Run 4 (Edge EdgePrompt)**: EdgeLLM with MultiTurn_EdgePrompt method

When analyzing issues, consider how they affect each run differently.

## Critical Areas for Improvement

Based on the TEST_RESULTS.md, focus on these critical areas:

1. **Topic Control in Baseline Runs** (HIGHEST PRIORITY):
   - Ensure consistent context propagation across all runs
   - Add verification steps to confirm topic consistency

2. **Template Standardization**:
   - Create default values for required template variables
   - Handle missing variables gracefully
   - Update templates with all necessary fields

3. **Validation System Robustness**:
   - Improve JSON structure for reliable parsing
   - Add fallback mechanisms for parsing failures
   - Simplify validation sequence for EdgeLLM models

4. **Token Optimization**:
   - Reduce validation sequence complexity
   - Implement progressive validation
   - Optimize template design

## Batch Processing

Always use the Batch tool when making multiple related tool calls, such as:
- Reading multiple files
- Making multiple edits to the same file
- Running multiple commands for status checking

## Documentation

When making significant changes:

1. **Update implementation documentation** in the relevant files
2. **Add comments for complex logic**
3. **Update IMPLEMENTATION_PLAN.md with progress**
4. **Create detailed test results documentation** like TEST_RESULTS.md

## Apply Meta-Dialectical Methodology

When solving complex issues like the topic inconsistency problem:

1. **Clearly articulate the initial approach**
2. **Systematically identify potential weaknesses**
3. **Strengthen the approach against these critiques**
4. **Develop a synthetic solution that resolves the core tensions**
5. **Test the solution across multiple contexts**
6. **Document both the process and the outcome**

This methodology ensures robust solutions that have survived meaningful challenge.