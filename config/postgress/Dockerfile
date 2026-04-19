FROM postgres:latest

COPY sql_init.sql /docker-entrypoint-initdb.d/

EXPOSE $POSTGRES_PORT

CMD ["postgres"]