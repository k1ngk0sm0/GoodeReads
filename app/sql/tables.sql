CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(320) UNIQUE NOT NULL,
    pass_hash VARCHAR NOT NULL,
    updates BOOLEAN
);

CREATE TABLE books (
    isbn  VARCHAR(13) PRIMARY KEY,
    title VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    year INTEGER NOT NULL
);

CREATE TABLE reviews (
    user_id INTEGER,
    isbn VARCHAR(13) NOT NULL,
    rating INTEGER,
    review VARCHAR NOT NULL
);
