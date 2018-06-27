#!/usr/bin/env python3

import json
import sys
import time
import os
import datetime as dt
from minecraft import authentication
from minecraft.networking.packets import * #Give me all those packets daddy
from minecraft.networking.connection import Connection
from minecraft.exceptions import YggdrasilError,InvalidState
from config import *
from StockMarket import *
st=StockMarket("Kraotum")
def process_chat(packet):
	global stop_loop,connection,restart
	st.process(packet)
	pack=[]
	def append_msg(msg,whisper=True): #Tiny little function that appends a ChatPacket with a message to pack which will all then be sent to the server at the end
		pack.append(ChatPacket())
		if whisper:
			msg="/r "+msg
		pack[-1].message=msg
	try:
		text=json.loads(packet.json_data)["extra"] #List of a bunch of fragmented text
	except: #No "extra" key, nothing of value
		return
	t=''
	for j in text:
		if j["text"]!=" " and j["text"]!="" and j["text"]!="\x15f\x157[ \x15a273.0\x15f\x157 / \x15c273.0 ?\x157 ]": #Clean the text of all the bad stuff
			t+=j["text"]
	if t and "§" not in t: #If there's anything worthwhile in t
		if t=="Server will restart in 15 seconds.": #Disconnect 15 seconds early to stop exception arising from server abruptly stopping
			connection.disconnect()
			restart=True
		elif t.startswith("Received "): #Deposits all of balance into nation when bot receives money
			#append_msg("/nation deposit all",False)
			amount=float(t.split(" ",1)[1].split("¥")[0])
			sender=t.split("from ",1)[1]
			matched=False
			for d in st.deals: #Find any deals with sender as buyer with the correct amount of money
				if d["money"]==amount and d["buy"]==sender and d["accepted"]:
					st.transfer_shares(d["amount"],d["buy"],d["sell"])
					append_msg("/pay "+d["sell"]+" "+str(amount),False)
					st.rm_deal(d)
					matched=True
					break
			if not matched:
				append_msg("/nation deposit "+str(amount),False)
		elif " -> You: " in t: #If the bot has been whispered to
			sender=t.split(" -> ",1)[0]
			command=t.split(": ",1)[1].split("//") #Allow for multiple commands in one message separated by "//" 
			for c in command: #Commands go here if you couldn't guess
				c=c.split(" ",1)
				if c[0]=="say" and sender==admin:
					append_msg(c[1],False)
				elif c[0]=="stop" and sender==admin:
					connection.disconnect()
					stop_loop=True
				elif c[0]=="restart" and sender==admin:
					print("Restarting...\n\n")
					os.execv(__file__,sys.argv) #This probably only works in environments where you can do ./file
				elif c[0]=="reconnect" and sender==admin:
					connection.disconnect()
				elif c[0]=="exec" and sender==admin:
					for e in c[1].split(";"):
						try:
							eval(e)
						except Exception as e:
							append_msg(str(e))
							break
				elif c[0]=="balance":
					if sender not in st.members:
						append_msg("You are not registered with "+st.nation+". To register, you must be part of the nation, your town must be registered with the 'addTown [town]' command, and you must give me the command 'addMember [name]'")
						continue
					bal=st.members[sender]["shares"]
					total=st.num_shares
					try:
						per=float("%.4f"%(bal/total))*100
					except ZeroDivisionError:
						per="Stop"
					append_msg("You have "+str(bal)+"/"+str(total)+" ("+str(per)+"%) shares")
				elif c[0]=="addMember":
					try:
						c[1]
					except IndexError:
						append_msg("Usage: addMember [player]")
						break
					append_msg("/res "+c[1],False)
				elif c[0]=="addTown":
					try:
						c[1]
					except IndexError:
						append_msg("Usage: addTown [town]")
						break
					append_msg("/town "+c[1],False)
				elif c[0]=="kinkshame":
					append_msg("Your kink is hereby shamed")
				elif c[0]=="ping":
					append_msg("pong")
				elif c[0]=="joinTown":
					append_msg("/town add "+sender,False)
				elif c[0]=="vote" and sender in st.members:
					try:
						c=[c[0]]+c[1].split() #Allow for multiple arguments
					except:
						append_msg("Usage: vote [make/vote/list/info] [etc]")
						continue
					if c[1]=="make":
						if st.members[sender]["shares"]/st.num_shares>=.01: #Check if sender has at least 1% of shares needed to make a vote
							try:
								if c[2] in st.votes or c[2] in st.votes_done:
									append_msg("There is already a vote named '"+c[2]+"'")
									continue
								c[3]=" ".join(c[3:]) #Connect all the words after c[2] to make one big proposition
								c=c[:4] #Get rid of everything after c[3]
								st.add_vote(c[2],c[3])
								append_msg("/tn "+sender+" has proposed a vote named '"+c[2]+"'. To learn more, use the command 'vote info "+c[2]+"'. To vote on it, use the command 'vote vote "+c[2]+" [yes/no]'",False)
							except:
								append_msg("Usage: vote make [vote name] [proposition]")
						else:
							append_msg("Sorry, you need to own at least 1% of the shares to propose a vote")
					elif c[1]=="vote":
						try:
							if c[2] in st.votes:
								if sender in st.votes[c[2]]["voted"]:
									append_msg("You've already voted in '"+c[2]+"'")
									continue
								stance=""
								if c[3].lower()=="yes":
									stance="yes"
								elif c[3].lower()=="no":
									stance="no"
								else:
									append_msg("Usage: vote vote [vote name] [yes/no]")
									continue
								st.vote(sender,c[2],stance)
							elif c[2] in st.votes_done:
								append_msg("'"+c[2]+"' has already finished. Use the command 'vote info "+c[2]+"' to learn more")
							else:
								append_msg("There is no vote named '"+c[2]+"'")
						except:
							append_msg("Usage: vote vote [vote name] [yes/no]")
					elif c[1]=="list":
						total=""
						for n in st.votes:
							total+=n+", "
						total=total[:-2]
						append_msg("Current votes: "+total)
					elif c[1]=="info":
						try:
							votes={} #Join both st.votes and st.votes_done so that players can get info on both
							votes.update(st.votes)
							votes.update(st.votes_done)
							if c[2] in votes:
								time_left=str(dt.timedelta(seconds=abs(int(votes[c[2]]["time"]+vote_wait-time.time()))))
								if c[2] in st.votes_done: #Timedelta messes up when seconds are negative, which would be when a vote is finished
									time_left="-"+time_left
								append_msg("Proposition: "+votes[c[2]]["proposition"]+"; For: "+str(votes[c[2]]["yes"])+"; Against: "+str(votes[c[2]]["no"])+"; Time left: "+time_left)
							else:
								append_msg("There is no vote named '"+c[2]+"'")
						except:
							append_msg("Usage: vote info [vote name]")
					else:
						append_msg("Usage: vote [make/vote/list/info] [etc]")
				elif c[0]=="deal" and sender in st.members:
					try:
						c=[c[0]]+c[1].split() #Allow for multiple arguments
					except:
						append_msg("Usage: deal [sell/accept/deny] [etc]")
						continue
					if c[1]=="sell":
						try:
							if c[2] in st.members and c[2]!=connection.auth_token.profile.name: #Players can't whisper to themselves, so check if the sender is trying to sell to the user
									shares=int(float(c[3]))
									if st.members[sender]["shares"]<shares or shares<0: #If sender is trying to sell more shares than they have or selling a negative number
										append_msg("Invalid amount of shares")
										continue
									c[4]="%.2f"%float(c[4])
									st.add_deal(c[2],sender,shares,float(c[4]))
									append_msg("/msg "+c[2]+" "+sender+" wants to sell you "+str(shares)+" shares for "+c[4]+"¥. Use the command 'deal accept [seller]' to accept, and 'deal deny [seller]' to deny",False)
							else:
								append_msg("You are not allowed to sell to "+c[2])
						except StockMarket.DuplicateDealException:
							append_msg("There is already a deal between you and "+c[2])
						except:
							append_msg("Usage: deal sell [buyer] [shares] [money]")
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
							append_msg("/msg "+c[2]+" "+sender+" has accepted your deal. Please pay me "+str(money)+"¥ now to sell them "+str(shares)+" shares",False)
						else:
							append_msg("You have no deals with "+c[2])
					elif c[1]=="deny":
						matched=False
						for d in st.deals: #Find matching deal
							if d["buy"]==sender and d["sell"]==c[2]:
								matched=True
								st.rm_deal(d)
								break
						if matched:
							append_msg("/msg "+c[2]+" "+sender+" has denied your deal",False)
						else:
							append_msg("You have no deals with "+c[2])
					else:
						append_msg("Usage: deal [sell/accept/deny] [etc]")
				else:
					append_msg("Unknown command. To seek help with the bot, please ask "+admin) 
		for p in pack: #Send each packet in pack to server
			connection.write_packet(p)
		with open("ChatLogs/"+dt.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")+".log","a",encoding="utf-8") as f: #Save chat messages in .log file for each day
			f.write("["+str(time.time())+"] "+t+"\n")
		print(t)
def keep_alive(packet): #Tell the server that we stll exist
	p=KeepAlivePacketServerbound()
	p.keep_alive_id=packet.keep_alive_id
	connection.write_packet(p)
	rm_votes=[] #Need this because you can't delete a key from a dctionary while it's being used in a for loop
	for v in st.votes:
		if st.votes[v]["time"]+vote_wait<=time.time(): #If the time has come for the vote to be finished
			p=ChatPacket()
			p.message="/tn The vote '"+v+"' has finished. Use the command 'vote info "+v+"' to learn more"
			connection.write_packet(p)
			rm_votes.append(v)
	for v in rm_votes:
		st.finish_vote(v)
	rm_votes=[]
	for v in st.votes_done:
		if st.votes_done[v]["time"]+vote_wait+vote_die<=time.time(): #If the time has come for the vote to die
			rm_votes.append(v)
	for v in rm_votes:
		st.rm_vote_done(v)
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
	c.register_packet_listener(process_chat,ChatMessagePacket)
	return c
if not os.path.exists("ChatLogs"):
	os.mkdir("ChatLogs")
connection=new_connection()
connection.connect()
print("Connected to server\n\n")
stop_loop=False
restart=False
while not stop_loop and not restart: #I'm pretty sure this needs to be here to keep the script running, but there's probably a more elegant solution
	time.sleep(5) #If this isn't here it bugs out
	if not connection.connected and not restart: #If for whatever reason we get unknowingly disconnected, get a new connection
		connection=new_connection()
		connection.connect()
if restart:
	time.sleep(5*60) #Hopefully enough time
	os.execv(__file__,sys.argv) #This probably only works in environments where you can do ./file
print("\n\nScript Ended")
