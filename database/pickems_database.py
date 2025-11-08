import aiosqlite
import os
from dotenv import load_dotenv
from datetime import datetime
from util.logger import setup_logger

class PickemsDatabase:
    def __init__(self):
        load_dotenv()
        self.pool = None
        self.conn = None
        self.log = setup_logger(__name__, 'log/db.log')

    async def login(self):
        dbinfo = "database/" + os.getenv("PICKEMS_DB_NAME")

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
            self.log.info(f"Query: {statement} with values {values}")
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

    async def create_message(self, message_id, game_id):
        sql = """INSERT INTO Messages (message_id, game_id)
        VALUES (?, ?);"""

        return await self.query(sql, message_id, game_id)

    async def get_message(self, game_id):
        sql = "SELECT message_id from Messages where game_id = ?;"

        m = await self.fetch(sql, game_id)

        return m[0][0] if m else None
    
    async def create_pick(self, user_id, game_id, team_id, season, picked_at):
        sql = """INSERT INTO Picks (user_id, game_id, team_id, season, picked_at)
        VALUES (?, ?, ?, ?, ?);"""

        return await self.query(sql, user_id, game_id, team_id, season, picked_at)
    
    async def get_pick(self, user_id, game_id):
        sql = """SELECT team_id FROM Picks WHERE user_id = ? AND game_id = ?"""

        team = await self.fetch(sql, user_id, game_id)

        return team[0][0] if team else None
    
    async def update_pick(self, user_id, game_id, team_id, picked_at):
        sql = """UPDATE Picks
        SET team_id = ?, picked_at = ?
        WHERE user_id = ? AND game_id = ?;"""

        return await self.query(sql, team_id, picked_at, user_id, game_id)
    
    # get all records from the Records table
    # fields: user_id, wins, losses
    # put into a dict with user_id as key
    # return dict
    async def get_records(self):
        sql = "SELECT user_id, wins, losses FROM Records;"

        records = await self.fetch(sql)

        return {r[0]: r[1:] for r in records}
    
    # get the leaderboard from the leaderboard view
    # fields: user_id, wins, losses, win_pct, rank
    # put into a dict with user_id as key
    # return dict
    async def get_leaderboard(self, season):
        sql = "SELECT * FROM Leaderboard WHERE season = ?;"

        leaderboard = await self.fetch(sql, season)

        return {l[0]: l[1:-1] for l in leaderboard}
    
    # get the max updated_at from the Records table
    # return datetime
    async def get_records_updated_at(self):
        sql = "SELECT MAX(updated_at) FROM Records;"

        updated_at = await self.fetch(sql)

        return updated_at[0][0]
    
    # get the record and rank from the leaderboard view for a user
    # fields: user_id, wins, losses, win_pct, rank
    # return tuple
    async def get_user_leaderboard_position(self, user_id, season):
        sql = "SELECT * FROM Leaderboard WHERE user_id = ? AND season = ?;"

        user = await self.fetch(sql, user_id, season)

        return user[0] if user else None
    
    # get the user's picks for a date
    # fields: team_id
    # return list of team_ids
    async def get_user_picks(self, user_id, date):
        sql = """SELECT team_id FROM Picks
        WHERE user_id = ? AND date(picked_at) = ?;"""

        picks = await self.fetch(sql, user_id, date)

        return [p[0] for p in picks]

    # delete all picks for a game
    async def delete_picks(self, game_id):
        sql = "DELETE FROM Picks WHERE game_id = ?;"

        return await self.query(sql, game_id)
    
    async def get_picks(self, date):
        sql = """SELECT user_id, team_id FROM Picks
        WHERE date(picked_at) = ?;"""
        
        picks = await self.fetch(sql, date)

        r = {}
        for p in picks:
            if p[0] in r:
                r[p[0]].append(p[1])
            else:
                r[p[0]] = [p[1]]
        
        return r
    
    async def update_record(self, user_id, win, season):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        #check if user's record exists
        sql = "SELECT * FROM Records WHERE user_id = ? and season = ?;"
        record_exists = await self.fetch(sql, user_id, season)
        
        if not record_exists:
            #create user's record
            sql = """INSERT INTO Records (user_id, wins, losses, season, updated_at)
            VALUES (?, 0, 0, ?, ?);"""
            await self.query(sql, user_id, season, now)
        
        #update user's record
        if win:
            sql = """UPDATE Records
            SET wins = wins + 1, updated_at = ?
            WHERE user_id = ?;"""
        else:
            sql = """UPDATE Records
            SET losses = losses + 1, updated_at = ?
            WHERE user_id = ?;"""
        
        return await self.query(sql, now, user_id)