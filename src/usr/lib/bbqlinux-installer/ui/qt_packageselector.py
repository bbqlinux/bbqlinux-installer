#!/usr/bin/env python

import os
import subprocess
import tarfile

from PyQt4 import QtGui, QtCore, uic

PKG_REPO = 0
PKG_NAME = 1
PKG_VERSION = 2
PKG_DESC = 3

GUI_PACKAGE_CHECKBOX = 0
GUI_PACKAGE_NAME = 1
GUI_PACKAGE_VERSION = 2

class WorkThread(QtCore.QThread):
	
    repo_db_dir = '/var/lib/pacman/sync/'

    def __init__(self):
        QtCore.QThread.__init__(self)
        
    def build_repo_list(self):
        self.repoList = []

        dirList=os.listdir(self.repo_db_dir)
        for fname in dirList:
            # Remove file extension
            repo = fname[:-3]
            self.repoList.append(repo)
 
    def run(self):
        ''' Parse package database '''
        self.build_repo_list()
        packageList = list()
        pkg_num = 0

        for repo in self.repoList:
            tar = tarfile.open(mode="r:*", fileobj = file(self.repo_db_dir + repo + '.db'))

            memberList = tar.getmembers()

            for member in memberList:        
                if (member.name.endswith('/desc')):
                    pkg_num += 1
                    packageData = list()
                    packageData.insert(PKG_REPO, repo)

                    fobject = tar.extractfile(member)

                    loop = 1
                    while loop == 1:
                        content = fobject.readline()
                        # If we've reached EOF, break
                        if not content:
                            loop = 0

                        if "%NAME%" in content:
                            pkg_name = fobject.readline().rstrip('\n')
                            packageData.insert(PKG_NAME, pkg_name)

                        if "%VERSION%" in content:
                            pkg_version = fobject.readline().rstrip('\n')
                            packageData.insert(PKG_VERSION, pkg_version)

                        if "%DESC%" in content:
                            pkg_desc = ""
                            desc_loop = 1
                            while desc_loop == 1:
                                content = fobject.readline()
                                if (not content == '\n'):
                                    pkg_desc += content
                                else:
                                    desc_loop = 0
                            packageData.insert(PKG_DESC, pkg_desc)
                            loop = 0

                    packageList.insert(pkg_num, packageData)  
        self.emit(QtCore.SIGNAL('aa'), packageList, self.repoList)
        return

