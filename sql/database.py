import aiomysql
import asyncio
from discord.ext import commands

import logging
from logging.handlers import RotatingFileHandler

class Database(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.pool = None
		logging.basicConfig(level=logging.INFO)
		self.log = logging.getLogger(__name__)
		# add a rotating handler
		handler = RotatingFileHandler('log/db.log', maxBytes=5*1024*1024,
									  backupCount=5)

		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	async def login(self):
		with open("db.txt") as f:
			dbinfo = f.read().split('\n')

		self.pool = await aiomysql.create_pool(host='127.0.0.1', port=3306,
								user=dbinfo[0], password=dbinfo[1],
								db=dbinfo[2], loop=self.bot.loop)
	async def query(self, statement, *values):
		good = False
		if self.pool is None:
			await self.login()
		try:
			async with self.pool.acquire() as conn:
				async with conn.cursor() as cur:
					try:
						await cur.execute(statement, values)
						await conn.commit()
						good = True
					except Exception as e:
						await conn.rollback()
						self.log.exception("Error committing")
		except Exception as e:
			self.log.exception("Error")
		finally:
			self.pool.close()
			await self.pool.wait_closed()
			self.pool = None

		return good

	async def fetch(self, statement, *values):
		if self.pool is None:
			await self.login()
		data = None
		try:
			async with self.pool.acquire() as conn:
				async with conn.cursor() as cur:
					try:
						await cur.execute(statement, values)
						data = await cur.fetchall()
						await conn.commit()
					except Exception as e:
						await conn.rollback()
						self.log.exception("Error committing")
		except Exception as e:
			self.log.exception("Error")
		finally:
			self.pool.close()
			await self.pool.wait_closed()
			self.pool = None

		return data

	async def create_incident(self, user_id, description, decision, reported_by, reported_at):
		sql = """INSERT INTO devils.incidents (user_id, description, decision, reported_by, reported_at)
		VALUES (%s, %s, %s, %s, %s);"""

		return await self.query(sql, user_id, description, decision, reported_by, reported_at)

	async def create_banish(self, user_id, roles, banished_at, unbanish_at, reason, banished_by):
		sql = "SELECT is_banished FROM banished WHERE user_id = %s AND is_banished = 'Y';"

		is_banished = await self.fetch(sql, user_id)

		if not is_banished:
			sql = """INSERT INTO devils.banished (user_id, roles, banished_at, unbanish_at, reason, is_banished, banished_by)
			VALUES (%s, %s, %s, %s, %s, 'Y', %s);"""

			return False, await self.query(sql, user_id, roles, banished_at, unbanish_at, reason, banished_by)

		return True, False

	async def create_unbanish(self, user_id, unbanished_by, unbanished_at):
		sql = "SELECT banished_id, roles FROM banished WHERE user_id = %s AND is_banished = 'Y';"

		data = await self.fetch(sql, user_id)

		if data:
			banished_id = data[0][0]
			roles = data[0][1]
			sql = f"""UPDATE devils.banished SET is_banished='N', unbanished_by=%s, unbanish_at=%s
			WHERE banished_id = {banished_id};"""

			return False, await self.query(sql, unbanished_by, unbanished_at), roles

		return True, False, None

	async def get_banished(self):
		sql = "SELECT user_id, unbanish_at FROM banished WHERE is_banished = 'Y';"

		return await self.fetch(sql)

	async def get_incident(self, user_id):
		sql = "SELECT * FROM incidents WHERE user_id = %s ORDER BY reported_at DESC;"

		return await self.fetch(sql, user_id)

def setup(bot):
	bot.add_cog(Database(bot))
