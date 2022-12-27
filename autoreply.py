from telethon import TelegramClient, events, sync
import json
import datetime
import re
import random

#
api_id = 2540394
api_hash = 'e495b6acc460d97ca29b23dd65b9fb68' 
client = TelegramClient('sessionfirst', api_id, api_hash)

#
timeToHello = 14 #days
timeToHi = 4 #hours

#
with open('settings.json', 'r', encoding='utf-8') as f:
	settings = json.load(f)
with open('users.json', 'r', encoding='utf-8') as f:
	users = json.load(f)

#
async def updateUsers(users):
	with open('users.json', 'w', encoding='utf-8') as f:
		json.dump(users, f, sort_keys = True, ensure_ascii=False, indent=4)

#
async def sayHello(user_id_int):
	await client.send_message(user_id_int, settings['greetings']['hello'])
	await client.send_file(user_id_int, settings['greetings']['images'])

async def sayHi(user_id_int):
	await client.send_message(user_id_int, settings['greetings']['hi'])

#
async def sendQuest(user_id, message):
	quest = 'no'
	for k in users[user_id]['questions']:
		if users[user_id]['questions'][k] == 0:
			quest = k
			break
	if quest != 'no':
		await client.send_message(users[user_id]['id'], settings['questions'][quest])
		users[user_id]['stat'] = 'parseAnswer'
	else:
		users[user_id]['stat'] = 'no' #в будущем: статус meeting - вызывать обработку встречи
		await client.send_message(users[user_id]['id'], settings['greetings']['done'])
#
async def parseAnswer(user_id, message):
	quest = 'no'
	for k in users[user_id]['questions']:
		if users[user_id]['questions'][k] == 0:
			quest = k
			break
	#if quest no
	matches = re.findall(settings['parse'][quest], message.text)
	
	if len(matches)<=0:
		pass
	else:
		users[user_id]['questions'][quest] = 1
		users[user_id]['about'][quest] = matches[0]
		#номер телефона не копируется, поэтому для него отдельный шаг
		if quest == 'phone':
			users[user_id]['about'][quest] = message.text
		users[user_id]['stat'] = 'sendQuest'
		await client.send_message(users[user_id]['id'], random.choice(settings["answers"]))

		#продолжаем спрашивать, функция через словарь
		await fs['sendQuest'](user_id, message)
#
fs = {'sendQuest': sendQuest, 'parseAnswer': parseAnswer}

###
with client:
	@client.on(events.NewMessage(incoming = True))
	async def handler(event):
		user_id_int = int(event.message.peer_id.user_id);
		user_id = str(event.message.peer_id.user_id)

		#
		if users.get(user_id) == None:
			users.update({
				user_id: {
					'id': user_id_int,
					'lasthello': datetime.date.today().strftime('%Y, %m, %d'),
					'last_reply': datetime.datetime.today().strftime('%Y-%m-%d %H:%M'),
					'prev_stat': 'no',
					'stat': 'sendQuest',
					'next_stat': 'parseAnswer',
					'questions': {
						'age': 0, 'nat': 0, 'phone': 0
					},
					'about': {
						'age': 0, 'nat': 0, 'phone': 0
					},
					"about_me": {
						"age": 0, "nat": 0, "phone": 0, "pretty": 0, "address": 0
					}
				}
			})
			#hello
			await sayHello(user_id_int)
		else:
			#User = users[user_id]
			last_reply = datetime.datetime.strptime(users[user_id]['last_reply'], '%Y-%m-%d %H:%M')
			delta = datetime.datetime.today() - last_reply
			if(delta.days >= timeToHello):
				await sayHello(user_id_int)

				#очищаем состояние и значения вопросов
				users[user_id]['stat'] = 'sendQuest'
				
				for k in users[user_id]['questions']:
					users[user_id]['questions'][k] = 0
				for k in users[user_id]['about_me']:
					users[user_id]['about_me'][k] = 0
			elif((delta.total_seconds()) // 3600 >= timeToHi):
				await sayHi(user_id_int)
				if users[user_id]['stat'] != 'meeting':
					users[user_id]['stat'] = 'sendQuest'

			users[user_id]['last_reply'] = datetime.datetime.today().strftime('%Y-%m-%d %H:%M')
			
			#выполнить функцию, которой предназначен пользователь
			next_stat = users[user_id]['next_stat']
			stat = users[user_id]['stat']
			if stat != 'no':
				await fs[stat](user_id, event.message)
		#

		#ответ на заданный вопрос 
		for k in settings['about_reg']:
			matches = re.findall(settings['about_reg'][k], event.message.text)
			if len(matches)>0:
				if users[user_id]['about_me'][k]==0:
					await event.reply(settings['about'][k])
					users[user_id]['about_me'][k] = 1
				elif users[user_id]['about_me'][k]==1:
					await event.reply(settings['about']['answered_' + k])
					users[user_id]['about_me'][k] = 2
				break

		await updateUsers(users)

	#separete functions for Me
	#добаить проверку, что ты пишешь сам себе
	@client.on(events.NewMessage(incoming = True, pattern='(Забудь меня)'))
	async def handler(event):
		users.pop(str(event.message.peer_id.user_id))
		await updateUsers(users)
		await event.reply('Все забыто. Чтобы начать говорить со мной вновь, напиши любую фразу.')
	
	client.run_until_disconnected()
	#
	