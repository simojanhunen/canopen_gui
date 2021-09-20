# Standard libraries
import sys
from functools import partial
from PySide2.QtCore import ( QFile, Qt, QSize)
from PySide2.QtGui import ( QIcon )
from PySide2.QtWidgets import ( QApplication, QCheckBox, QComboBox, QMenu, QPushButton, QSizePolicy, QMainWindow, QFileDialog,
                                QMessageBox, QTextEdit, QToolBar, QVBoxLayout, QHBoxLayout, QAction, QComboBox, QWidget)

# Custom libraries
import canopenitf as citf
import icons # used icons
from version import * # version numbers
import os

DEFAULT_HEIGHT = 25
APPLICATION_TITLE = " CANopen GUI "
VERSION = "Version {}.{}.{}".format(MAJOR, MINOR, PATCH)

class MainWindow(QMainWindow):
    def __init__(self, app=None, controller=None):
        super().__init__()
        self.main_widget = QWidget()
        self.controller = controller
        self.continuous_state = True
        self.app = app

        self.icons = self.fetch_icons()
        self.create_actions()
        self.create_widgets()
        self.refresh_message_lists()
        self.refresh_title()
        self.setWindowIcon(self.icons['logo'])

    def create_widgets(self):
        # Set top and bottom toolbars/menus
        self.create_menus()
        self.create_toolbars()
        self._status_bar = self.statusBar()

        # RX CONFIGURATION
        self._rx_dropdown_message = QComboBox()
        self._rx_dropdown_message.setMaximumHeight(DEFAULT_HEIGHT)
        self._rx_dropdown_message.addItems([])
        self._rx_dropdown_message.setCurrentIndex(0)
        self._rx_dropdown_message.setEditable(False)

        self._rx_value_box = QTextEdit()
        self._rx_value_box.setMaximumWidth(6*DEFAULT_HEIGHT)
        self._rx_value_box.setMaximumHeight(DEFAULT_HEIGHT)

        self._rx_send_button = QPushButton("Send", clicked=lambda: self.send_rx_message(
                                                                        data=self._rx_dropdown_message.currentData(), 
                                                                        value=self._rx_value_box.toPlainText()))
        self._rx_send_button.setMaximumWidth(2*DEFAULT_HEIGHT)
        self._rx_send_button.setMaximumHeight(DEFAULT_HEIGHT)

        rx_configuration = QHBoxLayout()
        rx_configuration.addWidget(self._rx_dropdown_message)
        rx_configuration.addWidget(self._rx_value_box)
        rx_configuration.addWidget(self._rx_send_button)

        self._rx_textbox = QTextEdit()
        self._rx_textbox.setText("")

        # TX CONFIGURATION
        self._tx_dropdown_message = QComboBox()
        self._tx_dropdown_message.setMaximumHeight(DEFAULT_HEIGHT)
        self._tx_dropdown_message.addItems([])
        self._tx_dropdown_message.setCurrentIndex(0)
        self._tx_dropdown_message.setEditable(False)

        self._tx_dropdown_type = QComboBox()
        self._tx_dropdown_type.setMaximumWidth(4*DEFAULT_HEIGHT)
        self._tx_dropdown_type.setMaximumHeight(DEFAULT_HEIGHT)
        self._tx_dropdown_type.addItems(["Decimal", "Hexadecimal", "Binary", "Ascii"])
        self._tx_dropdown_type.setCurrentIndex(0)

        self._tx_recv_button = QPushButton("Receive", clicked=lambda: self.recv_tx_message(
                                                                        data=self._tx_dropdown_message.currentData(), 
                                                                        type=self._tx_dropdown_type.currentText()))
        self._tx_recv_button.setMaximumWidth(4*DEFAULT_HEIGHT)
        self._tx_recv_button.setMaximumHeight(DEFAULT_HEIGHT)

        tx_configuration = QHBoxLayout()
        tx_configuration.addWidget(self._tx_dropdown_message)
        tx_configuration.addWidget(self._tx_dropdown_type)
        tx_configuration.addWidget(self._tx_recv_button)

        self._tx_textbox = QTextEdit()
        self._tx_textbox.setText("")

        # Create main layout and populate it
        main_layout = QVBoxLayout()

        # Top-side (rx) layout
        main_layout.addLayout(rx_configuration)
        main_layout.addWidget(self._rx_textbox)

        # Bottom-side (tx) layout
        main_layout.addLayout(tx_configuration)
        main_layout.addWidget(self._tx_textbox)

        self.main_widget.setLayout(main_layout)
        self.setCentralWidget(self.main_widget)

    def create_actions(self):
        self._exit_act = QAction(self.icons['exit'], "E&xit", self, statusTip="Exit the application", triggered=self.close)
        self._open_act = QAction(self.icons['close'], "&Open", self,  statusTip="Open an EDS file", triggered=self.open)
        self._help_act = QAction(self.icons['info'], "&Help", self, statusTip="About", triggered=self.about)
        self._refresh_act = QAction(self.icons['refresh'], "&Refresh", self, statusTip="Refresh connection", triggered=self.refresh)

    def refresh(self):
        self._status_bar.showMessage("Connection was refreshed.", 4000)
        self._status_bar.showMessage(f"{self.controller.scan_nodes()}", 4000)
        self.refresh_node_id_menu()
        self.refresh_active_node_id()

    def send_rx_message(self, data, value):
        data.data = value
        self._rx_textbox.append(self.controller.send_sdo(msg=data))

    def recv_tx_message(self, data, type):
        self._tx_textbox.append(self.controller.recv_sdo(msg=data, type=type))

    def change_node_id(self, new_node_id):
        self._status_bar.showMessage("Node id %s is now used." % (new_node_id), 4000)
        self.controller.set_current_node_id(new_node_id)
        self.refresh_title()
   
    def create_menus(self):
        self._file_menu = self.menuBar().addMenu("&File")
        self._file_menu.addAction(self._open_act)
        self._file_menu.addSeparator()
        self._file_menu.addAction(self._exit_act)

        self.menuBar().addSeparator()

        self._settings_menu = self.menuBar().addMenu("Settings")
        self._settings_menu.setLayoutDirection(Qt.LeftToRight)

        self.node_id_menu = QMenu("Node ID")
        self.refresh_node_id_menu()
        self._settings_menu.addMenu(self.node_id_menu)

    def refresh_node_id_menu(self):
        self.node_id_menu.clear()
        available_nodes = self.controller.get_available_node_ids()

        if len(available_nodes) == 0:
            self.node_id_menu.addAction("None found, try refreshing or open a new EDS file.")
        else:
            for node in available_nodes:
                self.node_id_menu.addAction(str(node), partial(self.change_node_id, node))

    def refresh_title(self):
        self.setWindowTitle(f"{APPLICATION_TITLE} - {VERSION}")

    def create_toolbars(self):
        self._spacer = QWidget()
        self._spacer.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self._tool_bar = QToolBar()
        self._tool_bar.setMovable(False)
        self._tool_bar.setFixedHeight(40)
        self._tool_bar.addAction(self._open_act)
        self._tool_bar.addAction(self._refresh_act)
        self._active_node_action = QAction(f"Active node id: {self.controller.get_current_node_id()}")
        self._tool_bar.addAction(self._active_node_action)
        self._tool_bar.addWidget(self._spacer)
        self._tool_bar.addAction(self._help_act)
        self._tool_bar.setMovable(False)
        self._tool_bar.setFixedHeight(DEFAULT_HEIGHT)
        self.addToolBar(self._tool_bar)

    def closeEvent(self, event):
        popup = QMessageBox()
        reply = popup.question(self, APPLICATION_TITLE,
            "Are you sure you want to quit?", popup.Yes, popup.No)
        if reply == popup.Yes:
            self.controller._disconnect()
            event.accept()
        else:
            event.ignore()

    # TODO: implementation of threads
    def continuous_state(self, status):
        if status:
            self.continuous_state = True
        else:
            self.continuous_state = False

    def open(self):
        fileName, filtr = QFileDialog.getOpenFileName(self)
        if fileName:
            self.load_file(fileName)

    def load_file(self, fileName):
        file = QFile(fileName)
        if not file.open(QFile.ReadOnly | QFile.Text):
            reason = file.errorString()
            QMessageBox.warning(self, "Application", f"Cannot read file {fileName}:\n{reason}.")
            return
        elif not fileName.endswith(".eds"):
            reason = f"File '{fileName}' is not a valid EDS file."
            QMessageBox.warning(self, "Application", f"{reason}")
            return

        self.controller.set_current_eds_file(fileName)
        self._status_bar.showMessage("%s was loaded." % (fileName.rsplit("/", 1)[1]), 4000)
        self.refresh_message_lists()
        self.refresh_node_id_menu()
        self.refresh_active_node_id()

    def refresh_active_node_id(self):
        self._active_node_action.setText(f"Active node id: {self.controller.get_current_node_id()}")

    def about(self):
        QMessageBox.about(self, "About",
            f"""<b>{APPLICATION_TITLE}</b> is a tool for communicating SDO messages between host pc and a device. 
            An EDS file is required of the user to send and receive messages. If the host pc finds only one node id
            when the EDS file is loaded, then that is automatically used.<br><br>
            <b>Sending:</b><br>
            Available values to send include decimal (e.g., 100), hexadecimal (e.g., 0x64) and binary (e.g, 0b1100100).<br><br>
            <b>Receiving:</b><br>
            The type of received messages can be configured as either Decimal, Hexadecimal, Binary or Ascii.<br><br>
            {VERSION}""")

    def refresh_message_lists(self):
        self._rx_dropdown_message.clear()
        self._tx_dropdown_message.clear()
        send_list, recv_list = self.controller.get_eds_contents()

        for entry in send_list:
            message, data = entry
            self._rx_dropdown_message.addItem(message, data)

        for entry in recv_list:
            message, data = entry
            self._tx_dropdown_message.addItem(message, data)

    def fetch_icons(self):
        logo_icon = QIcon()
        logo_icon.addFile(':/logo24.png', QSize(24, 24))
        logo_icon.addFile(':/logo32.png', QSize(32, 32))
        logo_icon.addFile(':/logo48.png', QSize(48, 48))
        logo_icon.addFile(':/logo96.png', QSize(96, 96))
        close_icon = QIcon(':/folder_closed.png')
        open_icon = QIcon(':/folder_opened.png')
        settings_icon = QIcon(':/settings.png')
        refresh_icon = QIcon(':/refresh.png')
        online_icon = QIcon(':/online.png')
        info_icon = QIcon(':/info.png')
        menu_icon = QIcon(':/menu.png')
        exit_icon = QIcon(':/exit.png')

        icons = {
            'logo' : logo_icon,
            'close' : close_icon,
            'open' : open_icon,
            'settings' : settings_icon,
            'refresh' : refresh_icon,
            'online' : online_icon,
            'info' : info_icon,
            'menu' : menu_icon,
            'exit' : exit_icon
        }
        return icons

def main():
    # Set the Python process as unique one instead of a general python executable when Windows is used.
    if os.name == 'nt':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPLICATION_TITLE)

    cancontroller = citf.CanOpenItf()
    app = QApplication(sys.argv)
    main = MainWindow(app, cancontroller)
    main.resize(1000, 800)
    main.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
