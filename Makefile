# Makefile for Academic Advisor

.PHONY: setup install db pinecone run lint clean

# Setup environment and install dependencies
setup: install db pinecone

# Install dependencies
install:
	pip install -r requirements.txt

# Setup database
db:
	python scripts/init_db.py

# Setup Pinecone
pinecone:
	python scripts/pinecone_setup.py
	python scripts/ingest_majors.py

# Run application
run:
	python backend/main.py

# Lint code
lint:
	flake8 backend

# Clean up
clean:
	rm -rf __pycache__
	rm -rf backend/__pycache__
	rm -rf backend/*/__pycache__