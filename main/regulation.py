from machine import Pin, PWM
from collections import OrderedDict
import ulogging

SSR1_PIN: int = 33
SSR2_PIN: int = 23
FREQUENCY: int = 1


class Regulation:

    def __init__(self, wattmeter, config: OrderedDict[str, str]) -> None:

        self.ssr1 = PWM(Pin(SSR1_PIN), FREQUENCY)
        self.config = config
        self.wattmeter = wattmeter
        # self.config.data['btn,BOOST-MODE']
        # self.config.data['in,TUV-VOLUME']
        # self.config.data['in,TUV-POWER']
        # self.config.data['in,NIGHT-BOOST']
        # self.config.data['in,NIGHT-TEMPERATURE']
        # self.config.data['in,MORNING-BOOST']
        # self.config.data['in,MORNING-TEMPERATURE']
        # self.config.data['in,BOOST-TIMEOUT']
        # self.config.data['BOOST']
        self.target_power = 0
        self.temp_delta = 0

        self.logger = ulogging.getLogger("Regulation")
        if int(self.config.data['sw,TESTING SOFTWARE']) == 1:
            self.logger.setLevel(ulogging.DEBUG)
        else:
            self.logger.setLevel(ulogging.INFO)

    def run(self, hour: int, minute: int) -> None:
        """
        Regulation function. 100% pwm = 1024, 0% pwm = 0
        """
        actual_time: int = hour * 3600 + minute * 60
        #self.logger.info("Actual time: {}".format(actual_time))
        self.tuv_energy = 4180 * 200 * self.temp_delta / 3600
        self.target_power = 0

        self.ssr1.duty(512)
