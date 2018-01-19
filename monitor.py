# -*- coding: utf-8 -*-
"""
@Data: 2018-01-12
@Author: darwin.tan(pavelbuffon@gmail.com)
"""
import os
import sys
import codecs
import re
import argparse
import requests
import time
from configparser import ConfigParser

requests.packages.urllib3.disable_warnings()


class TicketsMonitor(object):
    def __init__(self):
        self.stations_code_version = 1.9043
        self.stations_code = self.parse_stations_code()
        # A9:特等座 M:一等座 O:二等座 A6:高级软卧 A4:软卧 A3:硬卧 A2:软座 A1:硬座 WZ:无座 F:动卧
        self.train_types = {"G", "C", "D", "Z", "T", "K"}
        self.seat_types = {"商务座", "一等座", "二等座", "高级软座", "软卧", "动卧", "硬卧", "软座", "硬座", "无座"}
        self.ticket_url = "https://kyfw.12306.cn/otn/leftTicket/queryZ?"  # 余票查询API

        self.from_station = ""  # 始发站
        self.to_station = ""  # 终点站
        self.selected_trains = ""  # 车次
        self.departure_date = "2018-02-12"  # 出发日期
        self.selected_train_types = ""  # 列车类型，G/D/Z/T/K/L
        self.selected_seat_types = ""  # 席别
        self.interval = 60  # 查询间隔

        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--config", help="Specify config file, use absolute path")
        args = parser.parse_args()
        if args.config:
            self.load_config(args.config)
        else:
            self.load_config()

    def load_config(self, config_file="left.ini"):
        print("加载配置文件...")
        path = os.path.join(os.getcwd(), config_file)
        config = ConfigParser()
        try:
            # 指定读取config.ini编码格式，防止中文乱码（兼容windows）
            config.read_file(codecs.open(path, "r", "utf-8-sig"))
        except IOError as e:
            print(u'打开配置文件"%s"失败, 请先创建或者拷贝一份配置文件left.ini' % config_file)
            input('Press any key to continue')
            sys.exit()
        # left.ini配置的是中文，字典中存的是utf-8编码后的key，需要进行转码
        # self.from_station = self.stations_code.get(config.get("cookieInfo", "from").encode("utf-8"))
        # self.to_station = self.stations_code.get(config.get("cookieInfo", "to").encode("utf-8"))
        self.from_station = self.stations_code.get(config.get("cookieInfo", "from"))
        self.to_station = self.stations_code.get(config.get("cookieInfo", "to"))
        self.departure_date = config.get("cookieInfo", "departure_date")
        try:
            interval = int(config.get("cookieInfo", "interval"))
            if interval < self.interval:
                print("查询间隔太频繁有被封掉的风险，将采用默认值%s秒" % self.interval)
            else:
                self.interval = interval
        except ValueError:
            print("间隔设置值错误，将采用默认值%s秒" % self.interval)

        self.selected_trains = {x for x in config.get("trainInfo", "train_names").split(",") if x != ""}
        selected_train_types = {x for x in config.get("trainInfo", "train_types").split(",") if x in self.train_types}
        if len(selected_train_types) == 0:
            self.selected_train_types = self.train_types

        selected_seat_types = {x for x in config.get("confirmInfo", "seat_types").split(",") if x in self.seat_types}
        if len(selected_seat_types) == 0:
            # 未指定席别时，默认为所有席别
            self.selected_seat_types = self.seat_types

    def parse_stations_code(self, file_name="stations"):
        print("loading stations")
        path = os.path.join(os.getcwd(), file_name)
        file = codecs.open(path, "r", "utf-8-sig")
        stations = re.split(r"[@';]", file.read())[2:-2]
        stations_code = dict()
        for station in stations:
            segment = station.split("|")
            if len(segment) > 3:
                # stations_code[segment[1].encode('utf-8')] = segment[2]
                stations_code[segment[1]] = segment[2]
        return stations_code


    def query_left_ticket(self):
        # url = self.ticket_url + "leftTicketDTO.train_date={}&leftTicketDTO.from_station={}" \
        #       "&leftTicketDTO.to_station={}&purpose_codes=ADULT".format(
        #         self.departure_date, self.from_station, self.to_station)
        # response = requests.get(url, verify=False)  # 12306证书验证会影响访问，所以要关闭掉，同时要关掉warning
        # # response = requests.get(url, cert=("srca.cer", "/path/client.key"))
        # ticket_info = response.json()

        # test data
        ticket_info = {
            "data": {
                "flag": 1,
                "map": {
                    "BJP": "北京",
                    "BXP": "北京西",
                    "CSQ": "长沙",
                    "CWQ": "长沙南"
                },
                "result": [
                    "|预订|330000K5980X|K599|BTC|GZQ|BXP|CSQ|05:14|02:39|21:25|N|29TLOXBjDnsXQNX7tJr50%2B3Sh1fZLFiAadOkH3GscR%2B75%2FrugiHlkHfV3wg%3D|20180207|3|C1|09|29|0|0||||无|||无||无|无|||||10401030|1413|0",
                    "|预订|240000G48508|G485|BXP|NXG|BXP|CWQ|07:03|14:06|07:03|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P4|01|14|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "|预订|240000G5290H|G529|BXP|NFZ|BXP|CWQ|07:08|14:46|07:38|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P4|01|16|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "|列车运行图调整,暂停发售|2400000G710H|G71|BXP|NZQ|BXP|CWQ|24:00|24:00|99:59|IS_TIME_NOT_BUY||20180208||P2|01|13|0|1|||||||||||||||||0",
                    "|预订|240000G40306|G403|BXP|KOM|BXP|CWQ|08:00|13:38|05:38|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P3|01|05|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "HLNucKpEimdjHxttNm4wSvugVsk6taAwtZt5YHRaKO%2FxzhtK0yyLKSt2cr5GWWWB5oIwyTJ2SiZa%0AY1bII%2FHHTwsmqxSZ1cDob%2BISTE8mqu5UqLOBUkRS2GlMX7PAO3vzQ2d6NfsBHM2MGsW9%2B5N2%2B6MG%0AgJqJTAjnuOynL6SApFfdTsaPCzphoTso30vagGYGZ5hWgcDASRO6nqfw%2B3MSA1f0ysATlEe6efc1%0A7xC2z8XuhrGuipw7VW4WrbvDduzxzCtGt6LKSJY%3D|预订|2400000K2117|K21|BXP|NNZ|BXP|CSQ|08:18|05:56|21:38|Y|rcFrS3LwTIZGcctjkBNy8%2FrWTJkiKC0rc%2FrHrs3tG8zOjcDsk6MZQ9psQCU%3D|20180208|3|PB|01|19|0|0||||无|||有||无|无|||||10401030|1413|0",
                    "|预订|240000Z14907|Z149|BXP|GIW|BXP|CSQ|08:36|23:14|14:38|N|29TLOXBjDnsXQNX7tJr50%2B3Sh1fZLFiAadOkH3GscR%2B75%2FrugiHlkHfV3wg%3D|20180208|3|P4|01|09|0|0||||无|||无||无|无|||||10401030|1413|0",
                    "eLhPFCumNg5ozQRUz04R3ra8JPNKlT8YqckqFb1NN70cLl3oWoWHaaCPS2pxYB9VvU1XtkvPzHZi%0ACrVPNqKXUBDAyLUIjct0vCoDOzbfxzrTUsuI3f8GpYV0uo2U56j1uDWnNG%2BbkS9yupddssOggm71%0AV4nLM4PGoIb1cIZ7lBFEHZyVlDfCVkXqjIUL1ikmceI6BytrxxtQxi%2BH8ZkhhNW9z1PCDU0yUK8%2B%0At4IG1%2BrqxZ7R8ATI9vJ2YEzUHONZFs%2B6gA%3D%3D|预订|240000K96714|K967|BJP|HHQ|BJP|CSQ|08:37|05:44|21:07|Y|SsPq7n7C212nKvx%2F0f0zICU%2F1AdfBqaTxHCs9tclsELWAUeNRfbRRlEGlmw%3D|20180208|3|PA|01|20|0|0||||无|||有||无|无|||||10401030|1413|0",
                    "jWZsjZcG7KaUyGTVlZEq9mtBosGPGDvTGuuABfjR%2B7LXvN5M8bRwpagdwFYQZnQjQe7Udi1fdfip%0AWUjN%2BLSFUnWiUzcL55wtg2yZDvfL6eGjVcJqAdmF4tuYHGAombka4lsT7V5phathiOTTD7f4%2Bjld%0ATalTshCLOILkptORqlzLsEq%2BDECmGsmv%2FiGOLB6B84RyqjaqmYfR6Z4U8yEN1S5ny5iJUKaicHuS%0AUiXUuDoT9TpvmrjTQU4ul4goBOBK3Rh8FJihTE0%3D|预订|240000K43304|K433|BXP|AXM|BXP|CSQ|08:42|04:07|19:25|Y|HQwqGOk3hpMEhEEjlPHFWkTQaj2yGRbUdf5Z4%2F%2BYb%2Bu9UG7jsfA5NBeOVOI%3D|20180208|3|P3|01|17|0|0||||无|||有||无|无|||||10401030|1413|0",
                    "|列车运行图调整,暂停发售|2400000G830Q|G83|BXP|CWQ|BXP|CWQ|24:00|24:00|99:59|IS_TIME_NOT_BUY||20180208||P3|01|05|0|1|||||||||||||||||0",
                    "|列车运行图调整,暂停发售|2400000G810C|G81|BXP|KQW|BXP|CWQ|24:00|24:00|99:59|IS_TIME_NOT_BUY||20180208||P2|01|05|0|1|||||||||||||||||0",
                    "|预订|240000G4210E|G421|BXP|NFZ|BXP|CWQ|09:05|16:09|07:04|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P3|01|12|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "|预订|2400000G790D|G79|BXP|NZQ|BXP|CWQ|10:00|15:38|05:38|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P4|01|05|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "|预订|240000G40503|G405|BXP|KOM|BXP|CWQ|10:05|16:36|06:31|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P4|01|09|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "|预订|2400000G650G|G65|BXP|IZQ|BXP|CWQ|10:33|17:29|06:56|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P4|01|12|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "|预订|240000G40107|G401|BXP|KQW|BXP|CWQ|11:43|18:46|07:03|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P2|01|12|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "SOBIYkyLjPu97cO5c4MfVoz6trQFyQEpkHlIFKQa39eGWMxePEvSYrLSDQOJUo0A3II3yDsyvVjA%0AmAHdYY5AhH5yWHkaRnf%2BUzj%2F9qCpGLCcDCGyVQpBNXVGiLLtwI%2BHimItejtdARFsYt11Rd%2BI%2F2%2FR%0AgYrExIq%2BV3ziSCn%2FP6FPyqqVpo%2FlM0LIreHjJqX9GB1aUf7UDoaRGqBpQgE0nQFb5%2BR67RY7JijP%0A3Ae6%2B8M%2FEQDReHYwvUA95BJTB1%2FSQ5zUN0KGX5tRNp%2FUzfx0bw%3D%3D|预订|2400000Z3501|Z35|BXP|GZQ|BXP|CSQ|11:49|01:40|13:51|Y|JFnY5%2Fm%2BR9tdWBkLH3jJReHR76astfTB6ZkXzyE38UbjGlXKTNWNKyOwgUJZG06fL5OGZiMpUN8%3D|20180208|3|P4|01|04|0|0||无||无|||有||无|无|||||1040106030|14163|0",
                    "|预订|2400000G670F|G67|BXP|IZQ|BXP|CWQ|12:13|19:29|07:16|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P3|01|14|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "hrZ3owJDgfNyZusfHDgIMd7u%2BFWaGjTybq7hJBkA0a7JAYcnrwVLGvHlLrvyCaF3ytDTBa0i2wW0%0AFuzi2HSLZfhqJa00oToYZC4gwP0gB7JhHXFIZx2z%2FjNscSJL0lGV9YDx9yKfXdB22E%2BSIQA5efaN%0AbIvF68%2Bl1N9KZKCgtLIcYD%2Fem%2FyGNyLF5Cz8KyaLZDSsWpBx80QXZdClX%2FnKqYgBO5d924n7Jy3m%0AIK375LajmQvcmaazJSkd2shXK3XcJmhZmigQ4dw%3D|预订|240000Z16114|Z161|BXP|KMM|BXP|CSQ|12:34|02:55|14:21|Y|uclevjqhHQTHmAohkyqGwmG13S7TRlZx%2BOhpUCdENgUfygDgdBG4h2YZ0cI%3D|20180208|3|P2|01|08|0|0||||无|||7||无|无|||||10401030|1413|0",
                    "|预订|240000T1451E|T145|BJP|NCG|BJP|CSQ|12:37|05:20|16:43|N|zxzv7atZZ3TC2X8RIvyN7aQtwJNAoHZW5h8fZqdfvCzJqBN6VpBv%2Bs93f%2Bo%3D|20180208|3|P4|01|12|0|0||||无|||无||无|无|||||10403010|1431|0",
                    "qsMKOsf9GJa7lIFBBjfLiU%2FhUbABX%2BRW3qa6qVw3oyEnZ8W4JseDB4slB%2F%2BC6mTK6sH2vhRAjBl4%0AaTK2D4F9lrBaE0uPW7qXuyozO3rUV5b3y5mvKxk2yyUUsXzP0AsXyt55q%2Bc9r4pBPcFrpDZPDLPq%0AFRhOKwBoTWDn1LqcueZTztTg%2FMKnMAqK8jmcaZB5LOuQhR1fSqpptQbiqi2xc0gk2SJfkkETJe7%2B%0Ak%2Fob4g%2F%2FwFXIutGOT%2FRXGb%2BD1ws%2B1kDH8xB6JmaBg6vjLp%2Fszg%3D%3D|预订|2400000Z9703|Z97|BXP|GGQ|BXP|CSQ|12:40|02:26|13:46|Y|SiFLvHHVXxeK%2FqDqNaoYCU1IYVuPIMPqRStWdZH5v0bb8p6RRkiVRKJ9gnALMSBMuQ8EQ7DZXLM%3D|20180208|3|P3|01|04|0|0||无||无|||有||无|无|||||1040601030|14613|0",
                    "|预订|240000G53301|G533|BXP|CWQ|BXP|CWQ|13:02|18:41|05:39|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P3|01|05|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "|预订|2400000G6909|G69|BXP|IZQ|BXP|CWQ|13:07|19:53|06:46|N|xPqIs%2ByfNQYGSpnO4r%2FTyxBI5AKN6c%2BC3OEYCfb10ICbARfh|20180208|3|P4|01|11|1|0|||||||||||无|无|无||O0M090|OM9|0",
                    "|预订|240000G50307|G503|BXP|CWQ|BXP|CWQ|14:41|21:14|06:33|N|fwzHUTM24xYNVsXiu653rPQ8T9cBEeBKZewScdJ2%2BHPpC72f|20180208|3|P3|01|10|1|0|||||||||||无|无|无||O090M0|O9M|0",
                    "|预订|240000G50506|G505|BXP|CWQ|BXP|CWQ|15:40|22:32|06:52|N|7YP8YpA2bDszUnoWLCTTnUO59UE%2BsAGoP2IFbJHgiI772YC6WWBMmp1gtuI%3D|20180208|3|P4|01|13|1|0||||||无|||||无|无|无||O090M0P0|O9MP|0",
                    "|预订|24000000Z509|Z5|BXP|NNZ|BXP|CSQ|16:09|06:08|13:59|N|LgEp8enr3JY3%2FZbqaR3%2F12kK005hmKQW|20180208|3|P4|01|05|0|0||||无|||||无||||||4030|43|0",
                    "|预订|2400000Z770G|Z77|BXP|GIW|BXP|CSQ|16:15|06:14|13:59|N|29TLOXBjDnsXQNX7tJr50%2B3Sh1fZLFiAadOkH3GscR%2B75%2FrugiHlkHfV3wg%3D|20180208|3|P3|01|05|0|0||||无|||无||无|无|||||10401030|1413|0",
                    "|列车运行图调整,暂停发售|240000Z2010K|Z201|BXP|SEQ|BXP|CSQ|24:00|24:00|99:59|IS_TIME_NOT_BUY||20180208||P2|01|06|0|1|||||||||||||||||0",
                    "XYIR93tBv7ujiFp4uz1n4yN3FF9WyrCcgoC5RQSyacpE7CtRFUwhwmEexl9togsoRe7%2FSDxBnCqT%0AmO4gWA46yFkgB272Sjv7AUbPjF%2Fw4FiQ8P0lt8L7L0cSygDaSzfDxyhBwrYgqR2SNSaeCCgctoTa%0AcwhaG3cVMKg9I%2FTfdMJKMpJFTg%2BySfq%2BX4S3WAJMDPYvNb2rDfaPAK0uB0O1A4i1xfTpBR%2B7Ag5s%0AG7sn3AXAoDzCDIMA54pt4qIoXRDDNBVCWw%3D%3D|预订|24000000Z10C|Z1|BXP|CSQ|BXP|CSQ|18:00|08:02|14:02|Y|5u3NZOTZAz2tsxPBzP5A9lQpyFt%2BivBdJ3gUpjCKnY%2FgA27eiRTKSzljuSQ%3D|20180208|3|P2|01|06|0|0||||无|||有||无|无|||||10401030|1413|0",
                    "%2BXSpu0WYN%2FBwCbMftIFNgrOMVCtN9VV2SL4Wmp8Vp4qplCJ719v7Ctb12GS2Xwu2R4pKGGmEk%2B5Q%0AnMT%2BebNgyjAue1N%2BdwSplXaTSNwS6WI1gDNtdurt%2FKV8qjLwHMgiQ8kbr8NxZ%2F5V9XFfIN5y%2FtDE%0ApgIa5xFSl70UltChcbGQUuu7WCsHniTVoVSuWf6%2F1OgSRj57VMq4b4pE5z%2Blu3rdSm%2F9VnEoh6qT%0AjSrEcilMqm8Jfm4LixtRuPpK8FWPRPk1VrgVuig%3D|预订|240000K1571D|K157|BXP|ZJZ|BXP|CSQ|18:12|14:18|20:06|Y|p6bEHWA4JhSjbUQbcTwygJXMlTRkvLd5K4mdn5GhF8LK2e%2B4JsMYyaUlvVw%3D|20180208|3|PB|01|19|0|0||||无|||有||无|无|||||10401030|1413|0",
                    "|预订|250000Z20602|Z207|TJP|CSQ|BJP|CSQ|20:59|11:35|14:36|N|n5Tgo1qTDKhIMij7QMCmoA%3D%3D|20180208|3|P2|03|08|0|0||||无|||||||||||40|4|0",
                    "|预订|240000Z2850A|Z285|BXP|NNZ|BXP|CSQ|21:10|11:16|14:06|N|29TLOXBjDnsXQNX7tJr50%2B3Sh1fZLFiAadOkH3GscR%2B75%2FrugiHlkHfV3wg%3D|20180208|3|P4|01|06|0|0||||无|||无||无|无|||||10401030|1413|0",
                    "mvArYANr%2Bq9zfMUXkMqgoxyk7t8UbFGxvNLsC8Qq2JrTMP3HPKchr5RNxiSeCLPofA6z6fzmx3Vs%0AvJsukL2GhIbcQBk8UBVYAU01gHV14bb6SQCGz9YDa7p5BHx4KG%2BGv6sRMye8Q9FPzXP9Bm11NBP3%0Aoi7Qu7xwkmgX0udGHcK0WAFdCQek03sPfi0XnVAALDMjaIKgDgYWWi14wbM9CWWuDIr325m1b0hp%0A1BhcHwmCinYZNTI9wdTtkiF8ScOEg%2F1WUbSTUoU%3D|预订|2400000Z530R|Z53|BXP|KMM|BXP|CSQ|21:16|11:47|14:31|Y|TP0CPpK%2BM%2Bk3ToVkivCNHqBtyQQtbDriMqv2r4podraKaj6EQPJX1EaE%2FjY%3D|20180208|3|P3|01|08|0|0||||无|||有||无|无|||||10401030|1413|0",
                    "|预订|240000T2890E|T289|BXP|NNZ|BXP|CSQ|22:08|14:09|16:01|N|kk%2F5fMW0r%2Fi3%2FWiGjL8W%2FUTlsofLDRB5Io1BwXwZFFlkG27qoATi7EhKp0hF%2B%2FF4I1x19VfXrrA%3D|20180208|3|P4|01|11|0|0||无||无|||无||无|无|||||1040106030|14163|0"
                ]
            },
            "httpstatus": 200,
            "messages": "",
            "status": True
        }
        return ticket_info["data"]["result"]

    def parse_ticket_info(self, trans_info):
        trains = dict()
        for train_info in trans_info:
            info = train_info.split("|")
            train = dict()
            train["name"] = info[3]
            train["start"] = info[4]
            train["end"] = info[5]
            train["from_station"] = info[6]
            train["to_station"] = info[7]
            train["from_time"] = info[8]
            train["to_time"] = info[9]
            train["duration"] = info[10]
            train["start_date"] = info[13]
            train["from_station_index"] = info[16]  # 出发地站点在整个线路中的编号，编号从1开始，是String类型
            train["to_station_index"] = info[17]
            # train["swz"] = info[20]
            # train["ydz"] = info[21]
            # train["edz"] = info[22]
            # train["gjrw"] = info[23]
            # train["rw"] = info[24]
            # train["dw"] = info[25]
            # train["yw"] = info[26]
            # train["rz"] = info[27]
            # train["yz"] = info[28]
            # train["wz"] = info[29]
            # train["qt"] = info[30]
            train["tickets"] = {
                u"商务座": info[32],  # 也包括特等座
                u"一等座": info[31],  #
                u"二等座": info[30],  #
                u"高级软卧": info[21],  #
                u"软卧": info[23],  #
                u"动卧": info[33],  #
                u"硬卧": info[28],  #
                u"软座": info[20],
                u"硬座": info[29],  #
                u"无座": info[26],  #
                u"其他": info[22]
            }
            trains[train["name"]] = train
        return trains

    def check_tickets(self):
        info = self.query_left_ticket()
        trains_info = self.parse_ticket_info(info)
        results = ""
        if len(self.selected_trains) != 0:
            # 用户已指定车次，将忽略指定车次类型
            for train_name in self.selected_trains:
                if train_name not in trains_info.keys():
                    print(u"车次'%s'未查询到，请重新指定" % train_name)
                    continue
                train_info = trains_info.get(train_name)
                result = ",".join(x for x, y in train_info["tickets"].items()
                                  if (y != "" and y != "无" and x in self.selected_seat_types))
                if result != "":
                    results = results + train_name + " " + result + " 有票\n"
        else:
            matching_trains = {k: v for k, v in trains_info.items()
                               if (k.startswith(t) for t in self.selected_train_types)}
            for name, info in matching_trains.items():
                result = ",".join(x for x, y in info["tickets"].items()
                                  if (y != "" and y != "无" and x in self.selected_seat_types))
                if result != "":
                    results = results + name + " " + result + " 有票\n"

        if results == "":
            results = "no tickets available"
        return results


if __name__ == '__main__':
    print("===========monitor 12306 begin===========")
    monitor = TicketsMonitor()

    while True:
        tickets = monitor.check_tickets()
        print(time.ctime())
        print(tickets)
        time.sleep(monitor.interval)
