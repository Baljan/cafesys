#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	ALTER ROLE $POSTGRES_USER SET client_encoding TO 'utf8'; 
	ALTER ROLE $POSTGRES_USER SET default_transaction_isolation TO 'read committed'; 
	ALTER ROLE $POSTGRES_USER SET timezone TO 'UTC'; 
	GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
	CREATE SCHEMA IF NOT EXISTS heroku_ext;
EOSQL

pg_restore --exit-on-error --verbose --no-acl --no-owner -U $POSTGRES_USER -d $POSTGRES_DB /docker-entrypoint-initdb.d/latest.dump

echo "Done :)"
