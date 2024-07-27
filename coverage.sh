#!/bin/sh
pytest --cov=custom_components/yamaha_ynca tests/ --cov-report term-missing --cov-report html
mypy custom_components  --check-untyped-defs --enable-incomplete-feature=NewGenericSyntax
