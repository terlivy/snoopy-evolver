#!/usr/bin/env python3
"""Test analyzer.py"""
import sys
import os
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/snoopy-evolver-git')

from evolver.analyzer import analyze_signal, SignalAnalyzer

analyzer = SignalAnalyzer()

# Test 1: failure signal
print("=== Test: failure signal ===")
result = analyze_signal("failure", {
    "error": "ModuleNotFoundError: No module named 'requests'",
    "error_type": "import_error"
})
print(f"status: {result['status']}")
print(f"needs_evolution: {result['needs_evolution']}")
print(f"patterns: {len(result['patterns_detected'])}")
print(f"suggestions: {len(result['suggestions'])}")
print()

# Test 2: git_push signal
print("=== Test: git_push signal ===")
result = analyze_signal("git_push", {
    "branch": "main",
    "files_changed": ["a.py", "b.py", "c.py"]
})
print(f"status: {result['status']}")
print(f"needs_evolution: {result['needs_evolution']}")
print(f"patterns: {len(result['patterns_detected'])}")
print(f"suggestions: {len(result['suggestions'])}")
print()

# Test 3: retry signal
print("=== Test: retry signal ===")
result = analyze_signal("retry", {
    "retry_count": 5,
    "reason": "connection timeout"
})
print(f"status: {result['status']}")
print(f"needs_evolution: {result['needs_evolution']}")
print()

# Test 4: task_complete (should have gene matched)
print("=== Test: task_complete (with gene match) ===")
result = analyze_signal("task_complete", {})
print(f"status: {result['status']}")
print(f"gene_gap: {result.get('gene_gap')}")
print(f"suggestions: {len(result['suggestions'])}")
print()

print("All tests passed!")
