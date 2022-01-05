import re

VALID_FORMATS = {
	'second': (['second', 'seconds', 's', 'sec', 'secs'], 1),
	'minute': (['minute', 'minutes', 'm', 'min', 'mins'], 60),
	'hour': (['hour', 'hours', 'h', 'hr', 'hrs'], 3600),
	'day': (['day', 'days', 'd'], 86400)
}
LENGTH_REGEX = r'\d+'
FORMAT_REGEX = r'\D+'

class InvalidFormatException(Exception):
	def __init__(self, format):
		self.format = format
		self.message = f"Invalid duration format: {format}"
		super().__init__(self.message)

class InvalidDurationException(Exception):
	def __init__(self, duration):
		self.duration = format
		self.message = f"Invalid duration: {duration}"
		super().__init__(self.message)

async def parse(dur):
	length = re.search(LENGTH_REGEX, dur)
	format = re.search(FORMAT_REGEX, dur)

	if not length or not format:# or len(length) > 1 or len(format) > 1:
		raise InvalidDurationException(dur)

	actual_format = await get_full_duration_format(format[0])

	if not actual_format:
		raise InvalidFormatException(dur)

	return int(length[0]) * VALID_FORMATS[actual_format][1]

async def parse_pretty(dur):
	length = re.search(LENGTH_REGEX, dur)
	format = re.search(FORMAT_REGEX, dur)

	if not length or not format:# or len(length) > 1 or len(format) > 1:
		raise InvalidDurationException(dur)

	actual_format = await get_full_duration_format(format[0])

	if not actual_format:
		raise InvalidFormatException(dur)

	actual_format_ = actual_format
	if int(length[0]) > 1:
		actual_format_ += 's'

	pretty_str = length[0] + ' ' + actual_format_

	return pretty_str, int(length[0]) * VALID_FORMATS[actual_format][1]

async def get_full_duration_format(format):
	format = format.lower()

	if format in VALID_FORMATS.keys():
		return format

	for k, v in VALID_FORMATS.items():
		if format in v[0]:
			return k

	return None
