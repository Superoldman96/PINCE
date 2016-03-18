#!/usr/bin/python3
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QDialog, QCheckBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from time import sleep
from threading import Thread

import GuiUtils
import SysUtils
import GDB_Engine

from GUI.mainwindow import Ui_MainWindow as MainWindow
from GUI.selectprocess import Ui_MainWindow as ProcessWindow
from GUI.addaddressmanuallydialog import Ui_Dialog as ManualAddressDialog

# the PID of the process we'll attach to
currentpid = 0


# Checks if the inferior has been terminated
class AwaitProcessExit(QThread):
    process_exited = pyqtSignal()

    def run(self):
        while SysUtils.is_process_valid(currentpid) or currentpid is 0:
            sleep(0.1)
        self.process_exited.emit()


# the mainwindow
class MainForm(QMainWindow, MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        GuiUtils.center(self)
        self.await_exit_thread = AwaitProcessExit()
        self.await_exit_thread.process_exited.connect(self.on_inferior_exit)
        self.await_exit_thread.start()
        self.processbutton.clicked.connect(self.processbutton_onclick)
        self.pushButton_NewFirstScan.clicked.connect(self.newfirstscan_onclick)
        self.pushButton_NextScan.clicked.connect(self.nextscan_onclick)
        self.pushButton_AddAddressManually.clicked.connect(self.addaddressmanually_onclick)
        self.processbutton.setIcon(QIcon.fromTheme('computer'))
        self.pushButton_Open.setIcon(QIcon.fromTheme('document-open'))
        self.pushButton_Save.setIcon(QIcon.fromTheme('document-save'))
        self.pushButton_Settings.setIcon(QIcon.fromTheme('preferences-system'))
        self.pushButton_CopyToAddressList.setIcon(QIcon.fromTheme('emblem-downloads'))
        self.pushButton_CleanAddressList.setIcon(QIcon.fromTheme('user-trash'))

    def addaddressmanually_onclick(self):
        self.manual_address_dialog = ManualAddressDialogForm()
        self.manual_address_dialog.exec_()

    def newfirstscan_onclick(self):
        if self.pushButton_NewFirstScan.text() == "First Scan":
            self.pushButton_NextScan.setEnabled(True)
            self.pushButton_UndoScan.setEnabled(True)
            self.pushButton_NewFirstScan.setText("New Scan")
            return
        if self.pushButton_NewFirstScan.text() == "New Scan":
            self.pushButton_NextScan.setEnabled(False)
            self.pushButton_UndoScan.setEnabled(False)
            self.pushButton_NewFirstScan.setText("First Scan")

    def nextscan_onclick(self):
        self.add_element_to_addresstable("asdf", "0x00400000", 4)
        # t = Thread(target=GDB_Engine.test)  # test
        # t2=Thread(target=test2)
        # t.start()
        # t2.start()
        if self.tableWidget_valuesearchtable.rowCount() <= 0:
            return

    # shows the process select window
    def processbutton_onclick(self):
        self.processwindow = ProcessForm(self)
        self.processwindow.show()

    def on_inferior_exit(self):
        global currentpid
        GDB_Engine.detach()
        currentpid = 0
        self.label_SelectedProcess.setText("No Process Selected")
        QMessageBox.information(self, "Warning", "Process has been terminated")
        self.await_exit_thread.start()

    # closes all windows on exit
    def closeEvent(self, event):
        if not currentpid == 0:
            GDB_Engine.detach()
        application = QApplication.instance()
        application.closeAllWindows()

    def add_element_to_addresstable(self, description, address, type):
        frozen_checkbox = QCheckBox()
        value = GDB_Engine.read_single_address(address, type)
        type = GuiUtils.valuetype_to_text(type)
        address = GDB_Engine.convert_address_to_symbol(address)
        self.tableWidget_addresstable.setRowCount(self.tableWidget_addresstable.rowCount() + 1)
        currentrow = self.tableWidget_addresstable.rowCount() - 1
        self.tableWidget_addresstable.setCellWidget(currentrow, 0, frozen_checkbox)
        self.tableWidget_addresstable.setItem(currentrow, 1, QTableWidgetItem(description))
        self.tableWidget_addresstable.setItem(currentrow, 2, QTableWidgetItem(address))
        self.tableWidget_addresstable.setItem(currentrow, 3, QTableWidgetItem(type))
        self.tableWidget_addresstable.setItem(currentrow, 4, QTableWidgetItem(value))


# process select window
class ProcessForm(QMainWindow, ProcessWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center_parent(self)
        processlist = SysUtils.get_process_list()
        self.refresh_process_table(self.processtable, processlist)
        self.pushButton_Close.clicked.connect(self.pushbutton_close_onclick)
        self.pushButton_Open.clicked.connect(self.pushbutton_open_onclick)
        self.lineEdit_searchprocess.textChanged.connect(self.generate_new_list)
        self.processtable.itemDoubleClicked.connect(self.pushbutton_open_onclick)

    # refreshes process list
    def generate_new_list(self):
        text = self.lineEdit_searchprocess.text()
        processlist = SysUtils.search_in_processes_by_name(text)
        self.refresh_process_table(self.processtable, processlist)

    # closes the window whenever ESC key is pressed
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

    # lists currently working processes to table
    def refresh_process_table(self, tablewidget, processlist):
        tablewidget.setRowCount(0)
        tablewidget.setRowCount(len(processlist))
        for i, row in enumerate(processlist):
            tablewidget.setItem(i, 0, QTableWidgetItem(str(row.pid)))
            tablewidget.setItem(i, 1, QTableWidgetItem(row.username()))
            tablewidget.setItem(i, 2, QTableWidgetItem(row.name()))

    # self-explanatory
    def pushbutton_close_onclick(self):
        self.close()

    # gets the pid out of the selection to set currentpid
    def pushbutton_open_onclick(self):
        global currentpid
        currentitem = self.processtable.item(self.processtable.currentIndex().row(), 0)
        if currentitem is None:
            QMessageBox.information(self, "Error", "Please select a process first")
        else:
            pid = int(currentitem.text())
            if not SysUtils.is_process_valid(pid):
                QMessageBox.information(self, "Error", "Selected process is not valid")
                return
            if pid == currentpid:
                QMessageBox.information(self, "Error", "You're debugging this process already")
                return
            tracedby = SysUtils.is_traced(pid)
            if tracedby:
                QMessageBox.information(self, "Error",
                                        "That process is already being traced by " + tracedby + ", could not attach to the process")
                return
            print("processing")  # progressbar start
            result = GDB_Engine.can_attach(str(pid))
            if not result:
                print("done")  # progressbar finish
                QMessageBox.information(self, "Error", "Permission denied, could not attach to the process")
                return
            if not currentpid == 0:
                GDB_Engine.detach()
            currentpid = pid
            is_thread_injection_successful = GDB_Engine.attach(str(currentpid))
            p = SysUtils.get_process_information(currentpid)
            self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
            self.parent().QWidget_Toolbox.setEnabled(True)
            self.parent().pushButton_NextScan.setEnabled(False)
            self.parent().pushButton_UndoScan.setEnabled(False)
            readable_only, writeable, executable, readable = SysUtils.get_memory_regions_by_perms(currentpid)  # test
            SysUtils.exclude_system_memory_regions(readable)
            print(len(readable))
            print("done")  # progressbar finish
            if not is_thread_injection_successful:
                QMessageBox.information(self, "Warning", "Unable to inject threads, PINCE may(will) not work properly")
            self.close()


# Add Address Manually Dialog
class ManualAddressDialogForm(QDialog, ManualAddressDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.label_length.hide()
        self.lineEdit_length.hide()
        self.checkBox_Unicode.hide()
        self.comboBox_ValueType.currentIndexChanged.connect(self.valuetype_on_current_index_change)
        self.lineEdit_length.textChanged.connect(self.length_text_on_change)
        self.checkBox_Unicode.stateChanged.connect(self.unicode_box_on_check)
        self.update_needed = False
        self.lineEdit_addaddressmanually.textChanged.connect(self.addaddressmanually_on_change)
        self.update_thread = Thread(target=self.update_value_of_address)
        self.update_thread.daemon = True
        self.update_thread.start()

    # constantly updates the value of the address
    def update_value_of_address(self):
        while not self.update_thread._is_stopped:
            sleep(0.01)
            if self.update_needed:
                self.update_needed = False
                address = self.lineEdit_addaddressmanually.text()
                address_type = self.comboBox_ValueType.currentIndex()
                if address_type is 7:
                    length = self.lineEdit_length.text()
                    self.label_valueofaddress.setText(GDB_Engine.read_single_address(address, address_type, length))
                elif address_type is 6:
                    length = self.lineEdit_length.text()
                    isunicode = self.checkBox_Unicode.isChecked()
                    self.label_valueofaddress.setText(
                        GDB_Engine.read_single_address(address, address_type, length, isunicode))
                else:
                    self.label_valueofaddress.setText(GDB_Engine.read_single_address(address, address_type))

    def addaddressmanually_on_change(self):
        self.update_needed = True

    def length_text_on_change(self):
        self.update_needed = True

    def unicode_box_on_check(self):
        self.update_needed = True

    def valuetype_on_current_index_change(self):
        if self.comboBox_ValueType.currentIndex() == 6:  # if index points to string
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_Unicode.show()
        elif self.comboBox_ValueType.currentIndex() == 7:  # if index points to array of bytes
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_Unicode.hide()
        else:
            self.label_length.hide()
            self.lineEdit_length.hide()
            self.checkBox_Unicode.hide()
        self.update_needed = True

    def reject(self):
        self.update_thread._is_stopped = True
        super(ManualAddressDialogForm, self).reject()

    def accept(self):
        self.update_thread._is_stopped = True
        MainForm.add_element_to_addresstable(MainForm(), self.lineEdit_description.text(),
                                             self.lineEdit_addaddressmanually.text(), 4)
        super(ManualAddressDialogForm, self).accept()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainForm()
    window.show()
    sys.exit(app.exec_())
