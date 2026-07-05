FROM public.ecr.aws/lambda/python:3.12

# Install uv from the published image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Resolve and install runtime dependencies into the task root. uv sync does not
# support installing into an arbitrary target, so export the locked runtime
# requirements and install those.
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project --no-editable -o /tmp/requirements.txt \
    && uv pip install --no-cache --target "${LAMBDA_TASK_ROOT}" -r /tmp/requirements.txt

# Copy application source and migration assets.
COPY lexagent/ ${LAMBDA_TASK_ROOT}/lexagent/
COPY scripts/ ${LAMBDA_TASK_ROOT}/scripts/
COPY alembic.ini ${LAMBDA_TASK_ROOT}/
COPY migrations/ ${LAMBDA_TASK_ROOT}/migrations/

# Default handler; migration and seed Lambdas override the CMD.
CMD ["lexagent.api.handler.lambda_handler"]
