import uasyncio as asyncio
import led_handler
import wattmeter_com_interface
from ntptime import settime
from asyn import Lock
from gc import mem_free, collect
from machine import WDT, RTC
from main import web_server_app
from main import wattmeter
from main import __config__
import ulogging

EVSE_ERR: int = 1
WATTMETER_ERR: int = 2
WEBSERVER_CANCELATION_ERR: int = 4
WIFI_HANDLER_ERR: int = 8
TIME_SYNC_ERR: int = 16

AP: int = 1
WIFI: int = 2


class TaskHandler:
    def __init__(self, wifi):
        self.setting = __config__.Config()
        self.setting.get_config()
        watt_interface = wattmeter_com_interface.Interface(115200, lock=Lock(30))
        self.wattmeter = wattmeter.Wattmeter(wattmeter_com_interface.Interface(115200, lock=Lock(30)), self.setting)
        self.web_server_app = web_server_app.WebServerApp(wifi, self.wattmeter, watt_interface, self.setting)
        self.setting_after_new_connection: bool = False
        self.wdt = WDT(timeout=60000)
        self.wifi_manager = wifi
        self.led_error_handler = led_handler.LedHandler(pin=21, on_time=1, off_time=2, delta=40)
        self.led_wifi_handler = led_handler.LedHandler(pin=22, on_time=1, off_time=2, delta=20)
        self.errors: int = 0
        self.try_off_connections: int = 0
        self.ap_timeout: int = 600
        self.wifi_manager.turnONAp()

        self.logger = ulogging.getLogger("TaskHandler")
        if int(self.setting.data['sw,TESTING SOFTWARE']) == 1:
            self.logger.setLevel(ulogging.DEBUG)
        else:
            self.logger.setLevel(ulogging.INFO)

    def mem_free(self) -> None:
        before: int = mem_free()
        collect()
        after: int = mem_free()
        self.logger.debug("Memory before: {} & After: {}".format(before, after))

    async def led_wifi(self) -> None:
        while True:
            await self.led_wifi_handler.led_handler()
            await asyncio.sleep(0.1)

    async def led_error(self) -> None:
        while True:
            await self.led_error_handler.led_handler()
            await asyncio.sleep(0.1)

    async def time_handler(self) -> None:
        while True:
            if self.wifi_manager.isConnected() and self.wattmeter.time_init is False:
                try:
                    self.logger.info("Setting time.")
                    settime()
                    rtc = RTC()
                    import utime
                    tampon1 = utime.time()
                    tampon2 = tampon1 + int(self.setting.data["in,TIME-ZONE"]) * 3600
                    (year, month, mday, hour, minute, second, weekday, yearday) = utime.localtime(tampon2)
                    rtc.datetime((year, month, mday, 0, hour, minute, second, 0))
                    self.wattmeter.time_init = True
                    self.led_error_handler.remove_state(TIME_SYNC_ERR)
                    self.errors &= ~TIME_SYNC_ERR
                except Exception as e:
                    self.led_error_handler.add_state(TIME_SYNC_ERR)
                    self.errors |= TIME_SYNC_ERR
                    self.logger.info("Error during time setting: {}".format(e))

            await asyncio.sleep(10)
            self.mem_free()

    async def wifi_handler(self) -> None:
        while True:
            try:
                self.led_wifi_handler.add_state(AP)
                if self.wifi_manager.isConnected():
                    if self.ap_timeout > 0:
                        self.ap_timeout -= 1
                    elif (int(self.setting.data['sw,Wi-Fi AP']) == 0) and self.ap_timeout == 0:
                        self.wifi_manager.turnOfAp()
                        self.led_wifi_handler.remove_state(AP)
                    elif int(self.setting.data['sw,Wi-Fi AP']) == 1:
                        self.wifi_manager.turnONAp()

                    self.led_wifi_handler.add_state(WIFI)
                    if self.setting_after_new_connection is False:
                        self.setting_after_new_connection = True
                else:
                    self.led_wifi_handler.remove_state(WIFI)
                    if len(self.wifi_manager.read_profiles()) != 0:
                        if self.try_off_connections > 30:
                            self.try_off_connections = 0
                            result = await self.wifi_manager.get_connection()
                            if result:
                                self.setting_after_new_connection = False
                        self.try_off_connections = self.try_off_connections + 1
                self.led_error_handler.remove_state(WIFI_HANDLER_ERR)
                self.errors &= ~WIFI_HANDLER_ERR
            except Exception as e:
                self.led_error_handler.add_state(WIFI_HANDLER_ERR)
                self.errors |= WIFI_HANDLER_ERR
                self.logger.info("wifi_handler exception : {}".format(e))
            self.mem_free()
            await asyncio.sleep(2)

    async def interface_handler(self) -> None:
        while True:
            try:
                await self.wattmeter.wattmeter_handler()
                self.led_error_handler.remove_state(WATTMETER_ERR)
                self.errors &= ~WATTMETER_ERR
            except Exception as e:
                self.led_error_handler.add_state(WATTMETER_ERR)
                self.errors |= WATTMETER_ERR
                self.logger.info("interface_handler error: {}".format(e))
            self.mem_free()
            await asyncio.sleep(1)

    # Handler for time
    async def system_handler(self) -> None:
        while True:
            self.setting.data['ERRORS'] = str(self.errors)
            self.wdt.feed()
            self.mem_free()
            await asyncio.sleep(1)

    def main_task_handler_run(self) -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(self.wifi_handler())
        loop.create_task(self.system_handler())
        loop.create_task(self.time_handler())
        loop.create_task(self.interface_handler())
        loop.create_task(self.led_error())
        loop.create_task(self.led_wifi())
        loop.create_task(self.web_server_app.web_server_run())
        loop.run_forever()
