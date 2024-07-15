# Copyright IBM Corp. 2024
#
FROM python:3

#give ARG MAXIMO_SERVER_ENV a default value
ARG MAXIMO_SERVER_ENV

#assign the $MAXIMO_SERVER_ENV arg to the MAXIMO_SERVER_ENV ENV so that it can be accessed
#by the subsequent RUN call within the container
ENV MAXIMO_SERVER_ENV $MAXIMO_SERVER_ENV

USER root

#
WORKDIR /code

#
COPY ./requirements.txt /code/requirements.txt

#
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#
COPY ./src/app /code

USER 1001

#
CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8000"]