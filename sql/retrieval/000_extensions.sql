-- Runs once when Docker initializes a new, empty database volume.
-- Application tables and later schema migrations are separate steps.
CREATE EXTENSION IF NOT EXISTS vector;
