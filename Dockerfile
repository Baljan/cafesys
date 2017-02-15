FROM alpine:3.5

RUN mkdir /app
WORKDIR /app

ENV DJANGO_SETTINGS_MODULE=cafesys.settings.production \
    PYTHONPATH=/app:/app/cafesys:$PYTHONPATH \
    PYTHONUNBUFFERED=true

COPY ./requirements.alpine.txt /app/requirements.alpine.txt
# Installs packages and adds system CA cert directory to OpenLDAP config
RUN apk add --no-cache $(grep -vE "^\s*#" /app/requirements.alpine.txt | tr "\n" " ") && \
    echo "TLS_CACERTDIR /etc/ssl/certs" > /etc/openldap/ldap.conf && \
    pip install -U pip setuptools

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app

RUN DJANGO_SECRET_KEY=build DJANGO_DATABASE_URL=sqlite://// DJANGO_REDIS_URL=redis:// DJANGO_EMAIL_URL=consolemail:// django-admin.py collectstatic --noinput

EXPOSE 80
ENTRYPOINT ["/app/bin/entrypoint"]
CMD ["/app/bin/run-django"]
