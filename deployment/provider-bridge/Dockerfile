FROM python:3.13-alpine
RUN apk add --no-cache ffmpeg
COPY bridge.py /bridge.py
COPY actor_publication.py /actor_publication.py
EXPOSE 9210
ENTRYPOINT ["python3", "/bridge.py"]
