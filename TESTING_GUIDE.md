# AI Content Automation - Testing Guide

This document provides step-by-step instructions for running the testing framework for the AI Content Automation project.

## Setting Up the Testing Environment

1. First, create the necessary directories and files for testing:

```bash
python setup_test_env.py
```

2. Make sure all dependencies are installed:

```bash
pip install -r requirements.txt
```

3. Set up environment variables (if not already in .env file):

```
DATABASE_URL=sqlite:///test.db
GOOGLE_API_KEY=your_api_key_here
REDIS_URL=redis://localhost:6379/0
```

## Running Tests

You can run all tests or specific test groups:

### Run All Tests

```bash
python run_tests.py
```

### Run Unit Tests Only

```bash
python run_tests.py --unit
```

### Run Integration Tests Only

```bash
python run_tests.py --integration
```

### Run With Verbose Output

```bash
python run_tests.py -v
```

## Understanding Test Results

The test output will show:
- Each test group's status (passed or failed)
- Details about any failures
- Total test execution time
- Performance metrics (for integration tests)

Performance metrics are saved to the `test_results` directory as JSON files that can be analyzed to identify bottlenecks in the content pipeline.

## Common Issues and Solutions

### Database Connection Errors

If you see database connection errors:
- Verify your DATABASE_URL environment variable
- Make sure SQLite is installed if using SQLite
- Check database permissions

### API Mock Issues

If tests are failing due to unexpected API responses:
- Check the mocks in `tests/conftest.py`
- Update the mock responses to match the expected format

### SessionError or InvalidRequestError

If you see SQLAlchemy session errors:
- Make sure the test is using the test_db fixture correctly
- Check for conflicting sessions
- Use monkeypatching for db_session.add and commit

## Fixed Issues in This Release

1. **ResearchAgent Issues**
   - Added error handling for JSON parsing in _create_research_plan
   - Fixed mismatch between expected and actual content

2. **Content Agent Process Issues**
   - Added proper session handling to avoid "already attached" errors
   - Fixed test to properly commit objects

3. **Atomization Agent Issues**
   - Fixed LinkedIn content mock to include hashtags
   - Updated test to handle actual social platform content

4. **Distribution Agent Issues**
   - Fixed integrity constraint failure in run_with_posts test
   - Added proper commit order for article and posts

5. **Updated Mock Gemini Client**
   - Added more comprehensive mock responses
   - Fixed JSON format for chart and infographic responses

## Continuous Testing Improvements

As the project evolves, continue to update the test suite by:

1. **Updating Mocks** - Keep the mock responses up to date with actual API changes
2. **Adding Edge Cases** - Test failure scenarios and edge cases
3. **Improving Performance Metrics** - Enhance the metrics to provide more detailed insights
4. **Automating Tests** - Set up CI/CD pipelines to run tests automatically

By following these practices, the test suite will provide reliable feedback about the system's functionality and performance.