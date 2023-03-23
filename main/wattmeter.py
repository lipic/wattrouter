import ujson as json
import time
import uasyncio as asyncio
from machine import Pin,UART
from gc import collect, mem_free
import ulogging

class Wattmeter:
     
    def __init__(self,wattmeter,setting):
        self.relay  = Pin(25, Pin.OUT)
        self.wattmeterInterface = wattmeter
        self.dataLayer = DataLayer()
        self.fileHandler = fileHandler()
        self.DAILY_CONSUMPTION: str = 'daily_consumption.dat'
        self.timeInit: bool = False
        self.timeOffset: bool = False
        self.lastMinute: int =  0
        self.lastHour: int = 0
        self.lastDay: int =  0
        self.lastMonth: int = 0
        self.lastYear: int = 0
        self.startUpTime: int = 0
        self.setting = setting
        self.dataLayer.data['ID'] = self.setting.config['ID']
        self.logger = ulogging.getLogger("wattmeter")
        #if debug > 0:
        self.logger.setLevel(ulogging.DEBUG)


    async def wattmeterHandler(self):

        if (self.timeOffset == False) and (self.timeInit == True):
            self.startUpTime         = time.time()
            self.lastMinute          = int(time.localtime()[4])
            self.lastDay             = int(time.localtime()[2])
            self.lastMonth           = int(time.localtime()[1])
            self.lastYear            = int(time.localtime()[0])
            self.dataLayer.data['D'] = self.fileHandler.readData(self.DAILY_CONSUMPTION)
            self.dataLayer.data["M"] = self.fileHandler.getMonthlyEnergy(self.DAILY_CONSUMPTION)
            self.timeOffset = True

        self.dataLayer.data['RUN_TIME']       = time.time() - self.startUpTime
        curent_year: str                      = str(time.localtime()[0])[-2:]
        self.dataLayer.data['WATTMETER_TIME'] = ("{0:02}.{1:02}.{2}  {3:02}:{4:02}:{5:02}".format(time.localtime()[2],time.localtime()[1],curent_year,time.localtime()[3],time.localtime()[4],time.localtime()[5]))

        await self.__read_wattmeter_data(6000, 21)

        if (self.lastMinute != int(time.localtime()[4])) and (self.timeInit == True):
            minute_energy : int = self.dataLayer.data['E1_P_min']-self.dataLayer.data['E1_N_min']
            if len(self.dataLayer.data["Pm"])<61:
                self.dataLayer.data["Pm"].append(minute_energy*6)
            else:
                self.dataLayer.data["Pm"] = self.dataLayer.data["Pm"][1:]
                self.dataLayer.data["Pm"].append(minute_energy*6)
            
            self.dataLayer.data["Pm"][0] = len(self.dataLayer.data["Pm"])

            async with self.wattmeterInterface as w:
                await w.writeWattmeterRegister(100,[1])

            self.lastMinute = int(time.localtime()[4]) 

        if self.timeInit:
            if self.lastHour != int(time.localtime()[3]):

                async with self.wattmeterInterface as w:
                    await w.writeWattmeterRegister(101,[1])

                self.lastHour = int(time.localtime()[3])
                if len(self.dataLayer.data["Es"])<97:
                    self.dataLayer.data["Es"].append(self.lastHour)
                    self.dataLayer.data["Es"].append(self.dataLayer.data['E1_P_hour'])
                    self.dataLayer.data["Es"].append(self.dataLayer.data['E1_N_hour'])
                    self.dataLayer.data["Es"].append(self.dataLayer.data['HDO'])
                else:
                    self.dataLayer.data["Es"] = self.dataLayer.data["Es"][4:]
                    self.dataLayer.data["Es"].append(self.lastHour)
                    self.dataLayer.data["Es"].append(self.dataLayer.data['E1_P_hour'])
                    self.dataLayer.data["Es"].append(self.dataLayer.data['E1_N_hour'])
                    self.dataLayer.data["Es"].append(self.dataLayer.data['HDO'])
            
                self.dataLayer.data["Es"][0] = len(self.dataLayer.data["Es"])
            
            else:
                if len(self.dataLayer.data["Es"])<97:
                    self.dataLayer.data["Es"][len(self.dataLayer.data["Es"])-3] = self.dataLayer.data['E1_P_hour']
                    self.dataLayer.data["Es"][len(self.dataLayer.data["Es"])-2] = self.dataLayer.data['E1_N_hour']
                    self.dataLayer.data["Es"][len(self.dataLayer.data["Es"])-1] = self.dataLayer.data['HDO']
                else:
                    self.dataLayer.data["Es"][94] = self.dataLayer.data['E1_P_hour']
                    self.dataLayer.data["Es"][95] = self.dataLayer.data['E1_N_hour']
                    self.dataLayer.data["Es"][96] = self.dataLayer.data['HDO']
        
        if (self.lastDay != int(time.localtime()[2])) and self.timeInit and self.timeOffset:

            day = {("{0:02}/{1:02}/{2}".format(self.lastMonth,self.lastDay ,str(self.lastYear)[-2:] )) : [self.dataLayer.data["E1_P_day"], self.dataLayer.data["E1_N_day"]]}
            async with self.wattmeterInterface as w:
                await w.writeWattmeterRegister(102,[1])
            
            self.lastYear  = int(time.localtime()[0])
            self.lastMonth = int(time.localtime()[1])
            self.lastDay   = int(time.localtime()[2])
            self.fileHandler.writeData(self.DAILY_CONSUMPTION, day)
            self.dataLayer.data["D"] =  self.fileHandler.readData(self.DAILY_CONSUMPTION,31)
            self.dataLayer.data["M"] = self.fileHandler.getMonthlyEnergy(self.DAILY_CONSUMPTION)

    async def __read_wattmeter_data(self, reg:int, length:int)-> None:

        try:
            async with self.wattmeterInterface as w:
                receive_data =  await w.readWattmeterRegister(reg,length)
                self.logger.info("Len:{} ; Receive data:{} ".format(len(receive_data),receive_data))
            if (receive_data != "Null") and (reg == 6000):

                hdo_input:int = int(((receive_data[0]) << 8) | (receive_data[1]))
                if hdo_input == 1 and  '1'== self.setting.config['sw,AC IN ACTIVE: HIGH']:
                    self.dataLayer.data['HDO'] = 1
                elif hdo_input == 0 and  '0'== self.setting.config['sw,AC IN ACTIVE: HIGH']:
                    self.dataLayer.data['HDO'] = 1
                else:
                    self.dataLayer.data['HDO'] = 0

                self.dataLayer.data['I1']         = int(((receive_data[2]) << 8) | (receive_data[3]))
                self.dataLayer.data['P1']         = int(((receive_data[4]) << 8) | (receive_data[5]))
                self.dataLayer.data['U1']         = int(((receive_data[6]) << 8) | (receive_data[7]))
                self.dataLayer.data['E1_P_min']   = int(((receive_data[8]) << 8) | (receive_data[9]))
                self.dataLayer.data['E1_N_min']   = int(((receive_data[10]) << 8) | (receive_data[11]))
                self.dataLayer.data['E1_P_hour']  = int(((receive_data[12]) << 8) | (receive_data[13]))
                self.dataLayer.data['E1_N_hour']  = int(((receive_data[14]) << 8) | (receive_data[15]))
                self.dataLayer.data['E1_P_day']   = int(((receive_data[16]) << 8) | (receive_data[17]))
                self.dataLayer.data['E1_N_day']   = int(((receive_data[18]) << 8) | (receive_data[19]))
                self.dataLayer.data['E1_P']       = int((receive_data[22] << 24) | (receive_data[23] << 16) | (receive_data[20] << 8) | receive_data[21])
                self.dataLayer.data['E1_N']       = int((receive_data[26] << 24) | (receive_data[27] << 16) | (receive_data[24] << 8) | receive_data[25])
                self.dataLayer.data['I_TUV']      = int(((receive_data[28]) << 8) | (receive_data[29]))
                self.dataLayer.data['P_TUV']      = int(((receive_data[30]) << 8) | (receive_data[31]))
                self.dataLayer.data['E_TUV_min']  = int(((receive_data[32]) << 8) | (receive_data[33]))
                self.dataLayer.data['E_TUV_hour'] = int(((receive_data[34]) << 8) | (receive_data[35]))
                self.dataLayer.data['E_TUV_day']  = int(((receive_data[36]) << 8) | (receive_data[37]))
                self.dataLayer.data['E_TUV']      = int((receive_data[40] << 24) | (receive_data[41] << 16) | (receive_data[38] << 8) | receive_data[39])
     
                self.logger.info("U1:{} ; I1:{}; P1:{}".format(self.dataLayer.data['U1'], self.dataLayer.data['I1'],self.dataLayer.data['P1']))

            else:   
                self.logger.error("Timed out waiting for result.")
            
        except Exception as e:
            self.logger.error("Exception: {}. UART is probably not connected.".format(e))
