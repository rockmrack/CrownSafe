# Use official Python base image (small & secure)
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /usr/src/app

# Prevents Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install pip dependencies separately for better Docker caching
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all API code into the container
COPY . .

# Expose the default FastAPI port
EXPOSE 8000

# Start the FastAPI app using Uvicorn
CMD ["uvicorn", "api.main_babyshield:app", "--host", "0.0.0.0", "--port", "8000"]
