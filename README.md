&& apt-get install -y --no-install-recommends --allow-downgrades \
    bzip2 \
    ca-certificates \
    curl \
    libexpat1 \
    libldap-common \
    libpam0g \
    libpq5 \
    libxml2 \
    libxmlsec1 \
    libxmlsec1-openssl \
    libxslt1.1 \
    python3 \
    python3.12-venv \
    tini \
    unit \
    unit-python3.12 \
&& apt-get upgrade -y libxml2 libxslt1.1 \
&& apt-get clean \
