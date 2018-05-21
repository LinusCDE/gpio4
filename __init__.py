#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 3 16:36:26 2018

@author: hank
@page:   https://github.com/hankso
"""
import os
import threading
from . import constants


class SysfsGPIO(object):
    attributes = ('value', 'direction', 'active_low', 'edge')

    def __init__(self, pin):
        self.pin = pin
        self.path = '/sys/class/gpio/gpio{:d}'.format(pin)
        self._file = {}
        self._write_lock = threading.Lock()
        self._read_lock = threading.Lock()

    @property
    def export(self):
        return os.path.exists(self.path)

    @property
    def value(self):
        return int(self._read('value'))

    @property
    def direction(self):
        return self._read('direction')

    @property
    def active_low(self):
        return int(self._read('active_low'))

    @property
    def edge(self):
        return self._read('edge')

    @export.setter
    def export(self, value):
        # open or reopen attr files
        # gpio pin will be registed if it is not yet
        if value:
            if not self.export:
                with open('/sys/class/gpio/export', 'w') as f:
                    f.write(str(self.pin))
            for attr in self.attributes:
                self._file[attr] = open(
                    os.path.join(self.path, attr),
                    'wb+', buffering=0)
        # close attr files
        # gpio will be unexported if it exists
        else:
            if self.export:
                with open('/sys/class/gpio/unexport', 'w') as f:
                    f.write(str(self.pin))
            for h in list(self._file.values()):
                h.close()
            self._file.clear()

    @value.setter
    def value(self, data):
        self._write('value', data)

    @direction.setter
    def direction(self, data):
        self._write('direction', data)

    @active_low.setter
    def active_low(self, data):
        self._write('active_low', data)

    @edge.setter
    def edge(self, data):
        self._write('edge', data)

    def _read(self, attr):
        self._read_lock.acquire()
        self._file[attr].seek(0)
        value = self._file[attr].read().strip()
        self._read_lock.release()
        return value

    def _write(self, attr, data):
        self._write_lock.acquire()
        self._file[attr].seek(0)
        self._file[attr].write(str(data))
        self._write_lock.release()


class _GPIO(object):
    def __init__(self):
        self.IN = constants.INPUT
        self.OUT = constants.OUTPUT
        self.PULLUP = constants.INPUT_PULLUP
        self.PULLDN = constants.INPUT_PULLDN
        self.HIGH = constants.HIGH
        self.LOW = constants.LOW
        self.RISING = constants.RISING
        self.FALLING = constants.FALLING
        self.BOTH = constants.CHANGE
        self.BOARD = constants.BOARD_SUNXI
        self.BCM = constants.BCM
        self.VERSION = 1.0

        self._pin_dict = {}
        self._pwm_dict = {}
        self._irq_dict = {}
        self._mode = self.BOARD
        self._flag_interrupts = threading.Event()
        self.enable_interrupts()

    def _time_ms(self):
        return time.time() * 1000

    def _get_pin_num(self, pin, must_in_dict=False):
        try:
            p = self._mode[pin]
        except:
            raise KeyError(('Invalid pin({}) or unsupported mode!\n'
                            'Reset mode and check pin num.').format(pin))
        if must_in_dict and (p not in self._pin_dict):
            raise NameError(('Pin {} is not setup yet, please run'
                             '`GPIO.setup({}, state)` first!'
                             '').format(pin, pin))
        return p

    def _listify(self, *args, **kwargs):
        # convert all args to list and pad them to a certain length
        args = list(args) # tuple to list
        for i, arg in enumerate(args):
            if not isinstance(arg, list):
                if isinstance(arg, tuple):
                    args[i] = list(arg)
                else:
                    args[i] = [arg]
            if 'padlen' in kwargs:
                padlen = kwargs['padlen']
                if len(args[i]) < padlen:
                    args[i] += [args[i][-1]] * (padlen - len(args[i]))
                elif len(arg) > padlen:
                    args[i] = args[i][:padlen]
        if len(args) == 1:
            return args[0]
        return args

    def setup(self, pin, state, initial=None):
        # listify pin for multichannel operation
        pins = [self._get_pin_num(p) for p in self._listify(pin)]
        # pad state_list and initial_list in case someone
        # want to setup more than one pin at one time
        states, initials = self._listify(state, initial, padlen=len(pin))

        # register all pins and init them
        for p, s, i in zip(pins, states, initials):
            if s == self.PULLUP:
                s, i = self.IN, self.HIGH
            elif s == self.PULLDN:
                s, i = self.IN, self.LOW
            elif s not in [self.IN, self.OUT]:
                raise ValueError('Invalid state: {}!'.format(s))
            if p not in self._pin_dict:
                self._pin_dict[p] = SysfsGPIO(p)
                self._pin_dict[p].export = True
            self._pin_dict[p].direction = s
            if i in [self.HIGH, self.LOW]:
                self._pin_dict[p].value = i

    def input(self, pin):
        # single channel value
        if type(pin) not in [list, tuple]:
            return self._pin_dict[
                self._get_pin_num(pin, must_in_dict=True)].value
        # multichannel values
        pins = [self._get_pin_num(pin, must_in_dict=True)
                for p in self._listify(pin)]
        return [self._pin_dict[p].value for p in pins]

    def output(self, pin, value):
        pins = [self._get_pin_num(p, must_in_dict=True)
                for p in self._listify(pin)]
        values = self._listify(value, padlen=len(pins))
        for p, v in zip(pins, values):
            if v not in [True, False, self.HIGH, self.LOW]:
                raise ValueError('Invalid value: {}'.format(v))
            self._pin_dict[p].value = int(v)

    def cleanup(self, pin=None):
        if pin is None:
            pins = list(self._pin_dict.keys())  # py2&py3 compatiable
        else:
            pins = [self._get_pin_num(p) for p in self._listify(pin)]
        for p in pins:
            pin = self._pin_dict.pop(p, None)
            if pin:
                pin.export = False
            pwm = self._pwm_dict.pop(p, None)
            if pwm:
                pwm.clear()
            irq = self._irq_dict.pop(p, None)
            if irq:
                irq['flag_stop'].set()
                irq['flag_triggered'].clear()
            del pin, pwm, irq

    def enable_interrupts(self):
        self._flag_interrupts.set()

    def disable_interrupts(self):
        self._flag_interrupts.clear()

    def _soft_interrupt(self, sysgpio, flag_stop, flag_triggered):
        # in case user set pin to some mode like PULLUP, we must check
        # whether this pin is initialized as IN first
        # default PULLUP/PULLDN are not used
        if sysfsgpio.direction != self.IN:
            sysfsgpio.direction = self.IN
        while not flag_stop.isSet():
            l1, l2 = self._irq_dict[p]['l1'], self._irq_dict['l2']
            bouncetime = self._irq_dict[p]['bouncetime'] / 1000.0
            while sysfsgpio.value != l1:
                self._flag_interrupts.wait()
            while sysfsgpio.value != l2:
                self._flag_interrupts.wait()
            time.sleep(bouncetime)
            if sysfsgpio.value == l2:
                flag_triggered.set()
                for c in self._irq_dict[p]['callbacks']:
                    c(pin)

    def add_event_detect(self, pin, edge, func=None, bouncetime=None):
        p = self._get_pin_num(pin, must_in_dict=True)
        if p in self._irq_dict:
            raise NameError(('Pin {} is already been attached to a soft '
                             'interrupt on {} edge, if you want to reset it, '
                             'please run `GPIO.remove_event_detect({})`'
                             '').format(pin, self._irq_dict[p]['edge'], pin))
        if edge == self.RISING:
            l1, l2 = self.LOW, self.HIGH
        elif edge == self.FALLING:
            l1, l2 = self.HIGH, self.LOW
        elif edge == self.BOTH:
            l1 = sysfsgpio.value
            l2 = self.HIGH - l1
        else:
            raise ValueError('Invalid edge: {}'.format(edge))

        # initialize soft interrupt on this pin
        flag_stop, flag_triggered = threading.Event(), threading.Event()
        t = threading.Thread(target=self._soft_interrupt,
                             args=(self._pin_dict[p],
                                   flag_stop,
                                   flag_triggered))
        t.setDeamon(True)
        t.start()
        self._irq_dict[p] = {
            'bouncetime': bouncetime if bouncetime is not None else 0,
            'callbacks': self._listify(func) if func is not None else [],
            'edge': edge, 'l1': l1, 'l2': l2,
            'flag_stop': flag_stop, 'flag_triggered': flag_triggered
        }

    def remove_event_detect(self, pin):
        p = self._get_pin_num(pin, must_in_dict=True)
        if p not in self._irq_dict:
            raise NameError(('Pin {} is not used as interrupt source yet, '
                             'please run `GPIO.add_event_detect({}, edge)` to '
                             'attached a interrupt first').format(pin, pin))
        irq = self._irq_dict.pop(p)
        irq['flag_stop'].set()
        irq['flag_triggered'].clear()
        del irq

    def add_event_callback(self, pin, callback):
        p = self._get_pin_num(pin, must_in_dict=True)
        if p not in self._irq_dict:
            raise NameError(('Pin {} is not initialized with edge yet, please '
                             'run `GPIO.add_event_detect({}, edge)` first'
                             '').format(pin, pin))
        self._irq_dict[p]['callbacks'] += self._listify(callback)

    def event_detected(self, pin, timeout=constants.FOREVER_ms):
        p = self._get_pin_num(pin, must_in_dict=True)
        if p not in self._irq_dict:
            raise NameError(('Pin {} is not initialized with edge yet, please '
                             'run `GPIO.add_event_detect({}, edge)` first'
                             '').format(pin, pin))
        start = self._time_ms()
        while not self._irq_dict[p]['flag_triggered'].isSet():
            if (self._time_ms() - start) > timeout:
                return False
            time.sleep(1.0/10)  # sensibility: refresh 10 times per second
        self._irq_dict[p]['flag_triggered'].clear()
        return True

    def wait_for_edge(self, pin, edge, timeout=constants.FOREVER_ms):
        start = self._time_ms()
        p = self._get_pin_num(pin, must_in_dict=True)
        if edge == self.RISING:
            l1, l2 = self.LOW, self.HIGH
        elif edge == self.FALLING:
            l1, l2 = self.HIGH, self.LOW
        elif edge == self.BOTH:
            l1 = self._pin_dict[p].value
            l2 = self.HIGH - l1
        else:
            raise ValueError('Invalid edge: {}'.format(edge))
        while self._pin_dict[p].value != l1:
            if (self._time_ms() - start) > timeout:
                return
        while self._pin_dict[p].value != l2:
            if (self._time_ms() - start) > timeout:
                return
        return pin

    def setmode(self, m):
        self._mode = mode

    def getmode(self):
        return self._mode

    def PWM(self, pin, frequency=None):
        '''
        if pin is already initialized before:
            if frequency provided:
                update frequency and return PWM instance
            else:
                return PWM instance with no operation
        else:
            if frequency provided:
                initialize with this frequency and return PWM instance
            else:
                initialize with 1Hz(default) and return PWM instance
        '''
        pins = [self._get_pin_num(p) for p in self._listify(pin)]
        frequencys = self._listify(frequency, padlen = len(pins))
        return_list = []
        for p, f in zip(pins, frequencys):
            if p not in self._pwm_dict:
                self.setup(self._listify(pin)[pins.index(p)], self.OUT)
                if f is None:
                    raise NameError(('PWM on pin {} is not initialized yet, '
                                     'please provide pin num and freq'
                                     '').format(p))
                self._pwm_dict[p] = _PWM(self._pin_dict[p], f)
            elif f:
                self._pwm_dict[p].ChangeFrequency(f)
            return_list.append(self._pwm_dict[p])
        if len(pins) == 1:
            return return_list[0]
        else:
            return return_list

GPIO = _GPIO()

class _PWM:
    def __init__(self, sysfsgpio, frequency):
        self._sysfsgpio = sysfsgpio
        self.ChangeFrequency(frequency)
        self._flag_pause = threading.Event()
        self._flag_stop = threading.Event()
        self._t = threading.Thread(target=self._pwm)
        self._t.setDeamon(True)
        self._t.start()

    def _pwm(self):
        while not self._flag_stop.isSet():
            self._flag_pause.wait()
            self._sysfsgpio.value = 1
            time.sleep(self._high_time)
            self._sysfsgpio.value = 0
            time.sleep(self._low_time)

    def start(self, dc):
        self.ChangeDutyCycle(dc)
        self._flag_pause.set()

    def stop(self):
        self._flag_pause.clear()

    def ChangeFrequency(self, frequency):
        if frequency <= 0:
            raise ValueError('Invalid frequency: {}'.format(frequency))
        self._frequency = frequency
        self._period = 1.0/frequency
        if hasattr(self, 'dc'):
            self._high_time = self._dc * self._period
            self._low_time = (1 - self._dc) * self._period

    def ChangeDutyCycle(self, dc):
        if dc > 100 or dc < 0:
            raise ValueError('Invalid duty cycle: {}'.format(dc))
        self._dc = float(dc) / 100
        self._high_time = dc * self._period
        self._low_time = (1 - dc) * self._period

    def clear(self):
        self.stop()
        self._flag_stop.set()


from . import arduino

__all__ = ['arduino', 'constants', 'GPIO', 'SysfsGPIO']
