FROM alpine:3.4

RUN mkdir /src
WORKDIR /src

ENV DJANGO_SETTINGS_MODULE=cafesys.settings.production \
    PYTHONPATH=/src:$PYTHONPATH \
    PYTHONUNBUFFERED=true

COPY ./requirements.alpine.txt /src/requirements.alpine.txt
RUN apk add --no-cache $(grep -vE "^\s*#" /src/requirements.alpine.txt | tr "\n" " ")

COPY ./requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt

COPY . /src

CMD ["/src/run-django.sh"]
