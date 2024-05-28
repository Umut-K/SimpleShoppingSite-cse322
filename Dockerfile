FROM ubuntu:latest
LABEL authors="umutk"

ENTRYPOINT ["top", "-b"]