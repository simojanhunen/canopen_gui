# CANopen GUI

<div align='center'>
    <div>
Used to send and receive SDOs using CANopen protocol. The device on the other end has to support CANopen protocol and a valid EDS file has to be found with available message configurations. 

**Note: Supports only PCAN-adapters. The program expects the presence of CANopen object "Producer Heartbeat Time", which is hardcoded to 500 kbit/s.**
    </div>
    <br>
    <img src='assets/help.png' alt='icon' width='750px'>
</div>

## Generate resources

Resource script `icons.py` is generated with
```
pyside2-rcc src/icons/icons.qrc -o src/icons.py
```
