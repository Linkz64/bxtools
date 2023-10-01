import struct

# f = file
# v = value


#### GET



### Integer

## Signed Integers

def get_int32(f):
	"""
	Signed 32-bit Integer (4 bytes)
	Range: -2147483648 to 2147483647
	"""
	return struct.unpack("i", f.read(4))[0]

def get_int16(f):
	"""
	Signed 16-bit Integer (2 bytes)
	Range: -32768 to 32767

	"""
	return struct.unpack("h", f.read(2))[0]

def get_int8(f):
	"""
	Signed 8-bit Integer (1 byte)
	Range: -128 to 127
	"""
	return struct.unpack("b", f.read(1))[0]


## Unsigned Integers

def get_uint32(f):
	"""
	Unsigned 32-bit Integer (4 bytes)
	Range: 0 to 4294967295
	"""
	return struct.unpack("I", f.read(4))[0]

def get_uint16(f):
	"""
	Unsigned 16-bit Integer (2 bytes)
	Range: 0 to 65535
	"""
	return struct.unpack("H", f.read(2))[0]

def get_uint8(f):
	"""
	Signed 8-bit Integer (1 byte)
	Range: 0 to 255
	"""
	return struct.unpack("B", f.read(1))[0]



### Floating Point

def get_float32(f):
	"""
	Single 32-bit floating point value

	Length: 4 bytes
	Range: -inf to inf
	Examples:
		0x0000A040 = 5.0
		0x0000F0FF = nan  (Not a Number)
		0x0000F07F = nan
		0x0000807F = inf  (Positive infinity)
		0x000080FF = -inf (Negative infinity)
	"""
	return struct.unpack("f", f.read(4))[0]



### Get multiple values (f = file, x = amouint)

def get_int32x(f, x):
	return struct.unpack("i"*x, f.read(4*x))

def get_uint32x(f, x):
	return struct.unpack("I"*x, f.read(4*x))


def get_int16x(f, x):
	return struct.unpack("h"*x, f.read(2*x))

def get_uint16x(f, x):
	return struct.unpack("H"*x, f.read(2*x))


def get_int8x(f, x):
	return struct.unpack("b"*x, f.read(1*x))

def get_uint8x(f, x):
	return struct.unpack("B"*x, f.read(1*x))


def get_float32x(f, x):
	return struct.unpack("f"*x, f.read(4*x))


# Special

def get_vec2(f):
	"""2 float values"""
	return struct.unpack("fff", f.read(12))

def get_vec3(f):
	"""3 float values"""
	return struct.unpack("fff", f.read(12))




### Characters

def get_string(f, x):
	# A text string with length of x
	a = f.read(x)
	if a.startswith(b'\x00'):
		return ''
	else:
		return a.decode('utf-8').strip('\x00')




#### SET


### Integer

## Signed Integers

def set_int32(f, v): # Signed 32-bit Integer (4 bytes)
	return f.write(struct.pack("i", v)) # Range: -2147483648 to 2147483647

def set_int16(f, v): # Signed 16-bit Integer (2 bytes)
	return f.write(struct.pack("h", v)) # Range: -32768 to 32768

def set_int8(f, v): # Signed 8-bit Integer (1 byte)
	return f.write(struct.pack("b", v)) # Range: -128 to 128


## Unsigned Integers

def set_uint32(f, v): # Unsigned 32-bit Integer (4 bytes)
	return f.write(struct.pack("I", v)) # Range: 0 to 4294967295

def set_uint16(f, v): # Unsigned 16-bit Integer (2 bytes)
	return f.write(struct.pack("H", v)) # Range: 0 to 65535

def set_uint8(f, v): # Signed 8-bit Integer (1 byte)
	return f.write(struct.pack("B", v)) # Range: 0 to 255



### Floating Point

def set_float32(f, v): # Single 32-bit floating point value (4 bytes)
	return f.write(struct.pack("f", v)) # Range: -inf to +inf | Special: NaN | Example: 5.0



### Set multiple values from list


def set_int32s(f, v):
	return f.write(struct.pack("i"*len(v), *v))

def set_uint32s(f, v):
	return f.write(struct.pack("I"*len(v), *v))


