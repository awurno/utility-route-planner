FROM ghcr.io/osgeo/gdal:ubuntu-small-3.7.0

ARG POETRY_VERSION=1.7.0
    # python
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=${POETRY_VERSION} \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_NO_INTERACTION=1 \
    # make poetry install to this location
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=0

# prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt update \
    && apt install --no-install-recommends -y \
        python3-distutils \
        pip \
    && apt clean

RUN apt update \
    && apt install --no-install-recommends -y \
       # deps for installing poetry
        curl \
        # deps for building python deps
        build-essential \
        vim \
        gcc \
    && apt clean

# install poetry - respects $POETRY_VERSION & $POETRY_HOME \
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy only required packages list to cache them in docker layer
WORKDIR /home/appuser/app
COPY ../pyproject.toml poetry.lock ./

# Export requirements file, install them.
RUN poetry export -f requirements.txt --with linting --without-hashes --output requirements.txt \
     && pip install -r requirements.txt

# Creating folders, and files for a project:
COPY ../src ./src
COPY ../tests ./tests
COPY ../data/examples ./data/examples
COPY ../*.py .

RUN groupadd -r appgroup && useradd -r -g appgroup appuser && mkdir ./data/processed && mkdir /home/appuser/data && chown appuser -R /home/appuser
# will become mountpoint of our code
USER appuser
