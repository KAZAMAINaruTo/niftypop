#!/usr/bin/env python
# -*- coding: utf-8 -*-
import email
import email.parser
import nifpass
import logging
import poplib
import sqlite3
import sys
import nifpass

DATABASE_FILE = './nifmail.db'
MAX_SHIFT = 1000
# BIG_MAIL_SIZE_THRESHOLD = 200000
BIG_MAIL_SIZE_THRESHOLD = 0


class Nifpop(object):
    def __init__(self, popinfo:nifpass.PopServerInfo):
        self.popinfo = popinfo
        self.init_logging()

    def init_logging(self):
        log = logging.getLogger()
        if not log.handlers:
            log.addHandler(logging.StreamHandler(sys.stdout))
        log.level = log.setLevel(10)


    def check_login(self):
        log = logging.getLogger()
        try:
            M = poplib.POP3(self.popinfo.pop_server)
            log.info(M.user(self.popinfo.account))
            log.info(M.pass_(self.popinfo.get_pass()))
        finally:
            log.info(M.quit())


    def GetMailList(self, start_pos=1):
        log = logging.getLogger()
        with sqlite3.connect(DATABASE_FILE) as conn:
            strSQL = '''
SELECT COUNT(*) FROM MAIL_LIST;
'''
            fetch_start_pos = None
            cur =  conn.execute(strSQL)
            fetch_start_pos = cur.fetchone()[0]
            if not fetch_start_pos:
                fetch_start_pos = 1

            strSQL_richInfo = '''
INSERT OR REPLACE INTO MAIL_LIST(
        uid, size, order_num
        , subject, mail_from, mail_date)
    VALUES(?, ?, ?, ?, ?, ?);
'''
            strSQL_clearOrderNum = '''
UPDATE mail_list
    SET
        order_num = NULL
    WHERE
        uid <> ?
        AND order_num = ?;
'''

            strSQL_updateOrderNum = '''
UPDATE mail_list
    SET
        order_num = ?
    WHERE
        uid = ?
        AND (
            order_num <> ?
            OR order_num IS NULL);
'''
            try:
                M = poplib.POP3(self.popinfo.pop_server)
                log.info(M.user(self.popinfo.account))
                log.info(M.pass_(self.popinfo.get_pass()))
                n = int(M.stat()[0])
                nInserted = 0
                if fetch_start_pos > n:
                    fetch_start_pos = n + 1
                for order_num in range(start_pos, fetch_start_pos):
                    try:
                        uid = M.uidl(order_num).decode().split()[2]
                    except Exception as ex:
                        log.error(ex)
                        break
                    conn.execute(strSQL_clearOrderNum,
                                (uid, order_num))
                    conn.execute(strSQL_updateOrderNum,
                                (order_num, uid, order_num))
                    nInserted += 1
                    if nInserted >= 1000:
                        log.info(order_num)
                        conn.commit()
                        nInserted = 0
                if fetch_start_pos < start_pos:
                    fetch_start_pos = start_pos
                for order_num in range(fetch_start_pos, n + 1):
                    try:
                        mail_size = int(M.list(order_num).decode().split()[2])
                    except Exception as ex:
                        log.error(ex.message)
                        break
                    mail_header_raw = M.top(order_num, 0)[1]
                    fp = email.parser.BytesFeedParser()
                    [fp.feed(x + b'\r\n') for x in mail_header_raw]
                    msg = fp.close()
                    if msg['Subject'] is None:
                        mail_subject = ''
                    else:
                        try:
                            mail_subject = str(email.header.make_header(
                                            email.header.decode_header(
                                                msg['Subject'])))
                        except Exception:
                            print('Subject Decode Error: uid=', uid,
                                ' order_num=', order_num)
                            mail_subject = ''
                        try:
                            mail_from = str(email.header.make_header(
                                    email.header.decode_header(
                                        msg['From'])))
                        except Exception:
                            print('From Decode Error: uid=', uid,
                                ' order_num=', order_num)
                            mail_from = ''
                    mail_date = msg['Date']
                    uid = msg['X-UIDL']
                    conn.execute(strSQL_clearOrderNum,
                            (uid, order_num))
                    conn.execute(
                        strSQL_richInfo,
                        (uid, mail_size, order_num,
                        mail_subject,
                        mail_from,
                        mail_date))
                    nInserted += 1
                    if nInserted >= 1000:
                        log.info(order_num)
                        conn.commit()
                        nInserted = 0
                if nInserted > 0:
                    conn.commit()
            finally:
                log.info(M.quit())


    def PrepareDelete(self):
        log = logging.getLogger()
        with sqlite3.connect(DATABASE_FILE) as cnn:
            strSQL_ToDelete = '''
SELECT TD.uid, ML.order_num
FROM
    mail_to_delete TD
    INNER JOIN mail_list ML
    ON TD.uid = ML.uid
ORDER BY
    ML.order_num desc;
'''
            strSQL_Update = '''
UPDATE MAIL_LIST
    SET
        order_num = ?
    WHERE
        uid =?
'''
            rows = cnn.execute(strSQL_ToDelete).fetchall()
            # print(order_num_check_list)
            try:
                M = poplib.POP3(self.popinfo.pop_server)
                log.info(M.user(self.popinfo.account))
                log.info(M.pass_(self.popinfo.get_pass()))
                for (target_uid, to_order_num) in rows:
                    # print(target_uid, to_order_num)
                    check_min = to_order_num - MAX_SHIFT + 1
                    if check_min < 1:
                        check_min = 1
                    for order_num in range(
                            to_order_num,
                            check_min,
                            -1):
                        uidl = M.uidl(order_num).decode().split()
                        if target_uid == uidl[2]:
                            cnn.execute(strSQL_Update, (uidl[1], target_uid))
                            break
                cnn.commit()
            finally:
                log.info(M.quit())


    def FindUid(self, target_uid):
        log = logging.getLogger()
        strSQL = '''
SELECT order_num FROM MAIL_LIST WHERE mail_id = ?;
'''
        with sqlite3.connect(DATABASE_FILE) as conn:
            cur = conn.execute(strSQL, (target_uid,))
            to_oder_num = cur.fetchone()[0]
            cur.close()
            try:
                M = poplib.POP3(self.popinfo.pop_server)
                log.info(M.user(self.popinfo.account))
                log.info(M.pass_(self.popinfo.get_pass()))
                for order_num in range(
                        to_oder_num - MAX_SHIFT + 1,
                        to_oder_num + 1):
                    uidl = M.uidl(order_num).decode().split()
                    if target_uid == uidl[2]:
                        self.GetMailInfo(uidl[1])
                        break
            finally:
                M.quit()


    def UpdateOrderNum(self, to_oder_num):
        log = logging.getLogger()
        strSQL_Update = '''
UPDATE MAIL_LIST
    SET
        order_num = ?
    WHERE
        uid =?
'''
        with sqlite3.connect(DATABASE_FILE) as conn:
            try:
                M = poplib.POP3(self.popinfo.pop_server)
                log.info(M.user(self.popinfo.account))
                log.info(M.pass_(self.popinfo.get_pass()))
                for i in range(to_oder_num - MAX_SHIFT + 1, to_oder_num + 1):
                    uid = M.uidl(i).decode().split()[2]
                    conn.execute(strSQL_Update, (i, uid))
                    conn.commit()
            finally:
                M.quit()


    def DeleteListedMail(self):
        log = logging.getLogger()
        strSQL = '''
SELECT TD.uid, ML.order_num
    FROM
        mail_to_delete TD
        INNER JOIN mail_list ML
        ON TD.uid = ML.uid
    WHERE
        is_protected = 0;
'''
        f_reset = False
        with sqlite3.connect(DATABASE_FILE) as conn:
            rows = conn.execute(strSQL).fetchall()
            try:
                M = poplib.POP3(self.popinfo.pop_server)
                log.info(M.user(self.popinfo.account))
                log.info(M.pass_(self.popinfo.get_pass()))
                try:
                    for (uid, order_num) in rows:
                        check_uid = M.uidl(order_num).decode().split()[2]
                        if uid != check_uid:
                            log.error("uid is not match. abort. uid: %s check_uid: %s", uid, check_uid)
                            log.info(M.rset())
                            f_reset = True
                            break
                        log.info(M.dele(order_num))

                except Exception:
                    log.error("Error occored. abort.")
                    # log.error()
                    log.info(M.rset())
                    f_reset = True
            finally:
                log.info(M.quit())
            if not f_reset:
                strSQL_copy_to_deleted = '''
INSERT INTO DELETED_MAIL_LIST
    SELECT
        uid
        , size
        , subject
        , mail_from
        , mail_date
        FROM
            mail_list
            INNER JOIN mail_to_delete
            USING (uid);
'''
                conn.execute(strSQL_copy_to_deleted)
                strSQL_remove_deleted_mail = '''
DELETE FROM mail_list
    WHERE uid in (SELECT uid FROM deleted_mail_list);
'''
                conn.execute(strSQL_remove_deleted_mail)
                strSQL_clear_target = '''
DELETE FROM mail_to_delete
    WHERE
        (uid in (SELECT uid FROM deleted_mail_list))
        AND (uid not in (SELECT uid FROM mail_list));
'''
                conn.execute(strSQL_clear_target)
                conn.commit()
                self.renum_mail_order()


    def renum_mail_order(self):
        with sqlite3.connect(DATABASE_FILE) as conn:
            strSQL_create_temp_table1 = '''
CREATE TEMPORARY TABLE gen_new_mail_order
AS
    SELECT
            uid
            , order_num
        FROM
            mail_list
        ORDER BY
            order_num
;
'''
            conn.execute(strSQL_create_temp_table1)
            strSQL_create_temp_table2 = '''
CREATE TEMPORARY TABLE new_mail_order
AS
    SELECT
        uid
        , rowid AS new_order_num
    FROM
        gen_new_mail_order
    WHERE
        order_num != rowid
;
'''
            conn.execute(strSQL_create_temp_table2)
            strSQL_create_index = '''
CREATE UNIQUE INDEX UQ_uid ON NEW_MAIL_ORDER(uid);
'''
            conn.execute(strSQL_create_index)
            strSQL_update_order_num = '''
UPDATE
        mail_list
    SET
        order_num = (
            SELECT new_order_num
                FROM new_mail_order
                WHERE uid = mail_list.uid)
    WHERE
        order_num != (
            SELECT new_order_num
                FROM new_mail_order
                WHERE uid = mail_list.uid);
'''
            conn.execute(strSQL_update_order_num)
            conn.commit()


    def GetMailInfo(self, order_num):
        log = logging.getLogger()        
        try:
                M = poplib.POP3(self.popinfo.pop_server)
                log.info(M.user(self.popinfo.account))
                log.info(M.pass_(self.popinfo.get_pass()))
                mail_size = M.list(order_num).decode().split()[2]
                mail_header_raw = M.top(order_num, 0)[1]
        finally:
            M.quit()
        fp = email.parser.BytesFeedParser()
        [fp.feed(x + b'\r\n') for x in mail_header_raw]
        msg = fp.close()
        if msg['Subject'] is None:
            mail_subject = ''
        else:
            mail_subject = str(email.header.make_header(
                            email.header.decode_header(
                                msg['Subject'])))
        mail_from = str(email.header.make_header(
                        email.header.decode_header(msg['From'])))
        mail_date = msg['Date']
        mail_uidl = msg['X-UIDL']
        print(mail_subject)
        print(mail_from)
        strSQL = '''
INSERT OR REPLACE INTO MAIL_LIST(
        uid, size, order_num, subject, mail_from, mail_date)
    VALUES(?, ?, ?, ?, ?, ?);
'''
        with sqlite3.connect(DATABASE_FILE) as conn:
            conn.execute(strSQL,
                        (mail_uidl, mail_size, order_num,
                        mail_subject, mail_from, mail_date))
            conn.commit()


# if __name__ == '__main__':
#    main()
