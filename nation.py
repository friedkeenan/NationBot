#!/usr/bin/env python3

import json
import sys
import time
import os
import datetime as dt
from minecraft import authentication
from minecraft.networking.packets import * #Give me all those packets daddy
from minecraft.networking.packets.clientbound.play import UpdateHealthPacket
from minecraft.networking.packets.serverbound.play import ClientStatusPacket
from minecraft.networking.connection import Connection
from minecraft.exceptions import YggdrasilError
from CustomPackets import *
from config import *
from StockMarket import *

def write_msg(msg,whisper=True): #Tiny little function that writes a ChatPacket to the server
	p=ChatPacket()
	if whisper:
		msg="/r "+msg
	p.message=msg
	connection.write_packet(p)
def process_chat(packet):
	global stop_loop,connection,restart,update
	st.process(packet)
	t=st.process_chat(packet)
	if t: #If there's anything worthwhile in t
		if t=="Server will restart in 15 seconds": #Escape to limbo and then wait 15 seconds before choosing a character
			write_msg("/limbo",False)
			restart=time.time()
		elif t.startswith("Received "): #If the money isn't for a deal, deposit it into the nation bank, otherwise finish the deal
			amount=float(t.split(" ",1)[1].split("¥")[0])
			sender=t.split("from ")[-1]
			matched=False
			for d in st.deals: #Find any deals with sender as buyer with the correct amount of money
				if d["money"]==amount and d["buy"]==sender and d["accepted"]:
					st.transfer_shares(d["amount"],d["buy"],d["sell"])
					write_msg("/pay "+d["sell"]+" "+str(amount),False)
					st.rm_deal(d)
					matched=True
					break
			if not matched:
				write_msg("/nation deposit "+str(amount),False)
		elif " -> You: " in t: #If the bot has been whispered to
			sender=t.split(" -> ",1)[0]
			command=t.split(": ",1)[1].split("//") #Allow for multiple commands in one message separated by "//" 
			for c in command: #Commands go here if you couldn't guess
				c=c.split(" ",1)
				if c[0]=="say" and sender==admin:
					write_msg(c[1],False)
				elif c[0]=="stop" and sender==admin:
					connection.disconnect()
					stop_loop=True
				elif c[0]=="restart" and sender==admin:
					print("Restarting...\n\n")
					time.sleep(4)
					os.execv(__file__,sys.argv) #This probably only works in environments where you can do ./file
				elif c[0]=="reconnect" and sender==admin:
					connection.disconnect()
				elif c[0]=="update" and sender==admin: #Will update all the town and member info
					update=[list(st.towns.keys())[0],-1]
				elif c[0]=="tellraw" and sender==admin: #Emulates the /tellraw command
					p=ChatMessagePacket()
					p.json_data=c[1]
					p.position=1
					process_chat(p)
				elif c[0]=="exec" and sender==admin:
					for e in c[1].split(";"):
						try:
							eval(e)
						except Exception as e:
							write_msg(str(e))
							break
				elif c[0]=="balance":
					if len(c)==1:
						if sender not in st.members:
							write_msg("You are not registered with "+st.nation+". To register, you must be part of the nation, your town must be registered with the 'addTown [town]' command, and you must give me the command 'addMember [name]'")
							continue
						mem=sender
					else:
						mem=c[1]
						if mem not in st.members:
							write_msg(mem+" is not registered with "+st.nation)
							continue
					bal=st.members[mem]["shares"]
					total=st.num_shares
					try:
						per=float("%.4f"%(bal/total))*100
					except ZeroDivisionError:
						per="Stop"
					if mem==sender:
						write_msg("You have "+str(bal)+"/"+str(total)+" ("+str(per)+"%) shares")
					else:
						write_msg(mem+" has "+str(bal)+"/"+str(total)+" ("+str(per)+"%) shares")
				elif c[0]=="addMember":
					try:
						c[1]
					except IndexError:
						write_msg("Usage: addMember [player]")
						break
					write_msg("/res "+c[1],False)
				elif c[0]=="addTown":
					try:
						c[1]
					except IndexError:
						write_msg("Usage: addTown [town]")
						break
					write_msg("/town "+c[1],False)
				elif c[0]=="kinkshame":
					write_msg("Your kink is hereby shamed")
				elif c[0]=="ping":
					write_msg("pong")
				elif c[0]=="joinTown":
					write_msg("/town add "+sender,False)
				elif c[0]=="vote" and sender in st.members:
					try:
						c=[c[0]]+c[1].split() #Allow for multiple arguments
					except:
						write_msg("Usage: vote [make/vote/list/info] [etc]")
						continue
					if c[1]=="make":
						if st.members[sender]["shares"]/st.num_shares>=.01: #Check if sender has at least 1% of shares needed to make a vote
							try:
								if c[2] in st.votes or c[2] in st.votes_done:
									write_msg("There is already a vote named '"+c[2]+"'")
									continue
								c[3]=" ".join(c[3:]) #Connect all the words after c[2] to make one big proposition
								c=c[:4] #Get rid of everything after c[3]
								st.add_vote(c[2],c[3])
								write_msg("/tn "+sender+" has proposed a vote named '"+c[2]+"'. To learn more, use the command 'vote info "+c[2]+"'. To vote on it, use the command 'vote vote "+c[2]+" [yes/no]'",False)
							except:
								write_msg("Usage: vote make [vote name] [proposition]")
						else:
							write_msg("Sorry, you need to own at least 1% of the shares to propose a vote")
					elif c[1]=="vote":
						try:
							if c[2] in st.votes:
								if sender in st.votes[c[2]]["voted"]:
									write_msg("You've already voted in '"+c[2]+"'")
									continue
								stance=""
								if c[3].lower()=="yes":
									stance="yes"
								elif c[3].lower()=="no":
									stance="no"
								else:
									write_msg("Usage: vote vote [vote name] [yes/no]")
									continue
								st.vote(sender,c[2],stance)
							elif c[2] in st.votes_done:
								write_msg("'"+c[2]+"' has already finished. Use the command 'vote info "+c[2]+"' to learn more")
							else:
								write_msg("There is no vote named '"+c[2]+"'")
						except:
							write_msg("Usage: vote vote [vote name] [yes/no]")
					elif c[1]=="list":
						write_msg("Current votes: "+", ".join(st.votes.keys()))
						write_msg("Finished votes: "+", ".join(st.votes_done.keys()))
					elif c[1]=="info":
						try:
							votes={} #Join both st.votes and st.votes_done so that players can get info on both
							votes.update(st.votes)
							votes.update(st.votes_done)
							if c[2] in votes:
								time_left=str(dt.timedelta(seconds=abs(int(votes[c[2]]["time"]+vote_wait-time.time()))))
								if c[2] in st.votes_done: #Timedelta messes up when seconds are negative, which would be when a vote is finished
									time_left="-"+time_left
								write_msg("Proposition: "+votes[c[2]]["proposition"]+"; For: "+str(votes[c[2]]["yes"])+"; Against: "+str(votes[c[2]]["no"])+"; Time left: "+time_left)
							else:
								write_msg("There is no vote named '"+c[2]+"'")
						except:
							write_msg("Usage: vote info [vote name]")
					else:
						write_msg("Usage: vote [make/vote/list/info] [etc]")
				elif c[0]=="deal" and sender in st.members:
					try:
						c=[c[0]]+c[1].split() #Allow for multiple arguments
					except:
						write_msg("Usage: deal [sell/accept/deny] [etc]")
						continue
					if c[1]=="sell":
						try:
							if c[2] in st.members and c[2]!=connection.auth_token.profile.name: #Players can't whisper to themselves, so check if the sender is trying to sell to the user
									shares=float(c[3])
									if st.members[sender]["shares"]<shares or shares<0: #If sender is trying to sell more shares than they have or selling a negative number
										write_msg("Invalid amount of shares")
										continue
									c[4]="%.2f"%float(c[4])
									st.add_deal(c[2],sender,shares,float(c[4]))
									write_msg("/msg "+c[2]+" "+sender+" wants to sell you "+str(shares)+" shares for "+c[4]+"¥. Use the command 'deal accept [seller]' to accept, and 'deal deny [seller]' to deny",False)
							else:
								write_msg("You are not allowed to sell to "+c[2])
						except StockMarket.DuplicateDealException:
							write_msg("There is already a deal between you and "+c[2])
						except:
							write_msg("Usage: deal sell [buyer] [shares] [money]")
					elif c[1]=="accept":
						matched=False
						money=0
						shares=0
						for d in st.deals: #Find matching deal
							if d["buy"]==sender and d["sell"]==c[2]:
								matched=True
								d["accepted"]=True
								money=d["money"]
								shares=d["amount"]
								break
						if matched:
							write_msg("/msg "+c[2]+" "+sender+" has accepted your deal. Please pay me "+str(money)+"¥ now to sell them "+str(shares)+" shares",False)
						else:
							write_msg("You have no deals with "+c[2])
					elif c[1]=="deny":
						matched=False
						for d in st.deals: #Find matching deal
							if d["buy"]==sender and d["sell"]==c[2]:
								matched=True
								st.rm_deal(d)
								break
						if matched:
							write_msg("/msg "+c[2]+" "+sender+" has denied your deal",False)
						else:
							write_msg("You have no deals with "+c[2])
					else:
						write_msg("Usage: deal [sell/accept/deny] [etc]")
				else:
					write_msg("Unknown command. To seek help with the bot, please ask "+admin) 
		with open("ChatLogs/"+dt.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")+".log","a",encoding="utf-8") as f: #Save chat messages in .log file for each day
			f.write("["+str(time.time())+"] "+t+"\n")
		print(t)
def keep_alive(packet): #Is called every 30ish seconds
	global update
	rm_votes=[] #Need this because you can't delete a key from a dictionary while it's being used in a for loop
	for v in st.votes:
		if st.votes[v]["time"]+vote_wait<=time.time(): #If the time has come for the vote to be finished
			write_msg("/tn The vote '"+v+"' has finished. Use the command 'vote info "+v+"' to learn more",False)
			rm_votes.append(v)
	for v in rm_votes:
		st.finish_vote(v)
	rm_votes=[]
	for v in st.votes_done:
		if st.votes_done[v]["time"]+vote_wait+vote_die<=time.time(): #If the time has come for the vote to die
			rm_votes.append(v)
	for v in rm_votes:
		st.rm_vote_done(v)
	if time.time()>=st.last_update+do_update: #If enough time has passed to do another update
		update=[list(st.towns.keys())[0],-1]
		st.last_update=time.time()
		st.save_update()
	if update: #If update isn't None
		if update[1]==-1:
			write_msg("/town "+update[0].replace(" ","_"),False)
		else:
			write_msg("/res "+st.towns[update[0]]["res"][update[1]],False)
		if update[1]<len(st.towns[update[0]]["res"])-1:
			update[1]+=1
		else:
			update[1]=-1
			try:
				update[0]=list(st.towns.keys())[list(st.towns.keys()).index(update[0])+1]
			except IndexError:
				update=None
def respawn(packet):
	if packet.health<=0:
		p=ClientStatusPacket()
		p.action_id=0
		connection.write_packet(p)
def set_slot(packet):
	global restart
	if packet.window_id==2 and packet.slot==2: #If this is the second window opened and the third slot in that window (which will be a character slot)
		if restart:
			while time.time()<=restart+15: #Can't use time.time() because that causes a time out
				pass
			restart=None
		p=ClickWindowPacket()
		p.window_id=packet.window_id
		p.slot=packet.slot
		p.button=0
		p.action_number=1
		p.mode=0
		p.clicked=packet.slot_data
		connection.write_packet(p)
def in_out(packet,bound="OUT"):
	try:
		packet_type=hex(packet.get_id(packet.context))
		if packet_type in ignore_ids:
			return
		print(bound+": "+packet_type+" - "+str(type(packet)).split(".")[-1][:-2])
	except TypeError:
		return
	definition=packet.get_definition(packet.context)
	if not definition:
		return
	for t in definition:
		try:
			attr=list(t.keys())[0]
		except IndexError:
			continue
		print("---- "+attr+" : "+str(getattr(packet,attr)))
def new_connection():
	m=authentication.AuthenticationToken()
	auth=False
	while not auth: #Retry authentication until we get it
		try:
			auth=m.authenticate(user,pw)
		except YggdrasilError as e: #If authentication fails
			print(e)
			time.sleep(5)
			print("Retrying...")
	c=Connection(server_ip,auth_token=m,initial_version=server_version)
	c.register_packet_listener(keep_alive,KeepAlivePacketClientbound)
	c.register_packet_listener(process_chat,ChatMessagePacket,early=True)
	c.register_packet_listener(respawn,UpdateHealthPacket)
	c.register_packet_listener(set_slot,SetSlotPacket)
	if debug:
		c.register_packet_listener(in_out,Packet,outgoing=True)
		c.register_packet_listener(lambda x:in_out(x,"IN"),Packet)
	return c
if not os.path.exists("ChatLogs"):
	os.mkdir("ChatLogs")
connection=new_connection()
connection.connect()
print("Connected to server\n\n")
st=StockMarket("Kraotum")
stop_loop=False
restart=None
update=None
while not stop_loop: #There needs to be something happening in this loop or else it'll time out once it joins lobby
	time.sleep(5)
	if not connection.connected: #If for whatever reason we get unknowingly disconnected, get a new connection
		connection=new_connection()
		connection.connect()
print("\n\nScript Ended")
