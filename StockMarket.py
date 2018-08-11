import json
import os
import time
class StockMarket:
	class DuplicateDealException(Exception):
		pass
	def __init__(self,nation,direct="Storage"):
		self.nation=nation
		self.direct=direct
		self.deals=[] #Won't survive if script is reloaded because they should be finished quickly
		self.votes={}
		if os.path.exists(direct+"/votes.json"):
			with open(direct+"/votes.json") as f:
				self.votes=json.loads(f.read())
		self.votes_done={}
		if os.path.exists(direct+"/votes_done.json"):
			with open(direct+"/votes_done.json") as f:
				self.votes_done=json.loads(f.read())
		self.members={}
		if os.path.exists(direct+"/members.json"):
			with open(direct+"/members.json") as f:
				self.members=json.loads(f.read())
		self.towns={}
		if os.path.exists(direct+"/towns.json"):
			with open(direct+"/towns.json") as f:
				self.towns=json.loads(f.read())
		self.last_update=0
		if os.path.exists(direct+"/last_update.txt"):
			with open(direct+"/last_update.txt") as f:
				self.last_update=float(f.read())
		self.towny={"towny":False,"name":"","player":False,"town":False,"nation":False}
		if not os.path.exists(direct):
			os.mkdir(direct)
	@property
	def num_shares(self):
		total=0
		for i in self.members:
			total+=self.members[i]["shares"]
		return total
	def add_vote(self,name,prop):
		self.votes[name]={"proposition":prop,"yes":0,"no":0,"time":time.time(),"voted":[]}
		self.save_votes()
	def rm_vote(self,name):
		self.votes.pop(name)
		self.save_votes(self.direct+"/votes.json")
	def vote(self,voter,name,stance):
		self.votes[name][stance]+=self.members[voter]["shares"]
		self.votes[name]["voted"].append(voter)
		self.save_votes()
	def finish_vote(self,name):
		self.votes_done[name]=self.votes[name]
		self.rm_vote(name)
		self.save_votes_done()
	def rm_vote_done(self,name):
		self.votes_done.pop(name)
		self.save_votes_done()
	def add_deal(self,buy,sell,amount,money):
		for i in self.deals:
			if buy==i["buy"] and sell==i["sell"]:
				raise StockMarket.DuplicateDealException
		self.deals.append({"buy":buy,"sell":sell,"amount":amount,"money":money,"accepted":False})
	def rm_deal(self,deal):
		self.deals.remove(deal)
	def transfer_shares(self,amount,buy,sell):
		if self.members[sell]["shares"]<amount:
			raise Exception("Not enough shares")
		self.members[sell]["shares"]-=amount
		self.members[buy]["shares"]+=amount
		self.save_members(self.direct+"/members.json")
	def save_update(self,file=None):
		if file==None:
			file=self.direct+"/last_update.txt"
		with open(file,"w") as f:
			f.write(str(self.last_update))
	def save_votes(self,file=None):
		if file==None:
			file=self.direct+"/votes.json"
		t=json.dumps(self.votes,indent=2,sort_keys=True)
		with open(file,"w") as f:
			f.write(t)
	def save_votes_done(self,file=None):
		if file==None:
			file=self.direct+"/votes_done.json"
		t=json.dumps(self.votes_done,indent=2,sort_keys=True)
		with open(file,"w") as f:
			f.write(t)
	def save_towns(self,file=None):
		if file==None:
			file=self.direct+"/towns.json"
		t=json.dumps(self.towns,indent=2,sort_keys=True)
		with open(file,"w") as f:
			f.write(t)
	def save_members(self,file=None):
		if file==None:
			file=self.direct+"/members.json"
		t=json.dumps(self.members,indent=2,sort_keys=True)
		with open(file,"w") as f:
			f.write(t)
	def rm_dupe(dic,old,new): #If player or town has changed names, remove the old entry
		if dic[old]["uuid"]==dic[new]["uuid"]:
			dic.pop(old)
		return dic
	def process(self,packet): #This should be put in a ChatPacket function
		self.process_towny(packet)
		self.process_town(packet)
		self.process_player(packet)
	def process_chat(self,packet): #Processes chat packets into text
		if packet.position==2:
			return ""
		text=json.loads(packet.json_data)
		t=""
		try:
			t=text["text"]
			text=text["extra"]
			for j in text:
				t+=j["text"]
		except KeyError as e:
			pass
		return t
	def process_towny(self,packet): #Determines if bot is about to see player or nation info
		t=self.process_chat(packet)
		if t.startswith(".oOo."):
			self.towny["towny"]=True #When towny is true, wait for next line to determine whether town or player
			self.towny["name"]=t.split("[ ",1)[1].split(" ]",1)[0]
		elif self.towny["towny"]:
			if t.startswith("Board: "):
				self.towny["town"]=True
			elif t.startswith("Registered: "):
				self.towny["player"]=True
			self.towny["towny"]=False
	def process_player(self,packet): #Processes towny information into an entry for members
		if not self.towny["player"]:
			return
		t=self.process_chat(packet)
		if t.startswith("Registered: "): #First line of player info
			self.towny["name"]=self.towny["name"].split(" (",1)[0].split()[-1]
			if self.towny["name"] in self.members: #If player already registered, stop the function
				return
			self.members[self.towny["name"]]={"shares":0}
		elif t.startswith("UUID: "):
			self.members[self.towny["name"]]["uuid"]=t[6:]
		elif t.startswith("Town: "):
			n=t[6:].split(" (",1)[0]
			if n not in self.towns: #If town isn't registered, player isn't part of nation, so stop the function after removing name from all towns
				for name in self.towns:
					try:
						self.towns[name]["res"].remove(self.towny["name"])
						share_dist=self.members[self.towny["name"]]["shares"]/(len(self.members)-1)
						for m in self.members: #Redistribute their shares evenly
							if m==self.towny["name"]:
								continue
							self.members[m]["shares"]+=share_dist
					except ValueError:
						continue
				self.save_towns()
				self.members.pop(self.towny["name"])
				self.towny["name"]=""
				self.towny["player"]=False
				self.save_members()
				return
			if self.towny["name"] not in self.towns[n]["res"]: #If player is in a registered town but isn't included in our records as being in that town, update our records
				self.towns[n]["res"].append(self.towny["name"])
				self.save_towns()
			global town
			town=None #Indicates we have reached the end of the player's info
		else:
			try:
				town
			except NameError:
				return
			#Have to reset self.towny
			self.towny["name"]=""
			self.towny["player"]=False
			del town
			self.save_members()
	def process_town(self,packet): #Processes towny information into an entry for towns
		if not self.towny["town"]:
			return
		t=self.process_chat(packet)
		if t.startswith("Board: "): #First line of town info
			self.towny["name"]=self.towny["name"].split(" (",1)[0]
			if self.towny["name"] not in self.towns:
				self.towns[self.towny["name"]]={}
		if t.startswith("UUID: "):
			self.towns[self.towny["name"]]["uuid"]=t[6:]
		elif t.startswith("Mayor: "):
			self.towns[self.towny["name"]]["mayor"]=t[7:].split()[1]
		elif t.startswith("Nation: "):
			if t.split()[1]!=self.nation: #If town isn't in our nation, reset self.towny and stop the function
				self.towns.pop(self.towny["name"])
				self.towny["name"]=""
				self.towny["town"]=False
				self.save_towns()
		elif t.startswith("Residents ["): #Try to record as many residents as we can see
			try:
				self.towns[self.towny["name"]]["res"]
			except KeyError: #have to create the "res" list if town hasn't been registered yet
				self.towns[self.towny["name"]]["res"]=[]
			self.towns[self.towny["name"]]["num"]=int(t.split("[",1)[1].split("]",1)[0])
			global n #Use this variable to check that we're almost done getting info
			n=0
			for r in t.split("]: ",1)[1].split(", "):
				if r and n<self.towns[self.towny["name"]]["num"]:
					res=r.split()[-1]
					if res not in self.towns[self.towny["name"]]["res"]: #To avoid duplicates
						self.towns[self.towny["name"]]["res"].append(res)
					n+=1
		else:
			try:
				n
			except NameError:
				return
			for r in t.split(", "):
				if n<self.towns[self.towny["name"]]["num"] and r!="and more... ":
					if not r:
						return
					res=r.strip(" ")
					if res not in self.towns[self.towny["name"]]["res"]: #To avoid duplicates
						self.towns[self.towny["name"]]["res"].append(res)
					n+=1
			self.towns[self.towny["name"]].pop("num")
			self.towny["name"]=""
			self.towny["town"]=False
			del n
			self.save_towns()
