FROM postgres:18

COPY db_init.sql /docker-entrypoint-initdb.d/

EXPOSE $POSTGRES_PORT

CMD ["postgres"]