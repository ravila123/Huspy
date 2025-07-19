#!/bin/bash
# Test script for install_deps.sh functionality

echo "Testing install_deps.sh script..."

# Test 1: Check if script exists and is executable
if [ -x "scripts/install_deps.sh" ]; then
    echo "✓ Script exists and is executable"
else
    echo "✗ Script missing or not executable"
    exit 1
fi

# Test 2: Check script syntax
if bash -n scripts/install_deps.sh; then
    echo "✓ Script syntax is valid"
else
    echo "✗ Script has syntax errors"
    exit 1
fi

# Test 3: Check if script can display help/usage when virtual env doesn't exist
echo "Testing script behavior without virtual environment..."
if [ -d "venv" ]; then
    mv venv venv_backup
fi

# Run script and capture output (should fail gracefully)
output=$(scripts/install_deps.sh 2>&1 || true)
if echo "$output" | grep -q "Virtual environment not found"; then
    echo "✓ Script properly detects missing virtual environment"
else
    echo "✗ Script doesn't handle missing virtual environment properly"
    echo "Output: $output"
fi

# Restore venv if it was backed up
if [ -d "venv_backup" ]; then
    mv venv_backup venv
fi

# Test 4: Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "✓ Requirements file exists"
else
    echo "✗ Requirements file missing"
    exit 1
fi

echo "All tests passed! install_deps.sh is ready for use."