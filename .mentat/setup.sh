#!/bin/bash
set -eufx -o pipefail

curl -sSL https://install.python-poetry.org | \
    POETRY_HOME=/opt/poetry \
    POETRY_VERSION=2.1.1 \
    python3 -

POETRY_VIRTUALENVS_IN_PROJECT=true /opt/poetry/bin/poetry install
