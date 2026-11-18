# The image that runs the ServerApp and the ClientApps (Lab 94), from Flower's own base image
FROM flwr/superexec:1.43.0

WORKDIR /app
COPY pyproject.toml .
COPY branch_router branch_router
# Flower is already in the base image, so its line is removed before installing the rest
RUN sed -i 's/.*flwr\[simulation\].*//' pyproject.toml \
    && python -m pip --no-cache-dir install -U .

ENTRYPOINT ["flower-superexec"]
