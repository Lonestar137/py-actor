FROM docker.io/python3.12

RUN apt update && apt install -y vim git && \
	pip install xoscar
