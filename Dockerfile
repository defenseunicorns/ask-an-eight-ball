FROM python:3.9.18

WORKDIR /app

COPY . .
RUN pip install -r requirements.txt

CMD ["python", "main.py"]
EXPOSE 8002