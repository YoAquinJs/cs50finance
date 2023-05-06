## Database Setup
---
The project uses a sqlite3 database, there are 4 tablesk, all tables are linked to the users table, this is the schema:

### Users

This table stores users, Schema:
```
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL,
    hash TEXT NOT NULL,
    cash NUMERIC NOT NULL DEFAULT 10000.00);
```

### Stocks

This table stores stocks linked to the users table, Schema:
```
CREATE TABLE stocks (
    user_id INTEGER NOT NULL,
    stock TEXT NOT NULL,
    shares INT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id));
```

### Transactions

This table stores stock movements linked to the users table, Schema:
```
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    shares INTEGER NOT NULL,
    price FLOAT NOT NULL, 
    buy_price FLOAT NOT NULL DEFAULT 0,
    selled INTEGER NOT NULL DEFAULT 0,
    analisys BIT DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(id))
```

### Funds

This table stores fund movements linked to the users table, Schema:
```
CREATE TABLE funds (
    user_id INTEGER NOT NULL,
    amount FLOAT NOT NULL,
    timestamp DATETIME NOT NULL, 
    alias TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id))
```