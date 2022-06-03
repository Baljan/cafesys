FROM node:alpine AS nodedeps
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM python:3.9

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

COPY --from=nodedeps /app/node_modules ${APP_ROOT}/node_modules

RUN pip3 install -U pip setuptools

COPY ./requirements.txt ${APP_ROOT}/requirements.txt
RUN pip3 install --ignore-installed -r ${APP_ROOT}/requirements.txt

COPY . ${APP_ROOT}

RUN django-admin compilescss
RUN django-admin collectstatic --noinput

EXPOSE 80
# It seems there's no way to do variable substitution here.
CMD ["/app/bin/run-django"]
