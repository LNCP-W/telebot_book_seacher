FROM python:3.10-slim-buster

WORKDIR /opt/app
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y wget
RUN wget -q https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_100.0.4896.75-1_amd64.deb
RUN apt-get install -y ./google-chrome-stable_100.0.4896.75-1_amd64.deb
RUN apt-get install xvfb -y
RUN apt-get install unzip -y
RUN #apt-get install firefox
COPY requirements.txt /
RUN pip install -r /requirements.txt
COPY . .
CMD python -m main
