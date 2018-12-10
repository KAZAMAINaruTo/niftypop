CREATE TABLE IF NOT EXISTS mail_list(
    uid TEXT PRIMARY KEY
    , size INTEGER
    , order_num INTEGER
    , subject TEXT
    , mail_from TEXT
    , mail_date TEXT
    , is_protected INTEGER NOT NULL DEFAULT 0);
    

CREATE INDEX IF NOT EXISTS mail_list_order_num ON mail_list(order_num);

CREATE TABLE IF NOT EXISTS deleted_mail_list(
    uid TEXT PRIMARY KEY
    , size INTEGER
    , order_num INTEGER
    , subject TEXT
    , mail_from TEXT
    , mail_date TEXT);

CREATE TABLE IF NOT EXISTS mail_to_delete(
	uid TEXT PRIMARY KEY);
	

