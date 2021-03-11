FROM python:3.9-alpine

ENV TZ Asia/Tehran

RUN apk update && apk add bash git openssh make gcc musl-dev postgresql-dev

RUN mkdir -p /app
COPY . /app
WORKDIR /app

RUN make dependencies

CMD ["sh", "-c", "python3 -m boalo"] 
