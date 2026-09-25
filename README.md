# Introduction
This repository is made as a way to learn about Python, FastAPI and other libraries. It is a simple API that allows you to create, read, update and delete laboratorial exams like blood works.

## For Boot.dev
As an alumni of [Boot.dev](https://www.boot.dev), I am using this repository to complet the personal project in the Backend path.

## For FastAPI
This project is based on the [FastAPI](https://fastapi.tiangolo.com/) framework. I am learning this framework by following - with adaptations - the [tutotiral of Corey Schafer](https://www.youtube.com/playlist?list=PL-osiE80TeTsak-c-QsVeg0YYG_0TeyXI) on YouTube.

## Database
The database used is PostgreSQL, the ORM used is SQLAlchemy and alembic as the migration controller.

### DB Set up
- run the compose.yaml file

`docker-compose up`

- setup the Postgres database

`psql -U postgres`

- Create an user

`CREATE USER examuser WITH PASSWORD 'exampass';`
- exit the postgres database

`\q`
- Create a DB

`createdb -U postgres -O examuser exam`

## AWS Servecis
Here I am using the boto3 to access AWS services. The cloud solution will be used to save images nad PDF apart of the project. As this is a learn space **no aws account where created or used**