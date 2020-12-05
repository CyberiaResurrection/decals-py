import os
from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'window_state', 'maximized')
# Config.write()
# YourApp().run()
os.environ["KIVY_IMAGE"] = "pil"

Config.set("kivy", "exit_on_escape", "0")

from wifi import Cell, Scheme
import sys
import traceback

import urllib.request
import json
import math
import subprocess
from subprocess import check_output
import time
import _thread
import requests
import wget
from urllib.parse import urlparse
import qrcode

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.recycleview import RecycleView
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import BooleanProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior

confgiPath = "/home/pi/config.json"


class Environment:
    def __init__(self, url, staging, active):
        self.url = url
        self.staging = staging
        self.active = active


config = {
    "ssid": "VIRGIN730",
    "password": "Password",
    "id": "61692",
    "environments": [
        {
            "apiURL": "https://beercrawl.crawlmedia.com.au/api/v1/ontap/",
            "adResourceURL": "https://beercrawl.crawlmedia.com.au/images/decaladvert/",
            "beerResourceURL": "https://beercrawl.com.au/beer",
            "staging": True,
            "active": True,
        },
        {
            "apiURL": "https://beercrawl.com.au/api/v1/ontap/",
            "adResourceURL": "https://beercrawl.com.au/images/decaladvert/",
            "beerResourceURL": "https://beercrawl.com.au/beer",
            "staging": False,
            "active": False,
        },
    ],
    "ad_time": 8,
}

data = None
newData = None

Builder.load_string(
    """
<SelectableLabel>:
    # Draw a background to indicate selection
    color: (0.0, 0.0, 0.0, 0.9) if self.selected else (1.0, 1.0, 1.0, 1.0)
    canvas.before:
        Color:
            rgba: (0.9, 0.6, 0.0, 1.0) if self.selected else (0.0, 0.0, 0.0, 1.0)
        Rectangle:
            pos: self.pos
            size: self.size

<RV>:
    viewclass: 'SelectableLabel'
    size_hint: None, None
    size: 720, 500
    pos_hint_x: 0
    pos_hint_y: 0
    pos: 0, 0
    scroll_y: 0
    effect_cls: "ScrollEffect" 
    SelectableRecycleBoxLayout:
        id: box
        default_size: 360, dp(56)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        multiselect: False
        touch_multiselect: False
"""
)

cells = list(Cell.all("wlan0"))
configuredCellIndex = -1

try:
    f = open(confgiPath, "r")
    jsonStr = f.read()
    f.close()
    config = json.loads(jsonStr)
except:
    print(traceback.format_exc())


def saveConfiguration():
    global config
    try:
        jsonStr = json.dumps(config)
        f = open(confgiPath, "w")
        f.write(jsonStr)
        f.close()
        print("Configuration is saved")
    except:
        print(traceback.format_exc())


def get_urls():
    global config

    try:
        for i in range(len(config["environments"])):
            if config["environments"][i]["active"]:
                return {
                    "api": config["environments"][i]["apiURL"],
                    "adResource": config["environments"][i]["adResourceURL"],
                    "beerResource": config["environments"][i]["beerResourceURL"],
                }
        return config["environments"][0]["apiURL"]
    except:
        print(traceback.format_exc())
    return {}


def get_qr_code_url():
    global config
    global data

    root = get_urls()["beerResource"] + "/"
    root += data["items"]["slug"]
    root += "?justhadone=true&venue_id="
    root += config["id"]
    return root


def getStaging():
    global config

    try:
        for i in range(len(config["environments"])):
            if config["environments"][i]["active"]:
                return config["environments"][i]["staging"]
        return config["environments"][0]["staging"]
    except:
        print(traceback.format_exc())


saveConfiguration()


def volumeToDrinks(volume):
    return round(1.61 / 425 * 1000.0 * volume, 2)


class SelectableRecycleBoxLayout(
    FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout
):
    """ Adds selection and focus behaviour to the view. """


