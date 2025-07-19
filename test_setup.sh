#!/bin/bash

# Simple test script to validate setup.sh functionality
echo "Testing setup.sh functionality..."

# Test 1: Check if setup.sh exists and is executable
if [ -x "./setup.sh" ]; then
    echo "✓ setup.sh exists and is executable"
else
    echo "✗ setup.sh is not executable"
    exit 1
fi

# Test 2: Check if setup.sh has environment detection functions
if grep -q "detect_system" setup.sh && grep -q "detect_python" setup.sh; then
    echo "✓ Environment detection functions present"
else
    echo "✗ Environment detection functions missing"
    exit 1
fi

# Test 3: Check if setup.sh has virtual environment creation
if grep -q "create_virtual_environment" setup.sh; then
    echo "✓ Virtual environment creation function present"
else
    echo "✗ Virtual environment creation function missing"
    exit 1
fi

# Test 4: Check if setup.sh has error handling
if grep -q "handle_error" setup.sh && grep -q "trap.*ERR" setup.sh; then
    echo "✓ Error handling mechanisms present"
else
    echo "✗ Error handling mechanisms missing"
    exit 1
fi

# Test 5: Check if setup.sh has system dependency detection
if grep -q "check_system_dependencies" setup.sh && grep -q "install_system_packages" setup.sh; then
    echo "✓ System dependency detection present"
else
    echo "✗ System dependency detection missing"
    exit 1
fi

echo ""
echo "All tests passed! setup.sh appears to be correctly implemented."