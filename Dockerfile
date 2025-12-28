FROM python:3.11-slim

LABEL maintainer="aigremont"
LABEL description="Corrade Inventory Sorter - Sort Second Life inventory via Corrade HTTP API"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY inventory_sorter.py .
COPY config.example.json .
COPY rules.example.json .

# Create volume mount points for config
VOLUME ["/app/config"]

# Default to help output
ENTRYPOINT ["python", "inventory_sorter.py"]
CMD ["--help"]

