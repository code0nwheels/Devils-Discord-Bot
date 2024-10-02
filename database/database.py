import aiosqlite
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

class Database:
    def __init__(self):
        self.conn = None
        logging.basicConfig(level=logging.INFO)
        self.log = logging.getLogger(__name__)
        # Add a rotating handler
        handler = RotatingFileHandler('log/db.log', maxBytes=5*1024*1024, backupCount=5)
        # Create a logging format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

    async def login(self):
        load_dotenv()
        dbinfo = "database/" + os.getenv("DB_NAME")

        self.conn = await aiosqlite.connect(dbinfo)
        await self.conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key support

    async def query(self, statement, *values):
        if self.conn is None:
            await self.login()
        good = False
        try:
            async with self.conn.execute(statement, values) as cursor:
                await self.conn.commit()
                good = True
        except Exception as e:
            await self.conn.rollback()
            self.log.exception("Error committing")
        finally:
            await self.conn.close()
            self.conn = None
        return good

    async def fetch(self, statement, *values):
        if self.conn is None:
            await self.login()
        data = None
        try:
            async with self.conn.execute(statement, values) as cursor:
                data = await cursor.fetchall()
                await self.conn.commit()
        except Exception as e:
            await self.conn.rollback()
            self.log.exception("Error committing")
        finally:
            await self.conn.close()
            self.conn = None
        return data

    async def create_incident(self, user_id, description, decision, reported_by, reported_at):
        sql = """INSERT INTO incidents (user_id, description, decision, reported_by, reported_at)
        VALUES (?, ?, ?, ?, ?);"""
        return await self.query(sql, user_id, description, decision, reported_by, reported_at)

    async def create_banish(self, user_id, roles, banished_at, unbanish_at, reason, banished_by):
        sql = "SELECT is_banished FROM banished WHERE user_id = ? AND is_banished = 'Y';"
        is_banished = await self.fetch(sql, user_id)

        if not is_banished:
            sql = """INSERT INTO banished (user_id, roles, banished_at, unbanish_at, reason, is_banished, banished_by)
            VALUES (?, ?, ?, ?, ?, 'Y', ?);"""
            return False, await self.query(sql, user_id, roles, banished_at, unbanish_at, reason, banished_by)

        return True, False

    async def create_unbanish(self, user_id, unbanished_by, unbanished_at):
        sql = "SELECT banished_id, roles FROM banished WHERE user_id = ? AND is_banished = 'Y';"
        data = await self.fetch(sql, user_id)

        if data:
            banished_id = data[0][0]
            roles = data[0][1]
            sql = """UPDATE banished SET is_banished='N', unbanished_by=?, unbanish_at=?
            WHERE banished_id = ?;"""
            return False, await self.query(sql, unbanished_by, unbanished_at, banished_id), roles

        return True, False, None

    async def get_banished(self):
        sql = "SELECT user_id, unbanish_at FROM banished WHERE is_banished = 'Y';"
        return await self.fetch(sql)

    async def get_incident(self, user_id):
        sql = "SELECT * FROM incidents WHERE user_id = ? ORDER BY reported_at DESC;"
        return await self.fetch(sql, user_id)
