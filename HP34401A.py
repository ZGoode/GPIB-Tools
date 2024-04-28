import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout, QFrame, QHBoxLayout, QToolBar
import pyvisa
import threading
from threading import Timer, Thread, Event
from functools import partial

class HP34401AInterfaceWidget(QWidget):
    address488 = 0

    current_mode = ""

    # Mode change commands for each measurement function
    mode_commands = [
        "FUNC 'VOLT:DC'", # DC Voltage
        "FUNC 'VOLT:AC'", # AC Voltage
        "FUNC 'CURR:DC'", # DC Current
        "FUNC 'CURR:AC'", # AC Current
        "FUNC 'RES'", # 2W Resistance
        "FUNC 'FRES'", # 4W Resistance
        "FUNC 'CONT'", # Continuity
        "FUNC 'DIOD'", # Diode
        "FUNC 'FREQ'", # Frequency
        "FUNC 'PER'" # Period
    ]

    mode_button_styles = {
        ("VOLT:DC", "Voltage DC", "background-color: blue; color: white;"),
        ("VOLT:AC", "Voltage AC", "background-color: red; color: orange;"),
        ("CURR:DC", "Current DC", "background-color: green; color: white;"),
        ("CURR:AC", "Current AC", "background-color: orange; color: black;"),
        ("RES", "Resistance 2W", "background-color: purple; color: white;"),
        ("FRES", "Resistance 4W", "background-color: cyan; color: black;"),
        ("CONT", "Continuity", "background-color: gray; color: black;"),
        ("DIOD", "Diode", "background-color: yellow; color: black;"),
        ("FREQ", "Frequency", "background-color: darkcyan; color: white;"),
        ("PER", "Period", "background-color: darkmagenta; color: white;"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rm = pyvisa.ResourceManager()

        self.setWindowTitle("HP 34401A Interface")
        self.layout = QVBoxLayout(self)

        # Segment display (simulating data readout)
        self.lcd_display_widget = QWidget()
        self.lcd_display_layout = QHBoxLayout(self.lcd_display_widget)

        self.digits_label = QLabel("34410A DMM")  # Example initial value
        self.digits_label.setStyleSheet("font-size: 36pt; font-weight: bold; border: 2px solid black;")
        self.digits_label.setFixedWidth(800)
        self.lcd_display_layout.addWidget(self.digits_label)

        self.symbol_labels_widget = QWidget()
        self.symbol_labels_layout = QVBoxLayout(self.symbol_labels_widget)

        # Create symbol labels
        symbol_labels = ["4W", "))))", "―⯈|―"]  # Example symbols: 4W, continuity (∞), diode (►)
        self.symbol_label_widgets = [QLabel(symbol) for symbol in symbol_labels]

        for symbol_label in self.symbol_label_widgets:
            symbol_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
            self.symbol_labels_layout.addWidget(symbol_label)

        self.lcd_display_layout.addWidget(self.symbol_labels_widget)

        # Add display widget to the main layout
        self.layout.addWidget(self.lcd_display_widget)

        # Indicator lights (simulating mode/status indicators)
        self.indicator_frame = QFrame()
        self.indicator_frame.setFixedHeight(30)
        self.indicator_frame.setStyleSheet("background-color: gray; border: 1px solid black;")

        # Define indicator labels based on the specified sequence
        self.indicator_labels = [
            "*", "Adrs", "Rmt", "Man", "Trig", "Hold", "Mem", "Ratio", "Math", "ERROR", "Rear", "Shift"
        ]

        # Create QLabel widgets for each indicator
        self.indicator_widgets = [QLabel(text) for text in self.indicator_labels]

        # Add indicator labels to the indicator frame layout
        indicator_layout = QHBoxLayout(self.indicator_frame)
        for label_widget in self.indicator_widgets:
            label_widget.setStyleSheet("font-size: 10pt; font-weight: bold;")
            indicator_layout.addWidget(label_widget)

        self.layout.addWidget(self.indicator_frame)

        # Label for the menu
        self.label = QLabel(f"HP 34401A Menu - GPIB Address:{self.address488}")
        self.layout.addWidget(self.label)

        address_label_font_size = "8pt"  # Adjust this value as needed
        # Apply font size to the GPIB address label
        self.label.setStyleSheet(f"font-size: {address_label_font_size};")

        self.button_grid_layout = QGridLayout()
        self.layout.addLayout(self.button_grid_layout)

        # Define menu options (primary and secondary functions)
        self.primary_menu_options = [
            # Row 1
            ("Voltage AC", self.measure_voltage_ac),
            ("Current AC", self.measure_current_ac),
            ("Resistance 2W", self.measure_resistance_2w),
            ("Frequency", self.frequency),
            ("Continuity", self.continuity),
            ("Null", self.nullset),
            ("Min/Max", self.minmax),
            # Row 2
            ("◀", self.left),  # Custom left arrow icon
            ("▶", self.right),  # Custom right arrow icon
            ("▼", self.down),   # Thick down arrow
            ("▲", self.up),     # Thick up arrow
            ("Auto/Man", self.auto),
            ("Single", self.single),
            ("Shift", self.toggle_shift)
        ]

        self.secondary_menu_options = [
            # Row 1
            ("Voltage DC", self.measure_voltage_dc),
            ("Current DC", self.measure_current_dc),
            ("Resistance 4W", self.measure_resistance_4w),
            ("Period", self.measure_period),
            ("Diode", self.measure_diode),
            ("dB", self.db),
            ("dBm", self.dbm),
            # Row 2
            ("Menu On/Off", self.menu),
            ("Recall", self.recall),
            ("4 Digits", self.digits4),
            ("5 Digits", self.digits5),
            ("6 Digits", self.digits6),
            ("Auto/Hold", self.autohold),
            ("Shift", self.toggle_shift)
        ]

        # Initialize menu as primary (non-shifted)
        self.is_shifted = False
        self.update_menu(self.primary_menu_options)

        # Variable to track 4W mode state
        self.is_in_4w_mode = False

        # Variable to track diode mode state
        self.is_in_diode_mode = False

    def update_menu(self, menu_options):
        # Clear existing buttons
        for i in reversed(range(self.button_grid_layout.count())):
            widget = self.button_grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Populate grid layout with buttons
        num_cols = 7  # Number of columns for each row
        button_width = 120  # Fixed button width
        button_height = 40  # Fixed button height

        for idx, (option_text, callback) in enumerate(menu_options):
            row = idx // num_cols
            col = idx % num_cols
            button = QPushButton(option_text)
            button.setFixedSize(button_width, button_height)  # Set fixed size for the button
            button.clicked.connect(callback)
            self.button_grid_layout.addWidget(button, row, col)
            
            button_font_size = "6pt"  # Adjust this value as needed
            button.setStyleSheet(f"font-size: {button_font_size};")


    def toggle_shift(self):
        self.is_shifted = not self.is_shifted
        if self.is_shifted:
            self.update_menu(self.secondary_menu_options)
        else:
            self.update_menu(self.primary_menu_options)

    # Primary menu option callbacks
    def measure_voltage_ac(self):
        self.digits_label.setText("123.45 V")
        print("Performing Voltage AC Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[1]}")
        self.change_mode(self.address488, self.mode_commands[1])
        print()

    def measure_current_ac(self):
        self.digits_label.setText("1.23 A")
        print("Performing Current AC Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[3]}")
        self.change_mode(self.address488, self.mode_commands[3])
        print()

    def measure_resistance_2w(self):
        self.digits_label.setText("1000 Ω")
        print("Performing Resistance 2W Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[4]}")
        self.change_mode(self.address488, self.mode_commands[4])
        print()

    def frequency(self):
        self.digits_label.setText("50.0 Hz")
        print("Performing Frequency Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[8]}")
        self.change_mode(self.address488, self.mode_commands[8])
        print()

    def continuity(self):
        self.digits_label.setText("∞")
        print("Performing Continuity Test")
        self.reset_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[6]}")
        self.change_mode(self.address488, self.mode_commands[6])
        print()

    def nullset(self):
        self.digits_label.setText("Null")
        print("Performing Null Operation")

    def minmax(self):
        self.digits_label.setText("Min/Max")
        print("Min Max Mode")

    def left(self):
        print("Left")

    def right(self):
        print("Right")

    def up(self):
        print("Up")

    def down(self):
        print("Down")

    def auto(self):
        print("Auto/Manual")

    def single(self):
        print("Single Reading")

    # Secondary menu option callbacks (Shifted mode)
    def measure_voltage_dc(self):
        self.digits_label.setText("234.56 V")
        print("Performing Voltage DC Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[0]}")
        self.change_mode(self.address488, self.mode_commands[0])
        print()

    def measure_current_dc(self):
        self.digits_label.setText("2.34 A")
        print("Performing Current DC Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[2]}")
        self.change_mode(self.address488, self.mode_commands[2])
        print()

    def measure_resistance_4w(self):
        self.digits_label.setText("2000 Ω")
        print("Performing 4-Wire Resistance Measurement")
        self.set_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[5]}")
        self.change_mode(self.address488, self.mode_commands[5])
        print()

    def measure_period(self):
        self.digits_label.setText("10.0 s")
        print("Performing Period Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()
        print(f"Setting mode to {self.mode_commands[9]}")
        self.change_mode(self.address488, self.mode_commands[9])
        print()

    def measure_diode(self):
        self.digits_label.setText("0.65")
        print("Performing Diode Measurement")
        self.reset_4w_indicator()
        self.set_diode_indicator()
        print(f"Setting mode to {self.mode_commands[7]}")
        self.change_mode(self.address488, self.mode_commands[7])
        print()

    def db(self):
        print("Performing dB Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()

    def dbm(self):
        print("Performing dBm Measurement")
        self.reset_4w_indicator()
        self.reset_diode_indicator()

    def menu(self):
        print("Menu")
        self.reset_4w_indicator()
        self.reset_diode_indicator()

    def recall(self):
        print("Recall")
        self.reset_4w_indicator()
        self.reset_diode_indicator()

    def digits4(self):
        print("4 Digits")

    def digits5(self):
        print("5 Digits")

    def digits6(self):
        print("6 Digits")

    def autohold(self):
        print("Auto Hold")

    def set_4w_indicator(self):
        self.is_in_4w_mode = True
        self.symbol_label_widgets[0].setStyleSheet("font-size: 12pt; font-weight: bold; color: green;")

    def reset_4w_indicator(self):
        if self.is_in_4w_mode:
            self.is_in_4w_mode = False
            self.symbol_label_widgets[0].setStyleSheet("font-size: 12pt; font-weight: bold; color: black;")

    def set_diode_indicator(self):
        self.is_in_diode_mode = True
        self.symbol_label_widgets[2].setStyleSheet("font-size: 12pt; font-weight: bold; color: green;")

    def reset_diode_indicator(self):
        if self.is_in_diode_mode:
            self.is_in_diode_mode = False
            self.symbol_label_widgets[2].setStyleSheet("font-size: 12pt; font-weight: bold; color: black;")

    def change_mode(self, gpib_address, mode_command):
    # Open a VISA resource manager session
        rm = pyvisa.ResourceManager()

        try:
            # Open the GPIB instrument connection
            with self.rm.open_resource(f"GPIB::{gpib_address}") as instrument:
                # Set the measurement function to the specified mode
                instrument.write(mode_command)

                # Query the current measurement function to verify the change
                response = instrument.query("FUNC?")
                self.current_mode = response.strip()
                print("Current Measurement Function:", self.current_mode)


        except pyvisa.VisaIOError as e:
            print(f"VISA I/O Error: {e}")

    def set_address(self, gpib_address):
        print(f"Old address: {self.address488}")
        print(f"New address: {gpib_address}")
        self.address488 = gpib_address
        print(f"Updated to:{self.address488}")
        self.label.setText(f"HP 34401A Menu - GPIB Address: {self.address488}")

    def closeRM(self):
        # Close the connection to the instrument
        self.rm.close()

    def measureReturn(self):
        try:
            # Open connection to the GPIB device
            with self.rm.open_resource(f"GPIB::{self.address488}") as instrument:

                # Trigger a single measurement and wait for completion
                instrument.write('INIT')
                instrument.write('*WAI')  # Wait until measurement is done

                # Query the measured current value
                current_str = instrument.query('FETC?')

                # Parse the current value from the response (assuming a float result)
                current = float(current_str.strip())
                
                self.digits_label.setText(str(current))

                return current

        except pyvisa.Error as e:
            print(f"VISA error: {e}")
            return None

class perpetualTimer():
    interval = 0.5
    #can succesfully change interval value without having to restart the timer function.  YAY!!!!

    def __init__(self,hFunction):
        self.hFunction = hFunction
        self.thread = Timer(self.interval,self.handle_function)

    def handle_function(self):
        self.hFunction()
        self.thread = Timer(self.interval,self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

    def cancel(self):
        self.thread.cancel()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HP 34401A Controller")

        # Create a toolbar
        toolbar = self.addToolBar("Main Toolbar")

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)
        self.hp34401a_interface = HP34401AInterfaceWidget()
        self.layout.addWidget(self.hp34401a_interface)


    def closeEvent(self, event):
        # Ensure proper cleanup when the main window is closed
        self.hp34401a_interface.closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 300)
    window.show()

    # Access the HP34401AInterfaceWidget instance from MainWindow
    interface = window.hp34401a_interface
    
    # Set the GPIB address using the set_address method
    interface.set_address(2)

    def measure_and_return():
        return interface.measureReturn()

    timeDevice = perpetualTimer(measure_and_return)
    timeDevice.start()

    def cleanup():
        timeDevice.cancel()
        interface.closeRM()

    #cleanup code to properly close everything upon exit of window
    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec_())