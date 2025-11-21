# Use a small official Python image
FROM python:3.10-slim

# Set working directory in container
WORKDIR /app

# Copy only dependency files first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port that Flask will use
EXPOSE 5000

# Use environment variable to tell Flask the entrypoint if needed
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Default command to run the app
CMD ["python", "app.py"]

# Use a small official Python image
FROM python:3.10-slim

# Set working directory in container
WORKDIR /app

# Copy only dependency files first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port that Flask will use
EXPOSE 5000

# Use environment variable to tell Flask the entrypoint if needed
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Default command to run the app
CMD ["python", "app.py"]
