#!/usr/bin/env python
import sys
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from ui.qt_interface import InstallerWindow
	
# main entry
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = InstallerWindow()
    sys.exit(app.exec_())
