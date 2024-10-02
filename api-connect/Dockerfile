# Use the official Python image from the Docker Hub
FROM python:3.12.6-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app/

# Expose the port that the Flask app will run on
EXPOSE 5508

# Command to run the Flask app
CMD ["python3", "server.py"]