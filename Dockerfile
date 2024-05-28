# Use the official Python image from the Docker Hub
FROM python:latest

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Add a non-root user
# Add a non-root user with no home directory and no shell access
#RUN addgroup --gid 1001 --system app && \
#    adduser --no-create-home --shell /bin/false --disabled-password --uid 1001 --system --group app


# Set work directory
#WORKDIR /sss

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Change ownership of staticfiles directory to non-root user
#RUN mkdir -p /sss/staticfiles && chown -R app:app /sss/staticfiles

# Change to the non-root user
#USER app

RUN python manage.py makemigrations
RUN python manage.py migrate

# Run the Django server
CMD ["python", "manage.py", "runserver", "--insecure"]

