FROM alpine:3.6

# Kept separate to be substituted in next step
ENV APP_ROOT=/app
ENV DJANGO_SETTINGS_MODULE=cafesys.settings.production \
    PYTHONPATH=${APP_ROOT}:${PYTHONPATH} \
    PYTHONUNBUFFERED=true

# Build-only environment variables
ARG DJANGO_DATABASE_URL=sqlite:////
ARG DJANGO_DEBUG=False
ARG DJANGO_EMAIL_URL=consolemail://
ARG DJANGO_REDIS_URL=redis://
ARG DJANGO_SECRET_KEY=build

RUN mkdir ${APP_ROOT}
WORKDIR ${APP_ROOT}

COPY ./requirements.alpine.txt ${APP_ROOT}/requirements.alpine.txt
RUN apk add --no-cache $(grep -vE "^\s*#" ${APP_ROOT}/requirements.alpine.txt | tr "\n" " ") && \
    pip3 install -U pip setuptools

COPY ./requirements.txt ${APP_ROOT}/requirements.txt
RUN pip3 install -r ${APP_ROOT}/requirements.txt

COPY . ${APP_ROOT}

RUN django-admin compilescss
RUN django-admin collectstatic --noinput

EXPOSE 80
# It seems there's no way to do variable substitution here.
CMD ["/app/bin/run-django"]
