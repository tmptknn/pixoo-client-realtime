"""
Pixoo 
"""

from datetime import datetime
from lib2to3.pgen2.literals import simple_escapes
import sys
import socket
from threading import currentThread
from time import sleep
from PIL import Image
from binascii import unhexlify, hexlify
from math import log10, ceil
import random

from jinja2 import Undefined

class Pixoo(object):

  CMD_SET_SYSTEM_BRIGHTNESS = 0x74
  CMD_SPP_SET_USER_GIF = 0xb1
  CMD_DRAWING_ENCODE_PIC = 0x5b
  CMD_SET_DATE_TIME = 0x18

  BOX_MODE_CLOCK=0
  BOX_MODE_TEMP=1
  BOX_MODE_COLOR=2
  BOX_MODE_SPECIAL=3

  instance = None

  def __init__(self, mac_address):
    """
    Constructor
    """
    self.mac_address = mac_address
    self.btsock = None
    self.awake_timer = 0


  @staticmethod
  def get():
    if Pixoo.instance is None:
      Pixoo.instance = Pixoo(Pixoo.BDADDR)
      Pixoo.instance.connect()
    return Pixoo.instance

  def connect(self):
    """
    Connect to SPP.
    """

    while True:
      try:
          self.btsock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
          self.btsock.connect((self.mac_address, 1))
          self.set_system_brightness(100)
          return
      except OSError as oe:
          print(oe)
          sleep(0.5)
          continue
      

  def disconnect(self):
    self.btsock.close()

  def __spp_frame_checksum(self, args):
    """
    Compute frame checksum
    """
    return sum(args[1:])&0xffff


  def __spp_frame_encode(self, cmd, args):
    """
    Encode frame for given command and arguments (list).
    """
    payload_size = len(args) + 3

    # create our header
    frame_header = [1, payload_size & 0xff, (payload_size >> 8) & 0xff, cmd]

    # concatenate our args (byte array)
    frame_buffer = frame_header + args

    # compute checksum (first byte excluded)
    cs = self.__spp_frame_checksum(frame_buffer)

    # create our suffix (including checksum)
    frame_suffix = [cs&0xff, (cs>>8)&0xff, 2]

    # return output buffer
    return frame_buffer+frame_suffix


  def send(self, cmd, args):
    """
    Send data to SPP.
    """
    spp_frame = self.__spp_frame_encode(cmd, args)
    if self.btsock is not None:
      nb_sent = self.btsock.send(bytes(spp_frame))


  def set_system_brightness(self, brightness):
    """
    Set system brightness.
    """
    self.send(Pixoo.CMD_SET_SYSTEM_BRIGHTNESS, [brightness&0xff])


  def set_date_time(self, time=None):
    """
    Set date and time.
    """
    if time == None:
      time = datetime.now()

    cyear = int(time.year)
    shortyear = int(cyear%100)
    century = int((cyear-cyear%100)/100)
    month = int(time.month)
    day = int(time.day)
    hour = int(time.hour)
    minute = int(time.minute)
    second = int(time.second)
    timearray = [century&0xff,shortyear&0xff,month&0xff,day&0xff,hour&0xff,minute&0xff,second&0xff,0x00]
    self.send(Pixoo.CMD_SET_DATE_TIME, timearray)

  def set_box_mode(self, boxmode, visual=0, mode=0):
    """
    Set box mode.
    """
    self.send(0x45, [boxmode&0xff, visual&0xff, mode&0xff])


  def set_color(self, r,g,b):
    """
    Set color.
    """
    self.send(0x6f, [r&0xff, g&0xff, b&0xff])

  def encode_image(self, filepath):
    img = Image.open(filepath)
    return self.encode_raw_image(img)

  def encode_raw_image(self, img):
    """
    Encode a 16x16 image.
    """
    # ensure image is 16x16
    w,h = img.size
    if w == h:
      # resize if image is too big
      if w > 16:
        img = img.resize((16,16))

      # create palette and pixel array
      pixels = []
      palette = []
      for y in range(16):
        for x in range(16):
          pix = img.getpixel((x,y))
          
          if len(pix) == 4:
            r,g,b,a = pix
          elif len(pix) == 3:
            r,g,b = pix
          if (r,g,b) not in palette:
            palette.append((r,g,b))
            idx = len(palette)-1
          else:
            idx = palette.index((r,g,b))
          pixels.append(idx)

      # encode pixels
      bitwidth = ceil(log10(len(palette))/log10(2))
      nbytes = ceil((256*bitwidth)/8.)
      encoded_pixels = [0]*nbytes

      encoded_pixels = []
      encoded_byte = ''
      for i in pixels:
        encoded_byte = bin(i)[2:].rjust(bitwidth, '0') + encoded_byte
        if len(encoded_byte) >= 8:
            encoded_pixels.append(encoded_byte[-8:])
            encoded_byte = encoded_byte[:-8]
      encoded_data = [int(c, 2) for c in encoded_pixels]
      encoded_palette = []
      for r,g,b in palette:
        encoded_palette += [r,g,b]
      return (len(palette), encoded_palette, encoded_data)
    else:
      print('[!] Image must be square.')

  def draw_gif(self, filepath, speed=100):
    """
    Parse Gif file and draw as animation.
    """
    # encode frames
    frames = []
    timecode = 0
    anim_gif = Image.open(filepath)
    for n in range(anim_gif.n_frames):
      anim_gif.seek(n)
      nb_colors, palette, pixel_data = self.encode_raw_image(anim_gif.convert(mode='RGB'))
      frame_size = 7 + len(pixel_data) + len(palette)
      frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, timecode&0xff, (timecode>>8)&0xff, 0, nb_colors]
      frame = frame_header + palette + pixel_data
      frames += frame
      timecode += speed

    # send animation
    nchunks = ceil(len(frames)/200.)
    total_size = len(frames)
    for i in range(nchunks):
      chunk = [total_size&0xff, (total_size>>8)&0xff, i]
      self.send(0x49, chunk+frames[i*200:(i+1)*200])
   

  def draw_anim(self, filepaths, speed=100):
    timecode=0

    # encode frames
    frames = []
    n=0
    for filepath in filepaths:
      nb_colors, palette, pixel_data = self.encode_image(filepath)
      frame_size = 7 + len(pixel_data) + len(palette)
      frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, timecode&0xff, (timecode>>8)&0xff, 0, nb_colors]
      frame = frame_header + palette + pixel_data
      frames += frame
      timecode += speed
      n += 1
    
    # send animation
    nchunks = ceil(len(frames)/200.)
    total_size = len(frames)
    for i in range(nchunks):
      chunk = [total_size&0xff, (total_size>>8)&0xff, i]
      self.send(0x49, chunk+frames[i*200:(i+1)*200])


  def draw_pic(self, filepath):
    """
    Draw encoded picture.
    """
    nb_colors, palette, pixel_data = self.encode_image(filepath)
    frame_size = 7 + len(pixel_data) + len(palette)
    frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, 0, 0, 0, nb_colors]
    frame = frame_header + palette + pixel_data
    prefix = [0x0, 0x0A,0x0A,0x04]
    self.send(0x44, prefix+frame)

  def draw_image(self, display):
    """
    Encode a 16x16 image.
    """
    # ensure image is 16x16
    w = 16
    h = 16

    # create palette and pixel array
    pixels = []
    palette = []
    for y in range(16):
      for x in range(16):
        #pix = img.getpixel((x,y))
        r, g, b = display.get_pixel(x,y)
        #if len(pix) == 4:
        #  r,g,b,a = pix
        # elif len(pix) == 3:
        #r = random.randint(0,5)*20
        #g = random.randint(0,5)*20
        #b = random.randint(0,5)*20



        if (r,g,b) not in palette:
          if len(palette) <255:
            palette.append((r,g,b))
            idx = len(palette)-1
          else:
            idx = 255
        else:
          idx = palette.index((r,g,b))
        pixels.append(idx)

    # encode pixels
    bitwidth = ceil(log10(len(palette))/log10(2))
    nbytes = ceil((256*bitwidth)/8.)
    encoded_pixels = [0]*nbytes

    encoded_pixels = []
    encoded_byte = ''
    for i in pixels:
      encoded_byte = bin(i)[2:].rjust(bitwidth, '0') + encoded_byte
      if len(encoded_byte) >= 8:
          encoded_pixels.append(encoded_byte[-8:])
          encoded_byte = encoded_byte[:-8]
    encoded_data = [int(c, 2) for c in encoded_pixels]
    encoded_palette = []
    for r,g,b in palette:
      encoded_palette += [r,g,b]
    return (len(palette), encoded_palette, encoded_data)


  def animate(self, display):
    for i in range(1000):
      nb_colors, palette, pixel_data = self.draw_image(display)
      frame_size = 7 + len(pixel_data) + len(palette)
      frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, 0, 0, 0, nb_colors]
      frame = frame_header + palette + pixel_data
      prefix = [0x0, 0x0A,0x0A,0x04]
      self.send(0x44, prefix+frame)
      sleep(0.05)
      display.step()


  def draw(self, display):
    try:
      nb_colors, palette, pixel_data = self.draw_image(display)
      frame_size = 7 + len(pixel_data) + len(palette)
      frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, 0, 0, 0, nb_colors]
      frame = frame_header + palette + pixel_data
      prefix = [0x0, 0x0A,0x0A,0x04]
      self.send(0x44, prefix+frame)
      if self.awake_timer ==100:
        self.set_system_brightness(100)
        self.awake_timer = 0

      self.awake_timer += 1
      sleep(0.05)
    #  except ConnectionResetError as cre:
    #     print(str(cre))
    except OSError as oe:
        print(oe)
        self.connect()
        


