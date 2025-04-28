# AI Content Automation - Testing Guide

This guide explains how to run tests for the AI Content Automation project to verify that all components are working correctly.

## Overview

The testing framework includes:

1. **Unit Tests** - Tests for individual agent components
2. **Integration Tests** - End-to-end tests for the complete content pipeline
3. **Test Runner Script** - A script to run all tests and report results
4. **Pipeline Runner Tool** - A CLI tool to manually run the content pipeline
5. **Performance Metrics** - Tools for measuring agent performance

## Prerequisites

Before running tests, make sure you have:

1. Set up the Python environment with all dependencies: `pip install -r requirements.txt`
2. Set up environment variables in `.env`:
   ```
   DATABASE_URL=postgresql://username:password@localhost/test_ai_content
   GOOGLE_API_KEY=your_google_api_key
   REDIS_URL=redis://localhost:6379/0
   ```
3. Created a test database: `createdb test_ai_content`

## Running Tests

### Using the Test Runner Script

The easiest way to run all tests is using the test runner script:

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Run with verbose output
python run_tests.py -v
```

### Running Tests with Pytest Directly

You can also run tests directly with pytest:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_agents/test_research_agent.py

# Run with verbose output
pytest -v tests/
```

## Test Components

### Unit Tests

Unit tests verify that each agent works correctly in isolation:

- `test_research_agent.py` - Tests for the Research Agent
- `test_content_agent.py` - Tests for the Content Agent
- `test_visual_agent.py` - Tests for the Visual Agent
- `test_atomization_agent.py` - Tests for the Atomization Agent
- `test_distribution_agent.py` - Tests for the Distribution Agent

### Integration Tests

Integration tests verify that the entire pipeline works end-to-end:

- `test_content_pipeline.py` - Tests the full content creation and distribution flow

### Performance Metrics

All tests collect performance metrics that are saved to the `test_results` directory for analysis. The metrics include:

- Total duration for each pipeline step
- Breakdown of time spent in each agent
- Detailed timing for individual operations

## Pipeline Runner Tool

The project includes a CLI tool for manually running the content pipeline:

```bash
# Run the full pipeline with a specific topic
python tools/pipeline_runner.py --topic "AI in healthcare 2025"

# Run a portion of the pipeline starting from a specific point
python tools/pipeline_runner.py --start-point content --item-id 123

# Specify social media platforms
python tools/pipeline_runner.py --topic "AI trends" --platforms linkedin twitter

# Specify visual types
python tools/pipeline_runner.py --topic "AI trends" --visual-types chart quote_card
```

## Troubleshooting

If tests are failing, check the following:

1. **Database Connection** - Ensure your database is running and accessible
2. **API Keys** - Verify that your Google API key is valid
3. **Dependencies** - Make sure all required packages are installed
4. **Mocks** - Some tests use mocks for external services; verify these are working

For detailed error information, run tests with the `-v` flag.

## Extending Tests

When adding new features to the project, remember to:

1. Add unit tests for new components
2. Update integration tests to include new functionality
3. Update mocks for any new external dependencies
4. Add performance metrics for new operations

## Getting Test Results

Test results are outputted in two forms:

1. Console output showing pass/fail status
2. Performance metrics exported to JSON files in `test_results/`

You can analyze the JSON files to identify performance bottlenecks and optimization opportunities.