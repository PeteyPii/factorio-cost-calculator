FROM python:3.13
WORKDIR /code
RUN pip install --no-cache-dir --upgrade pydantic fastapi[standard] gravis simplejson
COPY . /code/
CMD ["fastapi", "run", "app.py", "--port", "80"]
