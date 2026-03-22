FROM alpine

RUN addgroup -S app && adduser -S -G app -u 10001 app

WORKDIR /app
USER 10001:10001

CMD ["echo", "Hello world."]
