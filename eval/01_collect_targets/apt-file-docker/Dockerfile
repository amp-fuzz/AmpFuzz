FROM ubuntu:20.10
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -qq apt-file
RUN apt-file update
ENTRYPOINT ["apt-file"]
