import canopen
import time

from canopen.objectdictionary import datatypes

CANOPEN_DATA_TYPES = {
    "Boolean": 0x0001,
    "Integer": 0x0002,
    "Integer": 0x0003,
    "Integer": 0x0004,
    "Unsigned Integer": 0x0005,
    "Unsigned Integer": 0x0006,
    "Unsigned Integer": 0x0007,
    "Float": 0x0008,
    "String": 0x0009,
    "Octet String": 0x000A,
    "Date": 0x000B,
    "Time of Day": 0x000C,
    "Time Difference": 0x000D,
    "Bit String": 0x000E,
    "Domain": 0x000F,
    "PDO CommPar": 0x0020,
    "PDO Mapping": 0x0021,
    "SDO Parameter": 0x0022
}

class CanOpenMessage():
    def __init__(self, index=None, subindex=None, bits=None, data=None):
        self.index = index
        self.subindex = subindex
        self.bits = bits
        self.data = data

class CanOpenItf():
    def __init__(self, eds=None, node_id=None):
        self.current_eds_file_path = eds
        self.current_node_id = node_id
        self.network = None
        self.create_network()
        self.scan_nodes()

    def _disconnect(self):
        self.network.disconnect()

    def create_network(self):
        self.network = canopen.Network()
        try:
            self.network.connect(bustype='pcan', channel='PCAN_USBBUS1', bitrate=250000)
        except Exception as e:
            print(f"Creating network failed due to '{e}'")

    def scan_nodes(self):
        if not self.current_eds_file_path:
            return "Provide valid EDS file before scanning nodes."

        self.network.clear()
        self.network.scanner.search()
        time.sleep(0.5)
        for node in self.network.scanner.nodes:
            self.network.add_node(node, self.current_eds_file_path)

        if len(self.network.keys()) == 1:
            self.set_current_node_id(list(self.network.keys())[0])

        if len(list(self.network.keys())) > 0:
            return "Node scan successful."
        else:
            return "No nodes were found."

    def get_eds_contents(self):
        if not self.current_node_id:
            info = "There is no active/valid EDS file."
            return ( [[info, CanOpenMessage()]], [[info, CanOpenMessage()]] )

        sendable = []
        receivable = []
        if self.network.nodes[self.current_node_id]:
            for obj in self.network.nodes[self.current_node_id].object_dictionary.values():
                n_bits = len(obj)
                if isinstance(obj, canopen.objectdictionary.Variable):
                    data_type = self.get_datatype_name(obj.data_type)
                    elem = [ f'{hex(obj.index)}.{hex(obj.subindex)}: {obj.name}, {data_type}, {n_bits}-bit', 
                                CanOpenMessage(obj.index, obj.subindex, n_bits) ]
                    sendable, receivable = self.add_if_access_matches(sendable, receivable, obj.access_type, elem)
                elif isinstance(obj, canopen.objectdictionary.Record) or \
                     isinstance(obj, canopen.objectdictionary.Array):
                    for subobj in obj.values():
                        data_type = self.get_datatype_name(subobj.data_type)
                        elem = [ f'{hex(obj.index)}.{hex(subobj.subindex)}: {subobj.name}, {data_type}, {n_bits}-bit', 
                                    CanOpenMessage(obj.index, subobj.subindex, n_bits) ]
                        sendable, receivable = self.add_if_access_matches(sendable, receivable, subobj.access_type, elem)
            return sendable, receivable

    def add_if_access_matches(self, send_list, recv_list, access_type, elem):
        if access_type in ["rw", "rww", "rwr"]:
            recv_list.append(elem)
            send_list.append(elem)
        elif access_type in ["ro", "const"]:
            recv_list.append(elem)
        elif access_type == "wo":
            send_list.append(elem)
        return send_list, recv_list

    def get_datatype_name(self, object_data_type):
        data_type = "Unknown"
        for name, value in CANOPEN_DATA_TYPES.items():
            if object_data_type == value:
                data_type = name
        return data_type

    def set_current_eds_file(self, eds_file_path):
        self.current_eds_file_path = eds_file_path
        self.scan_nodes()

    def set_current_node_id(self, node_id):
        self.current_node_id = node_id
        return self.set_nmt_mode_operational()

    def get_current_node_id(self):
        return "None" if not self.current_node_id else self.current_node_id;

    def set_nmt_mode_operational(self):
        try:
            self.network.nodes[self.current_node_id].sdo["Producer Heartbeat Time"].raw = 500
            self.network.nodes[self.current_node_id].nmt.state = 'OPERATIONAL'
            return f"NMT mode is operational."
        except Exception:
            self.network.nodes[self.current_node_id].nmt.state = 'STOPPED'
            return f"NMT mode could not be changed due to missing canopen object."

    def get_available_node_ids(self):
        return list(self.network.keys())

    def send_sdo(self, msg: CanOpenMessage):
        index = msg.index
        subindex = msg.subindex
        bits = msg.bits
        data = int(eval(msg.data))

        if (data < 0):
            data_to_send = (data).to_bytes(bits // 8, byteorder='little', signed=True)
        else:
            data_to_send = (data).to_bytes(bits // 8, byteorder='little', signed=False)

        try:
            self.network.nodes[self.current_node_id].sdo.download(index, subindex, bytes(data_to_send))
            msg = f"Send {hex(index)}.{hex(subindex)}, data: {data} {hex(data)} {bin(data)}"
        except Exception as e:
            msg = f"Send {hex(index)}.{hex(subindex)} failed with error '{e}'."
        
        return msg

    def recv_sdo(self, msg: CanOpenMessage, type):
            index = msg.index
            subindex = msg.subindex
            try:
                data = self.network.nodes[self.current_node_id].sdo.upload(index, subindex)
                converted_data = self.convert_data_to_type(data, type)
                msg = f"Read {hex(index)}.{hex(subindex)}, received {converted_data}"
            except Exception as e:
                msg = f"Read {hex(index)}.{hex(subindex)} failed with error '{e}'."
            return msg

    def convert_data_to_type(self, data, type):
        if type == "Hexadecimal":
            value = hex(int.from_bytes(data, byteorder='little'))
        elif type == "Binary":
            value = bin(int.from_bytes(data, byteorder='little'))
        elif type == "Ascii":
            value = ascii(data)
        # Decimal
        else:
            value = int.from_bytes(data, byteorder='little')
        return value

if __name__ == "__main__":
    exit()
