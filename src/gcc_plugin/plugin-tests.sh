#!/bin/bash

function inspect_output() {
    RESULT=0

    diff $1/output $1/expected | grep -E "<|>" &> /dev/null

    if [ $? -eq 0 ]; then
	echo "FAILED: " $1
	RESULT=1
    else
	echo "PASSED: " $1
    fi

    return $RESULT
}

inspect_output $1
