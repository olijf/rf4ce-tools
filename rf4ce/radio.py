# -*- coding: utf-8 -*-
"""
Low level gnuradio graphs for 802.15.4.
"""
import os
import sys
sys.path.append(os.environ.get('GRC_HIER_PATH', os.path.expanduser('~/.grc_gnuradio')))

from math import pi, sin
import numpy

from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import iio
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
#from ieee802_15_4_oqpsk_phy import ieee802_15_4_oqpsk_phy  # grc-generated hier_block
import pmt
import signal


from .autognuradio.ieee802_15_4_oqpsk_phy import ieee802_15_4_oqpsk_phy

class RxFlow(gr.top_block):

	def __init__(self, channel, processor, device="pluto-sdr", pcap_filename=None):
		gr.top_block.__init__(self, "Sniffer Flow")

		self.processor = processor

		##################################################
		# Variables
		##################################################
		self.channel = channel
		self.device = device

		##################################################
		# Blocks
		##################################################
		if self.device == "pluto-sdr":
			self.sdr_source = iio.fmcomms2_source_fc32('' if '' else iio.get_pluto_uri(), [True, True], 32768)
			self.sdr_source.set_len_tag_key('packet_len')
			self.sdr_source.set_frequency(self.get_center_freq())
			self.sdr_source.set_samplerate(int(4e6))
			self.sdr_source.set_gain_mode(0, 'slow_attack')
			self.sdr_source.set_gain(0, 64)
			self.sdr_source.set_quadrature(True)
			self.sdr_source.set_rfdc(True)
			self.sdr_source.set_bbdc(True)
			self.sdr_source.set_filter_params('Auto', '', 0, 0)
        
		#self.sdr_source = iio.device_source('192.168.2.1', self.get_center_freq(),
		#   int(4e6), int(20e6), 0x8000, True, True, True, "manual", 50, '', True)
            
		self.ieee802_15_4_oqpsk_phy_0 = ieee802_15_4_oqpsk_phy(pcap_filename)
		self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_gr_complex*1)

		self.msg_out_0 = msg_sink_block(self.processor)

		##################################################
		# Connections
		##################################################
		self.msg_connect((self.ieee802_15_4_oqpsk_phy_0, 'rxout'), (self.msg_out_0, 'msg_in'))
		self.connect((self.ieee802_15_4_oqpsk_phy_0, 0), (self.blocks_null_sink_0, 0))
		self.connect((self.sdr_source, 0), (self.ieee802_15_4_oqpsk_phy_0, 0))

	def get_channel(self):
		return self.channel

	def set_channel(self, channel):
		self.channel = channel
		if self.device == "pluto-sdr":
			self.sdr_source.set_frequency(self.get_center_freq())

	def get_center_freq(self):
		return 1000000 * (2400 + 5 * (self.channel - 10))



class msg_sink_block(gr.basic_block):

	def __init__(self, processor):

		gr.basic_block.__init__(
			 self,
			 name="msg_block",
			 in_sig=None,
			 out_sig=None)

		self.processor = processor
		self.message_port_register_in(pmt.intern('msg_in'))
		self.set_msg_handler(pmt.intern('msg_in'), self.handle_msg)

	def handle_msg(self, msg):
		messages = pmt.to_python(msg)
		for message in messages:
			if type(message) == numpy.ndarray:
				self.processor.feed(message.tostring())


class msg_block_source(gr.basic_block):

	def __init__(self):

		gr.basic_block.__init__(
			 self,
			 name="msg_block",
			 in_sig=None,
			 out_sig=None)

		self.message_port_register_out(pmt.intern('msg_out'))
	
	def transmit(self, data):
		vector = pmt.make_u8vector(len(data), 0)
		for i, c in enumerate(data):
			pmt.u8vector_set(vector, i, ord(data[i]))
		pdu = pmt.cons(pmt.make_dict(), vector)
		self.message_port_pub(pmt.intern('msg_out'), pdu)