class PackageSelector(object):

    resource_dir = '/usr/share/bbqlinux-installer/'

    def __init__(self, setup):
        self.ui = uic.loadUi('/usr/share/bbqlinux-installer/qt_package_selector.ui')
        
        # Connect the buttons
        QtCore.QObject.connect(self.ui.doneButton, QtCore.SIGNAL("clicked()"), self.doneButton_clicked)
        QtCore.QObject.connect(self.ui.clearButton, QtCore.SIGNAL("clicked()"), self.clearButton_clicked)
        QtCore.QObject.connect(self.ui.searchButton, QtCore.SIGNAL("clicked()"), self.searchButton_clicked)
        QtCore.QObject.connect(self.ui.searchEdit, QtCore.SIGNAL("returnPressed()"), self.searchButton_clicked)

        # Connect the repo list
        QtCore.QObject.connect(self.ui.repoListWidget, QtCore.SIGNAL("itemClicked(QListWidgetItem *)"), self.repoListItem_clicked)

        # Connect the package table
        QtCore.QObject.connect(self.ui.packageTableWidget, QtCore.SIGNAL("itemClicked(QTableWidgetItem *)"), self.packageTableWidgetItem_clicked)
        QtCore.QObject.connect(self.ui.queueTableWidget, QtCore.SIGNAL("itemClicked(QTableWidgetItem *)"), self.queueTableWidgetItem_clicked)

        # adding by emitting signal in different thread
        self.workThread = WorkThread()
        QtCore.QObject.connect(self.workThread, QtCore.SIGNAL('aa'), self.build_package_list)
        self.workThread.start()
        self.packageList = []
        
        # Get a list of installed packages
        self.list_installed_packages()

        # Setup object
        self.setup = setup

        # Packages to install
        self.setup.installList = []
        self.current_list = []
        
        # Initial status update
        self.updateStatus("Loading repos...")

    def doneButton_clicked(self):
        ''' Close the dialog window '''
        self.ui.done(0)

    def updateStatus(self, status):
        self.ui.loadingStatus.setText(status)
        while QtGui.qApp.hasPendingEvents():
            QtGui.qApp.processEvents()

    def list_installed_packages(self):
        self.excluded_packages = []
        self.updateStatus("Getting a list of installed packages...")
        output = subprocess.check_output(['pacman', '-Q']).splitlines()
        for x in output:
            x = x.split(" ")[0]
            self.excluded_packages.append(x)
        self.updateStatus("Good")


    def add_queueWidgetItem(self, row, pkg_name):
        self.ui.queueTableWidget.verticalHeader().setVisible(False)
        self.ui.queueTableWidget.sortItems(0, 0)
        self.ui.queueTableWidget.insertRow(row)

        # Checkbox
        chkBoxItem = QtGui.QTableWidgetItem()
        chkBoxItem.setData(35, QtCore.QVariant(row))
        chkBoxItem.setCheckState(QtCore.Qt.Checked)
        chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.ui.queueTableWidget.setItem(row, GUI_PACKAGE_CHECKBOX, chkBoxItem)

        # Queue item
        tableItem = QtGui.QTableWidgetItem(pkg_name)            
        self.ui.queueTableWidget.setItem(row, GUI_PACKAGE_NAME, tableItem)

        # Resize to contents after we got 20 items
        if (row == 20):
            self.ui.queueTableWidget.horizontalHeader().setStretchLastSection(False)
            self.ui.queueTableWidget.resizeColumnsToContents()
            self.ui.queueTableWidget.resizeRowsToContents()
            self.ui.queueTableWidget.horizontalHeader().setStretchLastSection(True)

    def add_packageWidgetItem(self, row, pkg_name, pkg_version, pkg_desc):
        self.current_list.append(pkg_name)
        self.ui.packageTableWidget.verticalHeader().setVisible(False)
        self.ui.packageTableWidget.sortItems(0, 0)
        self.ui.packageTableWidget.insertRow(row)
                
        isExcluded = False
        isQueued = False
        if pkg_name in self.excluded_packages:
            isExcluded = True
            
        if pkg_name in self.setup.installList:
            isQueued = True

        # Checkbox
        chkBoxItem = QtGui.QTableWidgetItem()
        chkBoxItem.setData(32, QtCore.QVariant(pkg_name))
        chkBoxItem.setData(33, QtCore.QVariant(pkg_version))
        chkBoxItem.setData(35, QtCore.QVariant(row))

        if isExcluded:
            chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable)
            chkBoxItem.setCheckState(QtCore.Qt.Checked)
        else:
            if isQueued:
                chkBoxItem.setCheckState(QtCore.Qt.Checked)
            else:
                chkBoxItem.setCheckState(QtCore.Qt.Unchecked)
            chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)

        self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_CHECKBOX, chkBoxItem)

        # package name
        tableItem = QtGui.QTableWidgetItem(pkg_name)            
        tableItem.setData(32, QtCore.QVariant(pkg_name))
        tableItem.setData(33, QtCore.QVariant(pkg_version))
        tableItem.setData(34, QtCore.QVariant(pkg_desc))
        self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_NAME, tableItem)

        # package version
        tableItem = QtGui.QTableWidgetItem(pkg_version)
        tableItem.setData(32, QtCore.QVariant(pkg_version))
        self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_VERSION, tableItem)

        # Resize to contents after we got 20 items
        if (row == 20):
            self.ui.packageTableWidget.horizontalHeader().setStretchLastSection(False)
            self.ui.packageTableWidget.resizeColumnsToContents()
            self.ui.packageTableWidget.resizeRowsToContents()
            self.ui.packageTableWidget.horizontalHeader().setStretchLastSection(True)
        self.updateStatus("Loading Package, %s %s" % (pkg_name, pkg_version))

    def footer_TableWidget(self, table):
        table.horizontalHeader().setStretchLastSection(False)
        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True);
        
    def repoListItem_clicked(self, item):
        ''' Build package list for selected repo '''
        self.ui.searchEdit.setText("")
        repo = str(item.data(32).toString())
        self.current_repo = repo

        row = -1
        # Clear the table
        self.ui.packageTableWidget.clearContents()
        self.ui.packageTableWidget.setRowCount(0)

        self.current_list[:] = []
        for package in self.packageList:
            if (package[PKG_REPO] == repo):
                row += 1
                pkg_desc = ""
                try:
                    pkg_desc = package[PKG_DESC]
                except:
                    pkg_desc = "No description available"

                self.add_packageWidgetItem(row,
                    package[PKG_NAME],
                    package[PKG_VERSION],
                    pkg_desc)

        self.footer_TableWidget(self.ui.packageTableWidget)
        self.updateStatus("%s has been successfully loaded!" % (repo))

    def update_repoListSearch(self, search):
        ''' Build package list for selected repo '''

        row = -1
        # Clear the table
        self.ui.packageTableWidget.clearContents()
        self.ui.packageTableWidget.setRowCount(0)

        self.current_list[:] = []
        for package in self.packageList:
            if (search in package[PKG_NAME]):
                row += 1
                pkg_desc = ""
                try:
                    pkg_desc = package[PKG_DESC]
                except:
                    pkg_desc = "No description available"

                self.add_packageWidgetItem(row,
                    package[PKG_NAME],
                    package[PKG_VERSION],
                    pkg_desc)

        self.footer_TableWidget(self.ui.packageTableWidget)

    def update_queue(self):
        row = -1
        self.ui.queueTableWidget.clearContents()
        self.ui.queueTableWidget.setRowCount(0)
        
        for x in self.setup.installList:
            row += 1
            self.add_queueWidgetItem(row, self.setup.installList[row])
                
        self.footer_TableWidget(self.ui.queueTableWidget)

    def packageTableWidgetItem_clicked(self, item):
        ''' Show package description '''
        description = ""
        pkg_name = str(item.data(32).toString())
        pkg_version = str(item.data(33).toString())
        pkg_desc = str(item.data(34).toString())
        
        if item.data(35).canConvert(QtCore.QVariant.Int):
            checked, ok = item.data(35).toInt()
            if (ok == False):
                checked = 0;
        else:
            checked = 0;
        
        if (checked > 0):
            if pkg_name in self.excluded_packages:
                description = "Can't uncheck this much needed system package"
            else:
                if pkg_name not in self.setup.installList:
                    self.setup.installList.append(pkg_name)
                    description = "<html><b>" + pkg_name + "</b> " + pkg_version + " selected</html>"
                    self.update_queue()
                else:
                    self.setup.installList.remove(pkg_name)
                    description = "<html><b>" + pkg_name + "</b> " + pkg_version + " removed</html>"
                    self.update_queue()
        else:
            description = "<html><b>" + pkg_name + " " + pkg_version + "</b>" + "<br><br>" + pkg_desc + "</html>"

        if (len(description) > 0):
            self.ui.packageDescEdit.setText(description)
        
    def queueTableWidgetItem_clicked(self, item):
        ''' Show package description '''
        if item.data(35).canConvert(QtCore.QVariant.Int):
            checked, ok = item.data(35).toInt()
            if (ok == False):
                checked = 0;
        else:
            checked = 0;
        
        if (checked > 0):
            pkg_name = self.setup.installList[int(checked)]
            self.setup.installList.remove(pkg_name)
            if pkg_name in self.current_list:
                pos = self.current_list.index(pkg_name)
                checkbox = self.ui.packageTableWidget.item(pos, GUI_PACKAGE_CHECKBOX)
                if checkbox is not None:
                    checkbox.setCheckState(QtCore.Qt.Unchecked)

            description = "<html><b>" + pkg_name + "</b> removed</html>"
            self.ui.packageDescEdit.setText(description)
            self.update_queue()
                
    def searchButton_clicked(self):
        ''' Search through all repo items '''
        search_object = self.ui.searchEdit.text()
        
        if (len(search_object) > 1):
            self.update_repoListSearch(search_object)
        else:
            self.updateStatus("Need at least 2 letters to search!")

    def clearButton_clicked(self):
        for x in self.setup.installList:
            if x in self.current_list:
                pos = self.current_list.index(x)
                checkbox = self.ui.packageTableWidget.item(pos, GUI_PACKAGE_CHECKBOX)
                if checkbox is not None:
                    checkbox.setCheckState(QtCore.Qt.Unchecked)
                    
        self.setup.installList[:] = []
        self.ui.queueTableWidget.clearContents()
        self.ui.queueTableWidget.setRowCount(0)

    def update_repo_list(self, repo_list):
        self.repoList = repo_list
        for repo in repo_list:
            item = QtGui.QListWidgetItem(repo)
            item.setData(32, QtCore.QVariant(QtCore.QString(repo)))
            self.ui.repoListWidget.addItem(item)

    def build_package_list(self, workerList, workerRepoList):
        ''' Parse package database '''
        self.packageList = workerList
        self.update_repo_list(workerRepoList)
        self.updateStatus("Good")

    def show(self):
        ''' Show the Dialog window '''
        self.ui.exec_()
