
CREATE TABLE IF NOT EXISTS deleted_boards (board TEXT PRIMARY KEY NOT NULL);
CREATE TABLE IF NOT EXISTS channels (
 board TEXT NOT NULL, name TEXT NOT NULL, name_search TEXT NOT NULL, created_at TEXT NOT NULL, timestamp INTEGER NOT NULL, author TEXT NOT NULL,
 PRIMARY KEY(board,name)
);
CREATE TABLE IF NOT EXISTS posts (
 seq INTEGER PRIMARY KEY AUTOINCREMENT,
 board TEXT NOT NULL, id TEXT NOT NULL, channel TEXT NOT NULL, root TEXT NOT NULL,
 author TEXT NOT NULL, timestamp INTEGER NOT NULL, body_search TEXT NOT NULL,
 payload TEXT NOT NULL, request_id TEXT NOT NULL, request TEXT NOT NULL,
 UNIQUE(board,id), UNIQUE(board,request_id)
);
CREATE INDEX IF NOT EXISTS posts_board_channel ON posts(board,channel,seq);
CREATE INDEX IF NOT EXISTS posts_board_channel_timestamp ON posts(board,channel,timestamp,seq);
CREATE INDEX IF NOT EXISTS posts_roots_created ON posts(board,channel,timestamp,seq) WHERE id=root;
CREATE INDEX IF NOT EXISTS posts_board_root ON posts(board,root,seq);
CREATE INDEX IF NOT EXISTS posts_board_root_timestamp ON posts(board,root,timestamp,seq);
CREATE INDEX IF NOT EXISTS posts_board_timestamp ON posts(board,timestamp,seq);
CREATE TABLE IF NOT EXISTS subscriptions (
 board TEXT NOT NULL, target TEXT NOT NULL, agent TEXT NOT NULL,
 PRIMARY KEY(board,target,agent)
);
CREATE TABLE IF NOT EXISTS subscription_opt_outs (
 board TEXT NOT NULL, target TEXT NOT NULL, agent TEXT NOT NULL,
 PRIMARY KEY(board,target,agent)
);