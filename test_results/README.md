# Test Results Directory

This directory stores performance metrics and test results generated during test runs.

## Files

- `pipeline_metrics_*.json` - Performance metrics for complete pipeline runs
- `agent_metrics_*.json` - Detailed metrics for individual agent operations

## How to Use

These files can be analyzed to:

1. Identify performance bottlenecks in the pipeline
2. Track performance changes over time
3. Optimize the most time-consuming operations

## Example Analysis

You can use Python to analyze the metrics files:

```python
import json
import glob
import matplotlib.pyplot as plt

# Load the latest metrics file
latest_file = max(glob.glob('test_results/pipeline_metrics_*.json'), key=os.path.getctime)
with open(latest_file, 'r') as f:
    metrics = json.load(f)

# Extract durations by agent
agent_durations = {}
for run_id, run_data in metrics.items():
    agent = run_data['agent']
    duration = run_data['duration']
    
    if agent not in agent_durations:
        agent_durations[agent] = 0
    agent_durations[agent] += duration

# Plot results
plt.figure(figsize=(10, 6))
plt.bar(agent_durations.keys(), agent_durations.values())
plt.title('Time Spent by Agent')
plt.ylabel('Seconds')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('agent_performance.png')
```

This directory is automatically created and populated when running tests with the performance metrics enabled.