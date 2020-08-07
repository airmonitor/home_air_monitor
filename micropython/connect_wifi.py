import network


def connect(ssid, password):
    station = network.WLAN(network.STA_IF)

    if station.isconnected():
        print("Already connected")
        return True

    station.active(True)
    station.connect(ssid, password)

    while not station.isconnected():
        pass

    print("Connection successful")
    print(station.ifconfig())
