FROM alpine:edge

RUN mkdir /src
WORKDIR /src

ENV DJANGO_SETTINGS_MODULE=cafesys.settings.production \
    PYTHONPATH=/src:/src/cafesys:$PYTHONPATH \
    PYTHONUNBUFFERED=true

COPY ./requirements.alpine.txt /src/requirements.alpine.txt
# Installs packages and adds system CA cert directory to OpenLDAP config
RUN apk add --no-cache $(grep -vE "^\s*#" /src/requirements.alpine.txt | tr "\n" " ") && \
    echo "TLS_CACERTDIR /etc/ssl/certs" > /etc/openldap/ldap.conf && \
    pip install -U pip setuptools

COPY ./requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt

COPY . /src

RUN DJANGO_SECRET_KEY=build DJANGO_DATABASE_URL=sqlite://// DJANGO_REDIS_URL=redis:// DJANGO_EMAIL_URL=consolemail:// django-admin.py collectstatic --noinput

EXPOSE 80
CMD ["/src/run-django.sh"]