class PixooMax(Pixoo):
  """
  PixooMax class, derives from Pixoo but does not support animation yet.
  """
  
  def __init__(self, mac_address):
    super().__init__(mac_address)

  def draw_pic(self, filepath):
    """
    Draw encoded picture.
    """
    nb_colors, palette, pixel_data = self.encode_image(filepath)
    frame_size = 8 + len(pixel_data) + len(palette)
    frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, 0, 0, 3, nb_colors&0xff, (nb_colors>>8)&0xff]
    frame = frame_header + palette + pixel_data
    prefix = [0x0, 0x0A,0x0A,0x04]
    self.send(0x44, prefix+frame)

  def draw_gif(self, filepath, speed=100):
    raise 'NotYetImplemented'

  def draw_anim(self, filepaths, speed=100):
    raise 'NotYetImplemented'

  def encode_image(self, filepath):
    img = Image.open(filepath)
    img = img.convert(mode="P", palette=Image.ADAPTIVE, colors=256).convert(mode="RGB")
    return self.encode_raw_image(img)

  def encode_raw_image(self, img):
    """
    Encode a 32x32 image.
    """
    # ensure image is 32x32
    w,h = img.size
    if w == h:
      # resize if image is too big
      if w > 32:
        img = img.resize((32,32))

      # create palette and pixel array
      pixels = []
      palette = []
      for y in range(32):
        for x in range(32):
          pix = img.getpixel((x,y))
          
          if len(pix) == 4:
            r,g,b,a = pix
          elif len(pix) == 3:
            r,g,b = pix
          if (r,g,b) not in palette:
            palette.append((r,g,b))
            idx = len(palette)-1
          else:
            idx = palette.index((r,g,b))
          pixels.append(idx)

      # encode pixels
      bitwidth = ceil(log10(len(palette))/log10(2))
      nbytes = ceil((256*bitwidth)/8.)
      encoded_pixels = [0]*nbytes

      encoded_pixels = []
      encoded_byte = ''

      # Create our pixels bitstream
      for i in pixels:
        encoded_byte = bin(i)[2:].rjust(bitwidth, '0') + encoded_byte
      
      # Encode pixel data
      while len(encoded_byte) >= 8:
        encoded_pixels.append(encoded_byte[-8:])
        encoded_byte = encoded_byte[:-8]

      # If some bits left, pack and encode
      padding = 8 - len(encoded_byte)
      encoded_pixels.append(encoded_byte.rjust(bitwidth, '0'))

      # Convert into array of 8-bit values
      encoded_data = [int(c, 2) for c in encoded_pixels]
      encoded_palette = []
      for r,g,b in palette:
        encoded_palette += [r,g,b]
      return (len(palette), encoded_palette, encoded_data)
    else:
      print('[!] Image must be square.')

if __name__ == '__main__':
  if len(sys.argv) >= 3:
    pixoo_baddr = sys.argv[1]
    img_path = sys.argv[2]

    pixoo = PixooMax(pixoo_baddr)
    pixoo.connect()

    # mandatory to wait at least 1 second
    sleep(1)

    # draw image
    pixoo.draw_pic(img_path)
  else:
    print('Usage: %s <Pixoo BT address> <image path>' % sys.argv[0])
