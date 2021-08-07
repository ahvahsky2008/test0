FROM python:3.6
EXPOSE 5000
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app
CMD python app.py