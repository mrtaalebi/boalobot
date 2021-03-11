FROM python:3.9-alpine

ENV TZ Asia/Tehran

RUN apk update && apk add bash git openssh make gcc musl-dev postgresql-dev

ENV OCSERV_VERSION 0.11.8
ENV OCSERV_URL ftp://ftp.infradead.org/pub/ocserv/ocserv-$OCSERV_VERSION.tar.xz

RUN buildDeps=" \
        curl \
        g++ \
        gnutls-dev \
        gpgme \
        libev-dev \
        libnl3-dev \
        libseccomp-dev \
        linux-headers \
        linux-pam-dev \
        lz4-dev \
        make \
        readline-dev \
        tar \
        xz \
    "; \
    set -x \
    && apk add --update --virtual .build-deps $buildDeps \
    && curl -SL $OCSERV_URL -o ocserv.tar.xz \
    && curl -SL $OCSERV_URL.sig -o ocserv.tar.xz.sig \
    && gpg --keyserver pgp.mit.edu --recv-key 7F343FA7 \
    && gpg --keyserver pgp.mit.edu --recv-key 96865171 \
    && gpg --verify ocserv.tar.xz.sig \
    && mkdir -p /usr/src/ocserv \
    && tar -xf ocserv.tar.xz -C /usr/src/ocserv --strip-components=1 \
    && rm ocserv.tar.xz* \
    && cd /usr/src/ocserv \
    && ./configure \
    && make \
    && make install \
    && mkdir -p /etc/ocserv \
    && cp /usr/src/ocserv/doc/sample.config /etc/ocserv/ocserv.conf \
    && cd / \
    && rm -rf /usr/src/ocserv \
    && runDeps="$( \
        scanelf --needed --nobanner /usr/local/sbin/ocserv \
            | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
            | xargs -r apk info --installed \
            | sort -u \
        )" \
    && apk add --virtual .run-deps $runDeps gnutls-utils iptables \
    && apk del .build-deps \
    && rm -rf /var/cache/apk/*

RUN mkdir -p /app
COPY . /app
COPY ./config/ocserv.conf /etc/ocserv/
WORKDIR /app

RUN make dependencies

CMD ["sh", "-c", "python3 -m boalo"] 
