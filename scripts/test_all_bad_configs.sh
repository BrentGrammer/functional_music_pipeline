#!/bin/bash
set -e

echo "Generating Chaos Monkey JSON files..."
python scripts/generate_chaos_monkey_files.py

echo "Running validation checks..."
FAILED_VALIDATION=0

for config in compositions/chaos_monkey/*.json; do
    echo "Testing $config"
    # We want this to fail. If it succeeds (returns 0), the validation leaked.
    if python main.py --composition-file "$config" --output-name dummy --output-format wav > /dev/null 2>&1; then
        echo "❌ VALIDATION FAILURE: $config actually parsed and succeeded!"
        FAILED_VALIDATION=1
    else
        echo "✅ Passed: $config correctly threw an error."
    fi
done

if [ "$FAILED_VALIDATION" -eq 1 ]; then
    echo "Chaos Monkey test FAILED: Some invalid configurations through."
    exit 1
else
    echo "Chaos Monkey test SUCCESS: All invalid configurations were blocked."
    exit 0
fi
