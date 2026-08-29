FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
# Bundle the sample watchlist into the image for the demo
COPY sample_watchlist.csv .
CMD ["python", "server.py"]
