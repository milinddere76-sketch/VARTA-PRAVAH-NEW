FROM alpine:latest
LABEL Name="vartapravah" Version="0.0.1"
RUN apk add --no-cache fortune-mod
CMD ["fortune", "-a"]