class SelectableLabel(RecycleDataViewBehavior, Label):
    """ Add selection support to the Label """

    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        """ Catch and handle the view changes """
        self.index = index
        return super(SelectableLabel, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """ Add selection on touch down """
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            self.parent.parent.selectItem(self.index)

    def apply_selection(self, rv, index, is_selected):
        """ Respond to the selection of items in the view. """
        self.selected = is_selected


class RV(RecycleView):
    def __init__(self, **kwargs):
        super(RV, self).__init__(**kwargs)

        self.data = [
            {
                "text": cell.ssid,
                "markup": "True",
                "font_size": "30px",
                "font_name": "Raleway-Regular.ttf",
            }
            for cell in cells
        ]
        self.selectedItem = configuredCellIndex
        self.selectItem(0)
        self.scroll_y = 1

    def nextItem(self):
        if self.selectedItem < len(self.data) - 1:
            self.selectedItem += 1
        else:
            return

        self.scroll_to_index(self.selectedItem)
        self.ids.box.select_node(self.selectedItem)
        print(self.selectedItem)

    def prevItem(self):
        if self.selectedItem > 0:
            self.selectedItem -= 1
        else:
            return

        self.scroll_to_index(self.selectedItem)
        self.ids.box.select_node(self.selectedItem)
        print(self.selectedItem)

    def selectItem(self, index):
        self.selectedItem = index
        self.scroll_to_index(self.selectedItem)
        self.ids.box.select_node(index)

    def scroll_to_index(self, index):
        box = self.children[0]
        pos_index = (box.default_size[1] + box.spacing) * index
        scroll = self.convert_distance_to_scroll(0, pos_index - (self.height * 0.5))[1]
        if scroll > 1.0:
            scroll = 1.0
        elif scroll < 0.0:
            scroll = 0.0
        self.scroll_y = 1.0 - scroll


# ---------------------------------------------------------------
# Settings Screen
# ---------------------------------------------------------------
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        layout = FloatLayout()

        self.wifiList = RV(pos=[0, 750], size=[720, 500])
        self.wifiInput = TextInput(
            pos=[50, 500],
            size=[620, 50],
            text="PASSWORD",
            size_hint_x=None,
            size_hint_y=None,
            font_size=30,
            write_tab=False,
            multiline=False,
            font_name="Raleway-Regular.ttf",
        )

        self.hintLabel = Label(
            text="Press Enter to connect",
            font_size="40px",
            font_name="Raleway-Regular.ttf",
            color=[1, 1, 1, 0.7],
            size=[720, 100],
            pos=[0, 400],
            text_size=[720, 100],
            halign="center",
            size_hint_x=None,
            size_hint_y=None,
        )

        layout.add_widget(self.wifiList)
        layout.add_widget(self.wifiInput)
        layout.add_widget(self.hintLabel)

        self.add_widget(layout)
        self.settingsToUi()
        return None

    def nextItem(self):
        self.wifiList.nextItem()

    def prevItem(self):
        self.wifiList.prevItem()

    def selectItem(self, index):
        self.wifiList.selectItem(index)

    def settingsToUi(self):
        global config

        self.wifiInput.text = config["password"]
        for i in range(len(self.wifiList.data)):
            if config["ssid"] == self.wifiList.data[i]["text"]:
                self.selectItem(i)
                break


# ---------------------------------------------------------------
# Connection Screen
# ---------------------------------------------------------------
class ConnectionScreen(Screen):
    def __init__(self, **kwargs):
        super(ConnectionScreen, self).__init__(**kwargs)

        self.cancelConnect = False

        layout = FloatLayout()
        self.spinner = ProgressBar(
            max=1000,
            value=0,
            pos=[50, 600],
            size=[620, 50],
            size_hint_x=None,
            size_hint_y=None,
        )

        self.anim = Animation(value=0) + Animation(value=1000)
        self.anim.repeat = True
        self.anim.start(self.spinner)

        self.connectLabel = Label(
            text="Connecting to WiFi",
            font_size="60px",
            font_name="Raleway-Regular.ttf",
            color=[1, 1, 1, 1],
            size=[620, 100],
            pos=[50, 700],
            text_size=[620, 100],
            halign="center",
            size_hint_x=None,
            size_hint_y=None,
        )

        self.hintLabel = Label(
            text="Press F2 to skip",
            font_size="40px",
            font_name="Raleway-Regular.ttf",
            color=[1, 1, 1, 0.7],
            size=[620, 100],
            pos=[50, 500],
            text_size=[620, 100],
            halign="center",
            size_hint_x=None,
            size_hint_y=None,
        )

        layout.add_widget(self.spinner)
        layout.add_widget(self.connectLabel)
        layout.add_widget(self.hintLabel)
        self.add_widget(layout)

        return None

    def startConnect(self):
        _thread.start_new_thread(self.connect, ())

    def startUpdateConnection(self):
        _thread.start_new_thread(self.updateConnection, ())

    def updateConnection(self):
        try:
            print("Update connection to ", config["ssid"], ", ", config["password"])
            self.connectLabel.text = "Updating network"
            self.hintLabel.opacity = 0.0

            out = check_output(["wpa_cli", "list_networks"]).decode(sys.stdout.encoding)
            lines = out.splitlines()

            for i in range(len(lines)):
                if i > 1:
                    parts = lines[i].split("\t")
                    id = parts[0].strip()
                    print("Removing existing network ", id)
                    out = check_output(["wpa_cli", "remove_network", id]).decode(
                        sys.stdout.encoding
                    )
                    print(out)

            print("Adding a new network")
            out = check_output(["wpa_cli", "add_network"]).decode(sys.stdout.encoding)
            parts = out.splitlines()
            id = parts[1]
            print(out)

            print("Setting SSID")
            out = check_output(
                ["wpa_cli", "set_network", id, "ssid", '"' + config["ssid"] + '"']
            ).decode(sys.stdout.encoding)
            print(out)

            print("Setting password")
            out = check_output(
                ["wpa_cli", "set_network", id, "psk", '"' + config["password"] + '"']
            ).decode(sys.stdout.encoding)
            print(out)

            print("Selecting network")
            out = check_output(["wpa_cli", "select_network", id]).decode(
                sys.stdout.encoding
            )
            print(out)

            print("Enabling network")
            out = check_output(["wpa_cli", "enable_network", id]).decode(
                sys.stdout.encoding
            )
            print(out)

            print("Saving configuration")
            out = check_output(["wpa_cli", "save_config"]).decode(sys.stdout.encoding)
            print(out)

            self.connectLabel.text = "Restarting"
            time.sleep(3)

            print("Restarting")
            out = check_output(["sudo", "reboot", "now"]).decode(sys.stdout.encoding)
            print(out)

            print("Reconfiguring supplicant")
            out = check_output(["wpa_cli", "reconfigure"]).decode(sys.stdout.encoding)
            print(out)

            print("Restarting daemon")
            out = check_output(["sudo", "systemctl", "daemon-reload"]).decode(
                sys.stdout.encoding
            )
            print(out)

            print("Stopping network")
            out = check_output(["sudo", "systemctl", "stop", "dhcpcd"]).decode(
                sys.stdout.encoding
            )
            print(out)

            print("Starting network")
            out = check_output(["sudo", "systemctl", "start", "dhcpcd"]).decode(
                sys.stdout.encoding
            )
            print(out)
        except:
            print(traceback.format_exc())

    def connect(self):
        global config
        self.connectLabel.text = "Connecting to WiFi"
        self.hintLabel.opacity = 0.5
        print("Connecting to ", config["ssid"], ", ", config["password"])
        time.sleep(3)

        if self.cancelConnect:
            self.anim.stop(self.spinner)
            self.spinner.value = 1000
            self.connectLabel.text = "Cancelled"
            time.sleep(3)
            self.parent.current = "settings"
            return

        connected = False
        for i in range(20):
            if self.cancelConnect:
                self.anim.stop(self.spinner)
                self.spinner.value = 1000
                self.connectLabel.text = "Cancelled"
                time.sleep(3)
                self.parent.current = "settings"
                break

            print("Connecting " + str(i + 1))
            out = check_output(["ifconfig", "wlan0"]).decode(sys.stdout.encoding)
            if "inet " in out:
                connected = True
                break

            time.sleep(1)

        if not self.cancelConnect:
            if connected:
                self.anim.stop(self.spinner)
                self.spinner.value = 1000
                self.connectLabel.text = "Connected"
                time.sleep(3)
                if config["id"] == "":
                    print("Switching to Login")
                    self.parent.current = "login"
                else:
                    print("Switching to Main")
                    self.parent.current = "main"
            else:
                self.anim.stop(self.spinner)
                self.spinner.value = 1000
                self.connectLabel.text = "Failed to connect"
                time.sleep(3)
                self.parent.current = "settings"


# ---------------------------------------------------------------
# Login Screen
# ---------------------------------------------------------------
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        global config
        super(LoginScreen, self).__init__(**kwargs)
        layout = FloatLayout()
        login = Image(source="login.png", pos=[0, 0], size=[720, 1280])
        self.loginInput = Label(
            text="",
            markup=True,
            font_size="80px",
            font_name="Raleway-Regular.ttf",
            color=[1, 1, 1, 1],
            size=[460, 150],
            pos=[30, 30],
            text_size=[500, 150],
            halign="left",
        )

        self.hintLabel = Label(
            text="Press Enter to apply",
            font_size="40px",
            font_name="Raleway-Regular.ttf",
            color=[1, 1, 1, 0.7],
            size=[620, 100],
            pos=[50, 450],
            text_size=[620, 100],
            halign="center",
            size_hint_x=None,
            size_hint_y=None,
        )

        self.stagingLabel = Label(
            text="STAGING",
            font_size="60px",
            font_name="Raleway-Medium.ttf",
            color=[1, 0, 0, 1],
            size=[620, 100],
            pos=[50, 740],
            text_size=[620, 100],
            halign="center",
            size_hint_x=None,
            size_hint_y=None,
        )

        self.login = config["id"]
        self.cursorOn = True

        def cursorBlink():
            self.cursorOn = not self.cursorOn
            self.showInput()

        Clock.schedule_interval(lambda dt: cursorBlink(), 0.5)

        layout.add_widget(login)
        layout.add_widget(self.hintLabel)
        if getStaging():
            layout.add_widget(self.stagingLabel)
        layout.add_widget(self.loginInput)
        self.add_widget(layout)
        return None

    def showInput(self):
        text = self.login
        if self.cursorOn:
            text += "_"
        else:
            text += " "

        self.loginInput.text = "[font=Raleway-Regular.ttf]" + text + "[/font]"

    def checkId(self):
        global config

        success = True

        print("Checking new ID")
        try:
            url = get_urls()["api"] + config["id"]
            print("Loading JSON")
            print(url)
            response = urllib.request.urlopen(url)
            print("Request response status: " + str(response.status))
            if response.status == 200:
                print("JSON loaded for tap code " + config["id"])
                testData = json.loads(response.read().decode())
                if testData["status"] == "ERROR":
                    print("Status = ERROR")
                    success = False
                else:
                    time.sleep(2)
                    mainScreen.start_get_data(dt=None)
                    sm.current = "main"
            else:
                print(
                    "Failed loading JSON for tap code "
                    + config["id"]
                    + ". Status code: "
                    + str(response.status)
                )
                success = False
        except:
            success = False
            print(traceback.format_exc())

        if not success:
            self.hintLabel.text = "Error.\r\nPlease check Tap Code"


class Tap(BoxLayout):
    def __init__(self, **kwargs):
        super(Tap, self).__init__(**kwargs)
        self.size = [720, 600]
        self.orientation = "vertical"
        self.size_hint = (None, None)
        self.pos_hint_x = None
        self.pos_hint_y = None

        self.label1 = Label(
            text="BEER NAME",
            pos=[0, 0],
            size=[720, 85],
            opacity=1.0,
            font_size="65px",
            font_name="Raleway-SemiBold.ttf",
            text_size=self.size,
            halign="left",
            valign="top",
            size_hint=(None, None),
            pos_hint={"x": 0.08},
        )

        self.label2 = Label(
            text="Brewery",
            pos=[0, 0],
            size=[720, 65],
            opacity=1.0,
            font_size="50px",
            font_name="Raleway-Medium.ttf",
            text_size=self.size,
            halign="left",
            valign="top",
            size_hint=(None, None),
            pos_hint={"x": 0.08},
        )

        self.label3 = Label(
            text="Style - abv",
            pos=[0, 0],
            size=[720, 65],
            opacity=1.0,
            font_size="55px",
            font_name="Raleway-Medium.ttf",
            text_size=self.size,
            halign="left",
            valign="top",
            size_hint=(None, None),
            pos_hint={"x": 0.08},
        )

        self.label4 = Label(
            text="",
            pos=[0, 0],
            size=[720, 40],
            opacity=1.0,
            font_size="55px",
            font_name="Raleway-Medium.ttf",
            text_size=self.size,
            halign="left",
            valign="top",
            size_hint=(None, None),
            pos_hint={"x": 0.08},
        )

        self.label5 = Label(
            text="[color=#dca037]Sch.:[/color] [size=45]425ml[/size] [color=#dca037]$8[/color] [size=45]1.61[/size] [size=35]std drinks[/size]",
            pos=[0, 0],
            size=[720, 70],
            opacity=1.0,
            font_size="55px",
            font_name="Raleway-Medium.ttf",
            text_size=self.size,
            halign="left",
            valign="top",
            size_hint=(None, None),
            pos_hint={"x": 0.08},
            markup=True,
        )

        self.label6 = Label(
            text="[color=#dca037]Sch.:[/color] [size=45]425ml[/size] [color=#dca037]$8[/color] [size=45]1.61[/size] [size=35]std drinks[/size]",
            pos=[0, 0],
            size=[720, 70],
            opacity=1.0,
            font_size="55px",
            font_name="Raleway-Medium.ttf",
            text_size=self.size,
            halign="left",
            valign="top",
            size_hint=(None, None),
            pos_hint={"x": 0.08},
            markup=True,
        )

        self.label7 = Label(
            text="[color=#dca037]Sch.:[/color] [size=45]425ml[/size] [color=#dca037]$8[/color] [size=45]1.61[/size] [size=35]std drinks[/size]",
            pos=[0, 0],
            size=[720, 70],
            opacity=1.0,
            font_size="55px",
            font_name="Raleway-Medium.ttf",
            text_size=self.size,
            halign="left",
            valign="top",
            size_hint=(None, None),
            pos_hint={"x": 0.08},
            markup=True,
        )

        self.add_widget(self.label1)
        self.add_widget(self.label2)
        self.add_widget(self.label3)
        self.add_widget(self.label4)
        self.add_widget(self.label5)
        self.add_widget(self.label6)
        self.add_widget(self.label7)

    def apply_data(self, data):
        self.label1.text = data["items"]["beer_name"].upper()
        self.label2.text = data["items"]["brewery"]
        self.label3.text = (
            data["items"]["style"][0] + " - " + data["items"]["abv"] + "%"
        )

        i = 0
        price = float(data["items"]["sizes"][i]["price"])
        if price - math.trunc(price) == 0:
            priceStr = str(math.trunc(price))
        else:
            priceStr = str(price)

        self.label5.text = (
            "[color=#dca037]"
            + data["items"]["sizes"][i]["name"]
            + ":[/color] [size=45]"
            + str(round(float(data["items"]["sizes"][i]["volume"]) * 1000.0))
            + "ml"
            + "[/size] [color=#dca037]$"
            + priceStr
            + "[/color] [size=45]"
            + str(volumeToDrinks(float(data["items"]["sizes"][i]["volume"])))
            + "[/size] [size=35]std drinks[/size]"
        )

        i = 1
        price = float(data["items"]["sizes"][i]["price"])
        if price - math.trunc(price) == 0:
            priceStr = str(math.trunc(price))
        else:
            priceStr = str(price)

        self.label6.text = (
            "[color=#dca037]"
            + data["items"]["sizes"][i]["name"]
            + ":[/color] [size=45]"
            + str(round(float(data["items"]["sizes"][i]["volume"]) * 1000.0))
            + "ml"
            + "[/size] [color=#dca037]$"
            + priceStr
            + "[/color] [size=45]"
            + str(volumeToDrinks(float(data["items"]["sizes"][i]["volume"])))
            + "[/size] [size=35]std drinks[/size]"
        )

        i = 2
        price = float(data["items"]["sizes"][i]["price"])
        if price - math.trunc(price) == 0:
            priceStr = str(math.trunc(price))
        else:
            priceStr = str(price)

        self.label7.text = (
            "[color=#dca037]"
            + data["items"]["sizes"][i]["name"]
            + ":[/color] [size=45]"
            + str(round(float(data["items"]["sizes"][i]["volume"]) * 1000.0))
            + "ml"
            + "[/size] [color=#dca037]$"
            + priceStr
            + "[/color] [size=45]"
            + str(volumeToDrinks(float(data["items"]["sizes"][i]["volume"])))
            + "[/size] [size=35]std drinks[/size]"
        )


# ---------------------------------------------------------------
# Main Screen
# ---------------------------------------------------------------
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

        global config
        self.item_index = 0
        self.sequence = []
        self.data = None
        self.omxProcess = None
        self.header_source = None
        self.advert_sources = []
        self.loading = False

        self.layout = FloatLayout()

        self.statusLabel = Label(
            text="Loading data",
            font_size="60px",
            font_name="Raleway-Regular.ttf",
            color=[1, 1, 1, 1],
            size=[720, 100],
            pos=[0, 700],
            text_size=[720, 100],
            halign="center",
            size_hint_x=None,
            size_hint_y=None,
        )

        self.layout.add_widget(self.statusLabel)

        self.items = []

        self.header = Image(
            source="blank.png",
            pos=[720, 320],
            size=[720, 600],
            opacity=1.0,
            anim_delay=0,
            keep_data=True,
        )

        self.layout.add_widget(self.header)

        tap = Tap(pos=[720, -180])
        self.items.append(tap)

        for i in range(100):
            image = Image(
                source="blank.png",
                pos=[720, -320],
                size=[720, 600],
                opacity=1.0,
                nocache=True,
            )
            self.items.append(image)

        for i in range(len(self.items)):
            self.layout.add_widget(self.items[i])

        self.add_widget(self.layout)

        def next_item(dt):
            global config
            if len(self.sequence) > 1:
                next_item_index = self.item_index + 1
                if next_item_index > len(self.sequence) - 1:
                    next_item_index = 0

                print("Switching to item ", next_item_index)

                p = self.sequence[self.item_index]
                n = self.sequence[next_item_index]

                self.items[n].x = 720

                anim1 = Animation(opacity=0.0, x=-720)
                anim2 = Animation(opacity=1.0, x=0)
                anim1.start(self.items[p])
                anim2.start(self.items[n])

                self.item_index = next_item_index

            Clock.schedule_once(next_item, config["ad_time"])

        Clock.schedule_once(next_item, config["ad_time"])
        self.start_get_data(dt=None)

        # self.omxProcess = subprocess.Popen(['omxplayer', moviepath, '--loop', '--win', '0,10,720,300', '--layer', '100000'],stdin=subprocess.PIPE,stdout=None,stderr=None,bufsize=0)
        return None

    def start_get_data(self, dt):
        if config["id"] == "":
            print("Empty ID")
            Clock.schedule_once(self.start_get_data, 10)
        elif self.parent == None:
            print("No parent")
            Clock.schedule_once(self.start_get_data, 10)
        elif self.parent.current != "main":
            print("Current is not main")
            Clock.schedule_once(self.start_get_data, 10)
        elif self.loading:
            print("Loading in progress")
            Clock.schedule_once(self.start_get_data, 10)
        else:
            _thread.start_new_thread(self.get_data, ())

    def get_data(self):
        global data
        global newData
        global config

        try:
            url = get_urls()["api"] + config["id"]
            print("Loading JSON")
            print(url)
            response = urllib.request.urlopen(url)
            if response.status == 200:
                newData = json.loads(response.read().decode())
                print("JSON loaded for tap code " + config["id"])

                if newData == data:
                    print("JSON not changed")
                else:
                    print("JSON has changed. Loading new data.")
                    self.load_data()
            else:
                print(
                    "Failed loading JSON for tap code "
                    + config["id"]
                    + ". Status code: "
                    + str(response.status)
                )
        except:
            print(traceback.format_exc())

        Clock.schedule_once(self.start_get_data, 10)

    def apply_data(self, dt):
        global data
        global config

        print("Applying data")

        for i in range(len(self.advert_sources)):
            print("Advert " + str(i + 1))
            self.items[i + 2].source = self.advert_sources[i]

        print("Tap info")
        self.items[0].apply_data(data)
        self.items[0].x = 0

        print("QR code")
        self.items[1].source = "qr-code.png"

        self.header.x = 0
        self.statusLabel.x = 720

        self.sequence = []
        count = len(newData["items"]["adverts"])
        if newData["items"]["disableQR"]:
            print("QR code is disabled")
            for i in range(count):
                self.sequence.append(0)
                self.sequence.append(i + 2)
        else:
            print("QR code is enabled")
            for i in range(count):
                self.sequence.append(0)
                self.sequence.append(1)
                self.sequence.append(i + 2)

        print("Header")
        self.header.source = self.header_source

        print("Done")

    def load_data(self):
        global config
        global data
        global newData

        print("Loading data")
        self.loading = True
        try:
            print("Loading header")
            img_url = newData["items"]["img"]
            url = urlparse(img_url)
            img_file = os.path.basename(url.path)

            if os.path.exists(img_file):
                os.remove(img_file)
            print(img_url)
            wget.download(img_url, out=img_file)
            self.header_source = img_file
            print("")

            self.advert_sources = []
            for i in range(len(newData["items"]["adverts"])):
                print("Loading advert " + str(i + 1))
                img_file = newData["items"]["adverts"][i]["filename"]
                img_url = get_urls()["adResource"] + img_file
                print(img_url)
                if os.path.exists(img_file):
                    os.remove(img_file)
                wget.download(img_url, out=img_file)
                self.advert_sources.append(img_file)
                print("")

            data = newData

            print("Generating QR code")
            url = get_qr_code_url()
            print("QR code link: " + url)

            qr = qrcode.QRCode(
                box_size=10,
                border=0,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="white", back_color="black")

            with open("qr-code.png", "wb") as f:
                img.save(f)

            print("Loading is completed")

            Clock.schedule_once(self.apply_data)
        except:
            print(traceback.format_exc())

        self.loading = False


connectionScreen = ConnectionScreen(name="connection")
settingsScreen = SettingsScreen(name="settings")
loginScreen = LoginScreen(name="login")
mainScreen = MainScreen(name="main")

sm = ScreenManager()
sm.add_widget(connectionScreen)
sm.add_widget(settingsScreen)
sm.add_widget(loginScreen)
sm.add_widget(mainScreen)
sm.switch_to(connectionScreen)


class PasswordApp(App):
    # Build
    def build(self):
        self._keyboard = Window.request_keyboard(
            self._keyboard_closed, self.root, "text"
        )
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

        Window.show_cursor = False
        connectionScreen.startConnect()

        return sm

    # Keyboard Down Event
    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        global config

        # Connection Screen ===================================================
        if sm.current == "connection":
            if keycode[1] == "f2":
                connectionScreen.cancelConnect = True
        # Settings Screen =====================================================
        elif sm.current == "settings":
            if keycode[1] == "tab":
                if settingsScreen.wifiInput.focus:
                    settingsScreen.wifiButton.focus = True
                else:
                    settingsScreen.wifiInput.focus = True
            elif keycode[1] == "escape":
                sm.current = "login"
            elif keycode[1] == "down":
                settingsScreen.nextItem()
            elif keycode[1] == "up":
                settingsScreen.prevItem()
            elif keycode[1] == "enter" and len(settingsScreen.wifiInput.text) > 7:
                config["ssid"] = settingsScreen.wifiList.data[
                    settingsScreen.wifiList.selectedItem
                ]["text"]
                config["password"] = settingsScreen.wifiInput.text
                saveConfiguration()
                print("New ssid: ", config["ssid"], ", password: " + config["password"])
                connectionScreen.cancelConnect = False
                connectionScreen.startUpdateConnection()
                sm.switch_to(connectionScreen)
        # Login Screen ========================================================
        elif sm.current == "login":
            if keycode[1] == "enter":
                config["id"] = loginScreen.login
                saveConfiguration()
                loginScreen.checkId()
            elif keycode[1] == "backspace":
                if len(loginScreen.login) > 0:
                    loginScreen.login = loginScreen.login[:-1]
            elif (
                len(keycode[1]) == 1
                and len(loginScreen.login) < 8
                and keycode[1] <= "9"
                and keycode[1] >= "0"
            ):
                loginScreen.login += keycode[1]
            elif keycode[1] == "escape":
                loginScreen.login = config["id"]
                sm.current = "main"

            loginScreen.showInput()
        # Main Screen =========================================================
        elif sm.current == "main":
            if keycode[1] == "escape":
                loginScreen.hintLabel.text = "Press Enter to apply"
                loginScreen.login = config["id"]
                sm.current = "login"

        if keycode[1] == "f10":
            App.get_running_app().stop()
        elif keycode[1] == "f2":
            settingsScreen.settingsToUi()
            loginScreen.login = config["id"]
            sm.current = "settings"
            settingsScreen.wifiInput.focus = True

    # Keyboard Closed Event
    def _keyboard_closed(self):
        # self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        # self._keyboard = None
        pass


PasswordApp().run()
