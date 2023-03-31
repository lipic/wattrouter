from machine import Pin, PWM

class Regulation:

    def __int__(self):
        frequency = 1
        ssr1 = PWM(Pin(5), frequency)

    def example(self):
        print("hello")