from machine import Pin, PWM
from collections import OrderedDict
import ulogging

SSR1_PIN: int = 33
SSR2_PIN: int = 23
FREQUENCY: int = 5
WATTER_CONST: int = 4180
MODE_OFF: int = 0
MODE_HDO: int = 1
MODE_BOOST: int = 2
MODE_HDO_BOOST: int = 3

PWM_MAX: int = 1023
PWM_OFF: int = 0

class Regulation:
    
    def __init__(self, wattmeter, config: OrderedDict[str, str]) -> None:

        self.ssr1 = PWM(Pin(SSR1_PIN), FREQUENCY)
        self.config = config
        self.wattmeter = wattmeter
        self.config.data['btn,BOOST-MODE']
        self.config.data['in,TUV-VOLUME']
        self.config.data['in,TUV-POWER']
        self.config.data['in,NIGHT-BOOST']
        self.config.data['in,NIGHT-TEMPERATURE']
        self.config.data['in,MORNING-BOOST']
        self.config.data['in,MORNING-TEMPERATURE']
        self.config.data['in,BOOST-TIMEOUT']
        self.config.data['BOOST']
        
        self.target_power = 0
        self.temp_input = 10
        self.tuv_energy_night = 0
        self.tuv_energy_morning = 0
        self.overflow_limit = -30 #limit pro handlovani pretoku
        
        self.target_duty = 0
        self.sec_night_boost = 0 # kolik sekund se musinahrivat aby se dosahlo teloty boostu
        self.sec_morning_boost = 0
        self.power_simulator = 0

        self.power_step = int(self.config.data['in,TUV-POWER']) / (1000 / FREQUENCY / 20) #1000ms 20ms
        self.power_step_count = int(self.config.data['in,TUV-POWER']) / self.power_step
        self.power_hyst = self.power_step / 4 # hystereze regulace 1/4 minimalniho kroku
        # vypocet energie pro nocni boost
        self.tuv_energy_night = WATTER_CONST * int(self.config.data['in,TUV-VOLUME']) * (int(self.config.data['in,NIGHT-TEMPERATURE']) - self.temp_input) / 3600                        
        # vypocet sekund se ma nahrivat nocni boost, pocitejme ze 1/4 v bojleru zustala, takze 3/4
        self.sec_night_boost = self.tuv_energy_night * 3600 * 3 / 4 / int(self.config.data['in,TUV-POWER'])
        # vypocet energie pro ranni boost
        self.tuv_energy_morning = WATTER_CONST * int(self.config.data['in,TUV-VOLUME']) * (int(self.config.data['in,MORNING-TEMPERATURE']) - self.temp_input) / 3600                        
        # vypocet sekund se ma nahrivat ranni boost, pocitejme ze 1/4 v bojleru zustala, takze 3/4
        self.sec_morning_boost = self.tuv_energy_night * 3600 * 3 / 4 / int(self.config.data['in,TUV-POWER'])
        
               
        self.logger = ulogging.getLogger("Regulation")
        if int(self.config.data['sw,TESTING SOFTWARE']) == 1:
            self.logger.setLevel(ulogging.DEBUG)
        else:
            self.logger.setLevel(ulogging.INFO)
            
              
    def run(self, hour: int, minute: int, power: int) -> None:
        """
        Regulation function. 100% pwm = 1023, 0% pwm = 0
        """
               
        actual_time: int = hour * 3600 + minute * 60

        self.config.data['btn,BOOST-MODE']
        self.config.data['in,TUV-VOLUME']
        self.config.data['in,TUV-POWER']
        self.config.data['in,NIGHT-BOOST']
        self.config.data['in,NIGHT-TEMPERATURE']
        self.config.data['in,MORNING-BOOST']
        self.config.data['in,MORNING-TEMPERATURE']
        self.config.data['in,BOOST-TIMEOUT']
        self.config.data['BOOST']

        self.logger.info("###################################")
        self.logger.info("BOOST-MODE: {}".format(self.config.data['btn,BOOST-MODE']))
        self.logger.info("TUV-VOLUME: {}".format(self.config.data['in,TUV-VOLUME']))
        self.logger.info("TUV-POWER: {}".format(self.config.data['in,TUV-POWER']))
        self.logger.info("NIGHT-BOOST: {}".format(self.config.data['in,NIGHT-BOOST']))
        self.logger.info("NIGHT-TEMPERATURE: {}".format(self.config.data['in,NIGHT-TEMPERATURE']))
        self.logger.info("MORNING-BOOST: {}".format(self.config.data['in,MORNING-BOOST']))
        self.logger.info("MORNING-TEMPERATURE: {}".format(self.config.data['in,MORNING-TEMPERATURE']))
        self.logger.info("BOOST-TIMEOUT: {}".format(self.config.data['in,BOOST-TIMEOUT']))
        self.logger.info("BOOST: {}".format(self.config.data['BOOST']))
        
        #actual_time = 60000
        #power = -800
        #self.config.data['btn,BOOST-MODE'] = MODE_BOOST
        
        
        #regulace podle pretoku celych periodach 20ms
        if power < self.overflow_limit:
            if power < (-self.power_hyst):
                self.target_power += self.power_step
                if self.target_power > int(self.config.data['in,TUV-POWER']):
                    self.target_power = int(self.config.data['in,TUV-POWER'])
        elif power > self.power_hyst:
            self.target_power -= self.power_step
            if self.target_power < 0:
                self.target_power = 0
 
        # pokud je aktivovany nejaky BOOST
        if int(self.config.data['btn,BOOST-MODE']) == MODE_BOOST:

            if self.get_boost_status(actual_time):
                self.target_power = int(self.config.data['in,TUV-POWER'])
                print("ssr sepnuto casovym boostem")

        elif int(self.config.data['btn,BOOST-MODE']) == MODE_HDO:
            
            if self.wattmeter.data_layer.data['HDO'] != 0:
                self.target_power = int(self.config.data['in,TUV-POWER'])
                print("ssr sepnuto HDOckem")

        elif int(self.config.data['btn,BOOST-MODE']) == MODE_HDO_BOOST:
            if self.get_boost_status(actual_time) and self.wattmeter.data_layer.data['HDO'] != 0:
                self.target_power = int(self.config.data['in,TUV-POWER'])
                print("ssr sepnuto casovym boostem a soucasne HDO")

        #manualni boost
        if self.config.data['BOOST']:
            self.target_power = int(self.config.data['in,TUV-POWER'])

        #strida   
        self.target_duty = int((self.target_power / int(self.config.data['in,TUV-POWER'])) * 1024)
        if self.target_duty > PWM_MAX:
           self.target_duty = PWM_MAX 
        print(self.target_duty)

        self.ssr1.duty(self.target_duty)
        
    def get_boost_status (self, time_sec: int) -> int:
        if time_sec > (int(self.config.data['in,NIGHT-BOOST']) - self.sec_night_boost) and time_sec < int(self.config.data['in,NIGHT-BOOST']):
             return True
        elif time_sec > (int(self.config.data['in,MORNING-BOOST']) - self.sec_morning_boost) and time_sec < int(self.config.data['in,MORNING-BOOST']):
             return True
        else:
            return False
