from machine import Pin, PWM
#from main.wattmeter import Wattmeter

SSR1_PIN: int = 33
SSR2_PIN: int = 23
FREQUENCY: int = 1

class Regulation:

    def __init__(self, setting)->None :

        self.ssr1 = PWM(Pin(SSR1_PIN), FREQUENCY)
        self.config = setting
        #nastaveni
        self.tuv_power = 2000 # vykon topne spiraly
        self.tuv_volume = 200 #objem nadrze
        self.target_energy = 9000 #energie za 24h odpovidajici tuv_volume a temp_delta
        self.temp_delta = 45 #pozadovane otepleni
        
        #regulacni dat
        self.target_power = 0
        
        
        

    def run(self, power:int)-> None:
        """
        Regulation function. 100% pwm = 1024, 0% pwm = 0
        """
        
        
        
        self.tuv_energy = 4180 * 200 *  self.temp_delta / 3600  
        self.target_power = 0
        

        self.ssr1.duty(512)