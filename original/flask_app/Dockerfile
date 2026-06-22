# SECURITY FINDING: Full Python image (large attack surface vs slim/alpine)
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# SECURITY FINDING: Running as root (Container Platform SRG / V-205072)
# SECURITY FINDING: Exposes debug port, debug=True in app
EXPOSE 5000

CMD ["python", "app.py"]
