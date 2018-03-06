"""
micropython driver for MAX31856 thermocouple interface.

https://datasheets.maximintegrated.com/en/ds/MAX31856.pdf
"""

try:
    import ustruct as struct
    from ucollections import OrderedDict
except ImportError:
    import struct
    from collections import OrderedDict

    def const(x):
        return x

CR0_REG = const(0x00)
CR0_AUTOCONVERT = const(0x80)
CR0_ONESHOT = const(0x40)
CR0_OCFAULT1 = const(0x20)
CR0_OCFAULT0 = const(0x10)
CR0_CJ = const(0x08)
CR0_FAULT = const(0x04)
CR0_FAULTCLR = const(0x02)
CR0_50HZ = const(0x01)

CR1_REG = const(0x01)
CR1_AVGSEL1 = const(0x00)
CR1_AVGSEL2 = const(0x10)
CR1_AVGSEL4 = const(0x20)
CR1_AVGSEL8 = const(0x30)
CR1_AVGSEL16 = const(0x40)

MASK_REG = const(0x02)
CJHF_REG = const(0x03)
CJLF_REG = const(0x04)
LTHFTH_REG = const(0x05)
LTHFTL_REG = const(0x06)
LTLFTH_REG = const(0x07)
LTLFTL_REG = const(0x08)
CJTO_REG = const(0x09)
CJTH_REG = const(0x0A)
CJTL_REG = const(0x0B)
LTCBH_REG = const(0x0C)
LTCBM_REG = const(0x0D)
LTCBL_REG = const(0x0E)
SR_REG = const(0x0F)

FAULT_CJRANGE = const(0x80)
FAULT_TCRANGE = const(0x40)
FAULT_CJHIGH = const(0x20)
FAULT_CJLOW = const(0x10)
FAULT_TCHIGH = const(0x08)
FAULT_TCLOW = const(0x04)
FAULT_OVUV = const(0x02)
FAULT_OPEN = const(0x01)

faults = {
    0x01: 'open',
    0x02: 'OV/UV',
    0x04: 'tclow',
    0x08: 'tchigh',
    0x10: 'cjlow',
    0x20: 'cjhigh',
    0x40: 'tcrange',
    0x80: 'cjrange',
}

tctypes = {
    'B': 0,
    'E': 1,
    'J': 2,
    'K': 3,
    'N': 4,
    'R': 5,
    'S': 6,
    'T': 7,
    'VG8': 8,
    'VG32': 12
}


if True:
    def nullprint(*args, **kwargs):
        pass

    myprint = nullprint
else:
    myprint = print

CR0_DEFAULT = const(CR0_OCFAULT0 |
              CR0_FAULTCLR |
              CR0_AUTOCONVERT |
              CR0_50HZ)

CR1_DEFAULT = CR1_AVGSEL16


class Max31856(object):

    def __init__(self, spi_obj, cs_pin, tc_type='K',cr0=CR0_DEFAULT, cr1=CR1_DEFAULT):
        """Initialise MAX31856
        spi_obj is uPython SPI object
        cs_pin is Pin object for chip select
        tc_type is thermocouple type code, see tctypes dict

        Default values of cr0, cr1 give autoconversion with 16 sample averaging,
        50Hz rejection, open circuit fault detection
        """
        self.tc_type = tc_type
        self.spi = spi_obj
        self.cs = cs_pin
        self.cs.value(1)
        self.spi.init(baudrate=1000000, polarity=0, phase=1)

        self.regs = bytearray(16)
        self.read_regs(CR0_REG, 16)

        self.regs[CR0_REG] = cr0
        self.regs[CR1_REG] = (cr1 & 0xF0) | tctypes[tc_type]
        self.regs[MASK_REG] = 0  # unmask all faults
        self.write_regs(CR0_REG, 3)

        self.read_regs(CR0_REG, 3)

    def write_regs(self, start_addr, count):
        """write some bytes from self.regs"""
        self.cs.value(0)
        b = bytearray((start_addr | 0x80,))  # MSB is write indicator
        b += self.regs[start_addr:start_addr+count]
        self.spi.write(b)
        self.cs.value(1)
        myprint('Write %d to %d' % (count, start_addr), b[1:])

    def read_regs(self, start_addr, count):
        """read some bytes into self.regs"""
        self.cs.value(0)
        b = bytearray(count+1)
        b[0] = start_addr
        self.spi.write_readinto(b, b)
        self.cs.value(1)
        myprint('Read %d from %d' % (count, start_addr), b[1:])
        self.regs[start_addr:start_addr+count] = b[1:]

    def read_data(self):
        """Read the interesting data registers:
        cold junction and thermocouple temperature and status.
        """
        self.read_regs(CJTH_REG, 6)

    def one_shot(self):
        """Trigger one-shot reading, disable autoconversion"""
        self.regs[CR0_REG] &= ~CR0_AUTOCONVERT
        self.regs[CR0_REG] |= CR0_ONESHOT
        self.write_regs(CR0_REG, 1)
        time.sleep(200)
        self.read_data()

    def temperature(self, read_chip=False):
        """Calculate the thermocouple temperature.
        If read_chip, read from chip into register mirror"""
        if read_chip:
            self.read_data()

        t = struct.unpack('>i', self.regs[LTCBH_REG:LTCBH_REG+4])[0]
        temp = t * 9.53674316406e-7  # shift 20 bits right
        return temp

    def faults(self, read_chip=False):
        """Check for fault, returns code, description"""
        if read_chip:
            self.read_data()

        f = self.regs[SR_REG]

        if f == 0:
            return 0, ''

        fl = []
        for bit, desc in faults.items():
            if f & bit:
                fl.append(desc)

        fs = '+'.join(fl)

        return f, fs

    def cold_junction(self, read_chip=False):
        """Calculate cold junction temperature"""
        if read_chip:
            self.read_data()

        t = struct.unpack('>h', self.regs[CJTH_REG:CJTL_REG+1])[0]
        return t * (1 / 256.0)