def set_int16s(f, v):
	return f.write(struct.pack("h"*len(v), *v))

def set_uint16s(f, v):
	return f.write(struct.pack("H"*len(v), *v))


def set_int8s(f, v):
	return f.write(struct.pack("b"*len(v), *v))

def set_uint8s(f, v):
	return f.write(struct.pack("B"*len(v), *v))


def set_float32s(f, v):
	return f.write(struct.pack("f"*len(v), *v))


def set_vec3(f, v):
	return f.write(struct.pack('fff', v[0], v[1], v[2]))

def set_vec2(f, v):
	return f.write(struct.pack('ff', v[0], v[1]))


### Characters

def set_str8(f, v):
	# A text string with length and value of v
	return f.write(bytes(v, 'utf-8')) # NOT TESTED YET

	# other methods

	# s = bytes(v, 'utf-8') # or s = string.encode()
	# struct.pack("b", len(s)) + s

	# or struct.pack("b", len(v)) + v.encode()


#def set_name(f, v, x): # file, value, max length
#
#    vLen = len(v)
#    s = bytes(v, 'utf-8')
#
#    if vLen < x:
#        addNulls = b'\00' * (x - vLen)
#        s += addNulls
#    if vLen > x:
#        s = s[:x]
#
#    return f.write(s)







### GET FROM BUFFERS


def bget_int32(b, o):
	return struct.unpack_from('i', b, offset=o)[0]

def bget_uint32(b, o):
	return struct.unpack_from('I', b, offset=o)[0]

def bget_int16(b, o):
	return struct.unpack_from('h', b, offset=o)[0]

def bget_uint16(b, o):
	return struct.unpack_from('H', b, offset=o)[0]

def bget_int8(b, o):
	return struct.unpack_from('b', b, offset=o)[0]

def bget_uint8(b, o):
	return struct.unpack_from('B', b, offset=o)[0]


def bget_float32(b, o):
	return struct.unpack_from('f', b, offset=o)[0]


def bget_vec2(b, o):
	return struct.unpack_from("ff", b, offset=o)

def bget_vec3(b, o):
	return struct.unpack_from("fff", b, offset=o)

def bget_vec4(b, o):
    return struct.unpack_from("ffff", b, offset=o)




def bget_vec2_int16_a(b, off):
    ints = struct.unpack_from('hh', b, offset=off)
    return (ints[0] / 65535, ints[1] / 65535)
def bget_vec2_uint16_a(b, off):
    ints = struct.unpack_from('HH', b, offset=off)
    return (ints[0] / 65535, ints[1] / 65535)

def bget_vec2_int16_b(b, off):
    ints = struct.unpack_from('hh', b, offset=off)
    return (ints[0] / 32768, ints[1] / 32768)
def bget_vec2_uint16_b(b, off):
    ints = struct.unpack_from('HH', b, offset=off)
    return (ints[0] / 32768, ints[1] / 32768)

def bget_vec2_int16_c(b, off):
    ints = struct.unpack_from('hh', b, offset=off)
    return (ints[0] / 4096, ints[1] / 4096)
def bget_vec2_uint16_c(b, off):
    ints = struct.unpack_from('HH', b, offset=off)
    return (ints[0] / 4096, ints[1] / 4096)

def bget_vec3_int16_a(b, off):
    ints = struct.unpack_from('hhh', b, offset=off)
    return (ints[0] / 65535, ints[1] / 65535, ints[2] / 65535)


def bget_string_old(b, o, x):
	"""
	This one removes nulls and merges the string
	b = buffer
	o = offset
	x = character count
	"""
	a = struct.unpack_from('s'*x, b, offset=o)

	string = ''
	for i in range(x):
		string += bytes(a[i]).decode('utf-8').strip('\x00') # .strip('\x00')

	return string


def bget_string(b, o, x):
	"""
	b = buffer
	o = offset
	x = character count
	"""
	a = struct.unpack_from('s'*x, b, offset=o)

	string = ''
	for i in range(x):
		if a[i] != b'\x00':
			string += bytes(a[i]).decode('utf-8')
		else:
			break # exit loop
	return string