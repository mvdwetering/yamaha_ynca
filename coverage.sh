#!/bin/sh
pytest
mypy custom_components  --check-untyped-defs
