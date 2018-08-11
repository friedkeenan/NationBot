import struct
from nbt import nbt
from io import BytesIO
import minecraft
from minecraft.networking.packets import Packet
from minecraft.networking.types import *
class Slot:
	def __init__(self,id=-1,item_count=None,item_damage=None,NBT=None):
		self.id=id
		self.count=item_count
		self.damage=item_damage
		self.NBT=NBT
class SlotType(Type):
	@staticmethod
	def read(file_object):
		id=Short.read(file_object)
		if id==-1:
			return Slot()
		count=Byte.read(file_object)
		dmg=Short.read(file_object)
		NBT=nbt.NBTFile(buffer=file_object.bytes)
		return Slot(id,count,dmg,NBT)
	@staticmethod
	def send(value,socket):
		send=bytes()
		send+=struct.pack(">h",value.id)
		send+=struct.pack(">b",value.count)
		send+=struct.pack(">h",value.damage)
		NBT=BytesIO()
		value.NBT.write_file(buffer=NBT)
		send+=NBT.getvalue()
		socket.send(send)
class ClickWindowPacket(Packet):
	id=0x07
	packet_name="click window"
	definition=[
		{"window_id":UnsignedByte},
		{"slot":Short},
		{"button":Byte},
		{"action_number":Short},
		{"mode":VarInt},
		{"clicked":SlotType}]
class SetSlotPacket(Packet):
	id=0x16
	packet_name="set slot"
	definition=[
		{"window_id":Byte},
		{"slot":Short},
		{"slot_data":SlotType}]
def add_play_packets(func):
	def wrap(func,context):
		packets=func(context)
		packets.add(SetSlotPacket)
		return packets
	return staticmethod(lambda x:wrap(func,x))
minecraft.networking.connection.PlayingReactor.get_clientbound_packets=add_play_packets(minecraft.networking.connection.PlayingReactor.get_clientbound_packets)
