from __future__ import absolute_import
from .msgtypes import *

BUF_COL_WIDTH = 16

def format(time, msg_type, message, sender, buffer):
	formatted = ''
	if buffer:
		formatted += '(%s)' % (buffer)
		formatted += ' ' * max(0,(BUF_COL_WIDTH - len(formatted)))
	formatted += '[%s] ' % time

	try:
		return formatted + parser_for_msgtype[msg_type](message, sender)
	except KeyError:
		return formatted + ' <Unknown event: %s, %s, %s>' % (msg_type, message, sender)

def msg_parser(message, sender):
	return '<%s> %s' % (sender, message)

def notice_parser(message, sender):
	return '-%s- %s' % (sender, message)

def action_parser(message, sender):
	return '* %s %s' % (sender, message)

def nick_parser(message, sender):
	return '-!- %s changed nick to %s' % (sender, message)

def mode_parser(message, sender):
	return '-!- %s set mode %s' % (sender, message)

def join_parser(message, sender):
	return '--> %s has joined the channel' % (sender)

def part_parser(message, sender):
	return '<-- %s has left the channel (%s)' % (sender, message)

def quit_parser(message, sender):
	return '<-- %s has quit (%s)' % (sender, message)

def kick_parser(message, sender):
	target, message = message.split(' ', 1)
	return '-!- %s has kicked %s (%s)' % (sender, target, message)

def topic_parser(message, sender):
	return '-!- %s' % (message)

def invite_parser(message, sender):
	return '-!- %s' % (message)

def splitjoin_parser(message, sender):
	items = message.split('#:#')
	users = ', '.join([item[:item.find('!')] for item in items[:-1]])
	servers = items[-1].split(' ')
	return '--> Netsplit between %s and %s ended. Joined: %s' % (servers[0], servers[1], users)

def splitquit_parser(message, sender):
	items = message.split('#:#')
	users = ', '.join([item[:item.find('!')] for item in items[:-1]])
	servers = items[-1].split(' ')
	return '<-- Netsplit between %s and %s. Quit: %s' % (servers[0], servers[1], users)

parser_for_msgtype = {
	MSG : msg_parser,
	NOTICE : notice_parser,
	ACTION : action_parser,
	NICK : nick_parser,
	MODE : mode_parser,
	JOIN : join_parser,
	PART : part_parser,
	QUIT : quit_parser,
	KICK : kick_parser,
	TOPIC : topic_parser,
	INVITE : invite_parser,
	SPLITJOIN : splitjoin_parser,
	SPLITQUIT : splitquit_parser
}
