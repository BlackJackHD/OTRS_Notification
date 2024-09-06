import psycopg2
from requests import get
import time
import re
import base64
import config
import telebot
from telebot import types
from wakeonlan import send_magic_packet

#чтение тикета из файла
def file_r(name):
	my_file = open(str(name))
	z = my_file.read()
	my_file.close()
	return(z)
#запись последнего id тикета в файл
def file_w(name, z):
		my_file = open(name, 'w+')
		z = str(z)
		my_file.write(z)
		z = my_file.read()
		my_file.close()	
#отправка сообщения
def text_message(recipient,text):
	token = str('https://api.telegram.org/bot' + config.token + '/sendMessage')
	payload = {'chat_id': recipient, 'text': text}
	r = get(token, params=payload)
#сообщение всем пользователям
def message_for_all(text):
	for x in config.recipient:
		text_message(x,text)
#сообщение об ошибке
def ermac(text):
	text = str("OTRSnoton - ") + text
	for x in config.ermac_recipient:
		token = str('https://api.telegram.org/bot' + config.ermac_token + '/sendMessage')
		payload = {'chat_id': x, 'text': text}
		r = get(token, params=payload)
#декодирование html-тела сообщения преобразование в читабельный вид
def html_decode(text):
	text = base64.b64decode(text)
	text = text.decode('utf-8')
	text = re.sub("&#(\d+);", lambda match: chr(int(match.group(1))), text)
	text = re.sub(r'<br>', '\n', text)
	text = re.sub(r'&nbsp;', ' ', text)
	text = re.sub(r'\<[^<>]*\>', '', text)
	return(text)
#sql-запрос с возвратом всех результатов
def psql_req(req):
	try:
		connection = psycopg2.connect(dbname=config.dbname,user=config.user, password=config.password,host=config.host, port=config.port)
		req = str(req)
		cursor = connection.cursor()
		cursor.execute(req)
		record = cursor.fetchall()
		return(record)
	except Exception as ex:
		ermac(ex)
		return(None)
#цветовая индикация заявок  по ID
	#🔴 - 1 - открыта разблокирована
	#🟡 - 2 - открыта заблокирована
	#🟢 - 3 - закрыта
	#🔵 - 9 - объединенна
	#⚫ - неизвестно
def bounce(id):
	record_bounce = psql_req("SELECT ticket_lock_id,ticket_state_id FROM ticket WHERE id = " + str(id) + ";")
	if record_bounce[0][1] == 3 or record_bounce[0][1] == 2:
		return("🟢")
	elif record_bounce[0][1] == 9:
		return("🔵")
	elif record_bounce[0][0] == 1:
		return("🔴")
	elif record_bounce[0][0] == 2:
		return("🟡")
	else:
		return("⚫")

bot = telebot.TeleBot(config.token)

# Все открытые заявки
@bot.message_handler(commands = ['open_tickets'])
def open_tickets(message):
	if message.text == '/open_tickets':
		record = psql_req("SELECT id,tn,title FROM ticket WHERE ticket_state_id = 1 OR ticket_state_id = 4 ORDER BY id DESC;")
		if len(record) > 0:
			j = 0
			message_ticket = str()
			while j < len(record):
				ticket = str(bounce(record[j][0])) + "ID - " + str(record[j][0]) + "\nНомер заявки - " + str(record[j][1]) + "\nНазвание темы - " + str(record[j][2])
				print(ticket)
				message_ticket = message_ticket + ticket  + '\n\n'
				j+=1
			bot.send_message(message.chat.id, message_ticket)

