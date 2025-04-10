# Use Python 3.13.2 as the base image
FROM python:3.13.2-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port that Gradio will run on
EXPOSE 7860

# Command to run the application
CMD ["python", "app.py"] 