#!/usr/bin/env python
import sys
import commands
from PyQt4 import QtGui, QtCore, uic
from ui.qt_interface import InstallerWindow
	
# main entry
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = InstallerWindow()
    sys.exit(app.exec_())
