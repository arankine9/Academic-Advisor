# PostgreSQL Setup Guide for macOS

## Option 1: Install PostgreSQL using Homebrew (Recommended)

1. Install Homebrew if you don't have it already:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Install PostgreSQL:
```bash
brew install postgresql@15
```

3. Start PostgreSQL service:
```bash
brew services start postgresql@15
```

4. Create a database for your application:
```bash
createdb academic_advisor
```

## Option 2: Install PostgreSQL using the official installer

1. Download the PostgreSQL installer from the official website:
   https://www.postgresql.org/download/macosx/

2. Follow the installation instructions.

3. Start PostgreSQL service:
```bash
pg_ctl -D /usr/local/var/postgres start
```

4. Create a database for your application:
```bash
createdb academic_advisor
```

## Option 3: Use Docker

1. Install Docker Desktop for Mac if you don't have it already:
   https://www.docker.com/products/docker-desktop/

2. Run PostgreSQL in a Docker container:
```bash
docker run --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15
```

3. Create a database for your application:
```bash
docker exec -it postgres createdb -U postgres academic_advisor
```

## Updating your .env file

After installing PostgreSQL, update your .env file with the correct connection string:

```
# For local PostgreSQL installation (Options 1 and 2)
DATABASE_URL=postgresql://localhost/academic_advisor

# For Docker installation (Option 3)
DATABASE_URL=postgresql://postgres:postgres@localhost/academic_advisor
```

## Testing your PostgreSQL connection

After setting up PostgreSQL, you can test the connection with:

```bash
psql -d academic_advisor
```

This should open the PostgreSQL command line interface. Type `\q` to exit.

## Troubleshooting

If you encounter issues with PostgreSQL:

1. Make sure the PostgreSQL service is running:
```bash
# For Homebrew installation
brew services list

# For standard installation
pg_ctl status -D /usr/local/var/postgres
```

2. Check if you can connect to PostgreSQL:
```bash
psql -U postgres
```

3. If you get a "role postgres does not exist" error, create the postgres user:
```bash
createuser -s postgres
```

4. If you get a "peer authentication failed" error, you may need to update your pg_hba.conf file to use md5 authentication instead of peer. 