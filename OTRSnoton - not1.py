import psycopg2
from requests import get
import time
import re
import base64
import config
import telebot
from telebot import types
from threading import Thread

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
# Проверка наличия новых id и article_id и отправка уведомления, с учётом статуса изменения 
def notification():
	try:
		last_ticket_id = str(file_r('lti.txt'))
		# time.sleep(1)
		last_article_id = str(file_r('lai.txt'))
		record_article_id = psql_req("SELECT id,ticket_id FROM article WHERE id > " + last_article_id + " ORDER BY id;")
		if len(record_article_id) > 0:
			j = 0
			while j < len(record_article_id):
				record_title = psql_req("SELECT id,tn,title,customer_user_id,create_time FROM ticket WHERE id = " + str(record_article_id[j][1]) + ";")
				time.sleep(1)
				record_body = psql_req("SELECT content_type,content,article_id FROM article_data_mime_attachment WHERE article_id=" + str(record_article_id[j][0]) + ";")
				time.sleep(1)
				try:						
					if record_body[0][0][0:5] == "text/":
						if record_article_id[j][1] > int(last_ticket_id):
							message_for_all(str(bounce(record_title[0][0])) + "Новая заявка:\n\nID - " + str(record_title[0][0]) + "\nНомер заявки - " + str(record_title[0][1]) + "\nНазвание темы - " + str(record_title[0][2]) + "\nОтправитель - " + str(record_title[0][3]) + "\nВремя создания - " + str(record_title[0][4]) + "\n---\n" + html_decode(record_body[0][1]))
							time.sleep(1)
							file_w('lti.txt', record_title[0][0])
							file_w('lai.txt', record_body[0][2])
						else:
							message_for_all(str(bounce(record_title[0][0])) + "Добавлен ответ к заявке:\n\nID заявки: " + str(record_title[0][0]) + "\nНазвание темы:" + str(record_title[0][2]) + "\n---\n" + html_decode(record_body[0][1]))
							time.sleep(1)
							file_w('lai.txt', record_body[0][2])
					else:
						file_w('lai.txt', record_body[0][2])
				except:
					message_for_all(str(bounce(record_title[0][0])) + "Новая заявка:\n\nID - " + str(record_title[0][0]) + "\nНомер заявки - " + str(record_title[0][1]) + "\nНазвание темы - " + str(record_title[0][2]) + "\nОтправитель - " + str(record_title[0][3]) + "\nВремя создания - " + str(record_title[0][4]))
					# time.sleep(1)
					file_w('lti.txt', record_title[0][0])
					file_w('lai.txt', record_article_id[0][0])
				j+=1
			file_w('lai.txt', record_article_id[0][0])
	except Exception as ex:
		ermac(ex)
	time.sleep(10)

z = 0
while z == 0:
  try:
  	print('hui')
  	notification()
  	print('end')
  	time.sleep(5)
  except:
  	print('Vse upalo')
  	time.sleep(5)