class DataLayer:
    def __str__(self):
        return json.dumps(self.data)
    def __init__(self):
        self.data: dict        = dict()
        self.data['HDO']       = 0
        self.data['I1']        = 0
        self.data['U1']        = 0
        self.data['P1']        = 0
        self.data['E1_P_min']  = 0
        self.data['E1_N_min']  = 0
        self.data['E1_P_hour'] = 0
        self.data['E1_N_hour'] = 0
        self.data['E1_P_day']  = 0
        self.data['E1_N_day']  = 0
        self.data['E1_P']      = 0
        self.data['E1_N']      = 0
        self.data['I_TUV']     = 0
        self.data['P_TUV']     = 0
        self.data['E_TUV_min'] = 0
        self.data['E_TUV_hour']= 0
        self.data['E_TUV_day'] = 0
        self.data['E_TUV']     = 0
        self.data["Pm"]        = [0]   #minute power
        self.data["Es"]        = [0]   #Hour energy
        self.data['D']         = None  #Daily energy
        self.data['M']         = None  #Monthly energy
        self.data['RUN_TIME']  = 0
        self.data['WATTMETER_TIME'] = 0
        self.data['ID']        = 0

class fileHandler:
                
    def readData(self,file,length=None):
        data = []
        try:
            #b = mem_free()
            csv_gen = self.csv_reader(file)
            row_count = 0
            data = []
            for row in csv_gen:
                collect()
                row_count += 1

            csv_gen = self.csv_reader(file)
            cnt = 0
            for i in csv_gen:
                cnt+=1
                if cnt>row_count-31:
                    data.append(i.replace("\n",""))
                collect()
            #print("Mem free before:{}; after:{}; rozdil:{} ".format(b,mem_free(),b-mem_free()))
            return data
        except Exception as e:
            return [] 
    
    def csv_reader(self,file_name):
        for row in open(file_name, "r"):
            try:
                yield row
            except StopIteration:
                return

    def getMonthlyEnergy(self,file):
        energy = []
        lastMonth = 0
        lastYear = 0
        positiveEnergy = 0
        negativeEnergy = 0

        try:
            csv_gen = self.csv_reader(file)
            for line in csv_gen:
                line = line.replace("\n","").replace("/",":").replace("[","").replace("]","").replace(",",":").replace(" ","").split(":")
                #print("0 - Mem free before:{}; after:{}; rozdil:{} ".format(b,mem_free(),b-mem_free()))
                if lastMonth == 0:
                    lastMonth = int(line[0])
                    lastYear = int(line[2])

                if lastMonth != int(line[0]):
                    if len(energy)<36:
                        energy.append("{}/{}:[{},{}]".format(lastMonth,lastYear,positiveEnergy,negativeEnergy))
                    else:
                        energy = energy[1:]
                        energy.append("{}/{}:[{},{}]".format(lastMonth,lastYear,positiveEnergy,negativeEnergy))
                    positiveEnergy = 0
                    negativeEnergy = 0
                    lastMonth = int(line[0])
                    lastYear = int(line[2])

                positiveEnergy += int(line[3])
                negativeEnergy += int(line[4])
                collect()                

            if len(energy)<36:
                energy.append("{}/{}:[{},{}]".format(lastMonth,lastYear,positiveEnergy,negativeEnergy))
            else:
                energy = energy[1:]
                energy.append("{}/{}:[{},{}]".format(lastMonth,lastYear,positiveEnergy,negativeEnergy))
            return energy    
                
        except Exception as e:
            print("Error: ",e)

    def writeData(self,file,data):
        lines = []
        for variable, value in data.items():
            lines.append(("%s:%s\n" % (variable, value)).replace(" ",""))
            
        with open(file, "a+") as f:
            f.write(''.join(lines))