# Все разблокированные заявки
@bot.message_handler(commands = ['unblock_tickets'])
def unblock_tickets(message):
	if message.text == '/unblock_tickets':
		record = psql_req("SELECT id,tn,title FROM ticket WHERE ticket_state_id = 1 AND ticket_lock_id = 1 OR ticket_state_id = 4 AND ticket_lock_id = 1 ORDER BY id DESC;")
		if len(record) > 0:
			j = 0
			message_ticket = str()
			while j < len(record):
				ticket = str(bounce(record[j][0])) + "ID - " + str(record[j][0]) + "\nНомер заявки - " + str(record[j][1]) + "\nНазвание темы - " + str(record[j][2])
				print(ticket)
				message_ticket = message_ticket + ticket  + '\n\n'
				j+=1
			bot.send_message(message.chat.id, message_ticket)

# Дневная активность
@bot.message_handler(commands = ['day_active'])
def day_active(message):
	if message.text == '/day_active':
		today = time.strftime('%Y-%m-%d', time.gmtime(time.time()))
		print(today)
		# Запрос артиклей сегодняшнего дня
		record = psql_req("SELECT id,ticket_id,create_time FROM article WHERE create_time > '" + today + "' ORDER BY ticket_id DESC;")
		if len(record) > 0:
			j = 0
			while j < len(record):
				record_title = psql_req("SELECT title,id FROM ticket WHERE id = " + str(record[j][1]) + ";")
				print(record_title)
				record_body = psql_req("SELECT content_type,content,create_time FROM article_data_mime_attachment WHERE article_id=" + str(record[j][0]) + ";")
				for x in record_body:
					try:	
						if x[0][0:5] == "text/":
							bot.send_message(message.chat.id, str(bounce(record[j][1])) + "ID заявки: " + str(record_title[0][1]) + "\n" + "Название темы: " + str(record_title[0][0]) + "\n---\n" + html_decode(x[1]))
					except:
						None
				j+=1
		else:
			bot.send_message(message.chat.id, "Активности сегодня не было")

# Wake-On-Lan рабочего ПК
@bot.message_handler(commands = ['WoL'])
def WoL(message):
	if message.text == '/WoL':
		send_magic_packet(config.wol)
		bot.send_message(message.chat.id, "Magic Packet is sended.")

# Коськи :3
@bot.message_handler(commands = ['kitty'])
def kitty(message):
    if message.text == '/kitty':
        S = config.cats
        bot.send_sticker(message.chat.id, S[int(time.time())%len(S)])

# Выдача данный по ID заявки
@bot.message_handler(content_types = ["text"])
def detail_ticket(message):
	if message.text.isdigit() == True:	
		try:
			ticket_id = str(message.text)
			record_title = psql_req("SELECT title FROM ticket WHERE id=" + ticket_id + ";")
			record = psql_req("SELECT id FROM article WHERE ticket_id=" + ticket_id + ";")
			if len(record) == 0:
				bot.send_sticker(message.chat.id, 'CAACAgIAAxkBAAEETCRiQYmQFwll0zEk50LdTBIbESJwAANPAAOxPQYQpfTBjdo8MWAjBA')
				time.sleep(2)
				bot.send_message(message.chat.id, "ID не существует")
			else:
				bot.send_message(message.chat.id, str(bounce(ticket_id)) + str(record_title[0][0]))
				for id in record:
					record_1 = psql_req("SELECT content_type,content FROM article_data_mime_attachment WHERE article_id=" + str(id[0]) + ";")
					for x in record_1:
						if x[0][0:9] == "text/html":
							bot.send_message(message.chat.id, html_decode(x[1]))
		except Exception as ex:
			ermac(ex)
		else:
			text = "Зачем мне " + message.text + ", когда мне нужен ID?"
			bot.send_message(message.chat.id, text)

# Проверка на дурака)
@bot.message_handler(content_types = ["voice"])
def voice_message(message):
    bot.send_message(message.chat.id, "У меня нет времени на гс.")
    name = message.from_user.first_name + " " + message.from_user.last_name + " " + message.from_user.username
    text = str("ГС получено от:") + name
    ermac(text)

try:
	bot.polling(none_stop=True, interval=2)
except:
	time.sleep(5)