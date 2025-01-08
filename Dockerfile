# Use an official Python runtime as a parent image
FROM python:3.12.4-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make ports available to the world outside this container
EXPOSE 5000 8000

# Define environment variable for frontend
ENV FLASK_APP=./frontend/app.py

# By default, only run the frontend
CMD ["flask", "run", "--host=0.0.0.0"]
