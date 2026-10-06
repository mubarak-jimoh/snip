FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY snip ./snip

# Run as a normal user, not root
RUN useradd --create-home snip && mkdir -p /app/instance && chown -R snip /app
USER snip

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
