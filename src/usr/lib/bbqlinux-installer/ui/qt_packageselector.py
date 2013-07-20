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
GUI_PACKAGE_STATUS = 1
GUI_PACKAGE_NAME = 2
GUI_PACKAGE_VERSION = 3

class PackageSelector(object):

    resource_dir = '/usr/share/bbqlinux-installer/'
    repo_db_dir = '/var/lib/pacman/sync/'

    def __init__(self, setup):
        self.ui = uic.loadUi('/usr/share/bbqlinux-installer/qt_package_selector.ui')
        
        # Connect the buttons
        QtCore.QObject.connect(self.ui.doneButton, QtCore.SIGNAL("clicked()"), QtGui.qApp, QtCore.SLOT("quit()"))
        QtCore.QObject.connect(self.ui.addButton, QtCore.SIGNAL("clicked()"), self.addButton_clicked)
        QtCore.QObject.connect(self.ui.removeButton, QtCore.SIGNAL("clicked()"), self.removeButton_clicked)

        # Connect the repo list
        QtCore.QObject.connect(self.ui.repoListWidget, QtCore.SIGNAL("itemClicked(QListWidgetItem *)"), self.repoListItem_clicked)

        # Connect the package table
        QtCore.QObject.connect(self.ui.packageTableWidget, QtCore.SIGNAL("itemClicked(QTableWidgetItem *)"), self.packageTableWidgetItem_clicked)

        # Build the list of available repos
        self.build_repo_list()
        
        # Get a list of installed packages
        self.list_installed_packages()

        # Setup object
        self.setup = setup

        # Packages to install
        self.setup.installList = []
        
    def updateStatus(self, status):
        self.ui.loadingStatus.setText("Status: "+status)
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
        
    def updateExcludedRow(self, row):
        statusIconPath = self.resource_dir + '/icons/actions/dialog-warning-3.png'
        statusIcon = QtGui.QIcon(statusIconPath)
        statusItem = QtGui.QTableWidgetItem(statusIcon, QtCore.QString(""))
        self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_STATUS, statusItem)

    def build_repo_list(self):
        self.repoList = []

        dirList=os.listdir(self.repo_db_dir)
        for fname in dirList:
            # Remove file extension
            repo = fname[:-3]
            self.repoList.append(repo)
            item = QtGui.QListWidgetItem(repo)
            item.setData(32, QtCore.QVariant(QtCore.QString(repo)))
            self.ui.repoListWidget.addItem(item)

        self.ui.repoListWidget.sortItems(QtCore.Qt.AscendingOrder)
        self.updateStatus("Completed parsing repo lists")
        print "Available repos: %s" % self.repoList

    def repoListItem_clicked(self, item):
        ''' Build package list for selected repo '''
        repo = str(item.data(32).toString())
        self.updateStatus("Loading repo, "+repo)

        packageList = self.build_package_list()

        row = -1
        # Clear the table
        self.ui.packageTableWidget.clearContents()
        self.ui.packageTableWidget.setRowCount(0)

        for package in packageList:
            if (package[PKG_REPO] == repo):
                row += 1
                self.ui.packageTableWidget.verticalHeader().setVisible(False)
                self.ui.packageTableWidget.sortItems(0, 0)
                self.ui.packageTableWidget.insertRow(row)
                
                isExcluded = False
                if package[PKG_NAME] in self.excluded_packages:
                   isExcluded = True

                # Checkbox
                chkBoxItem = QtGui.QTableWidgetItem()
                if isExcluded:
                    chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable)
                    self.updateExcludedRow(row)
                else:
                    chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
				    
                chkBoxItem.setCheckState(QtCore.Qt.Unchecked)
                chkBoxItem.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)  
                self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_CHECKBOX, chkBoxItem)

                # package name
                tableItem = QtGui.QTableWidgetItem(QtCore.QString(package[PKG_NAME]))            
                tableItem.setData(32, QtCore.QVariant(QtCore.QString(package[PKG_NAME])))
                tableItem.setData(33, QtCore.QVariant(QtCore.QString(package[PKG_VERSION])))
                tableItem.setData(34, QtCore.QVariant(QtCore.QString(package[PKG_DESC])))
                self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_NAME, tableItem)

                # package version
                tableItem = QtGui.QTableWidgetItem(QtCore.QString(package[PKG_VERSION]))
                tableItem.setData(32, QtCore.QVariant(QtCore.QString(package[PKG_VERSION])))
                self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_VERSION, tableItem)

                # if the package is part of the install list, mark it
                if (package[PKG_NAME] in self.setup.installList):
                    statusIconPath = self.resource_dir + '/icons/actions/software-update-available-2.png'
                    statusIcon = QtGui.QIcon(statusIconPath)
                    statusItem = QtGui.QTableWidgetItem(statusIcon, QtCore.QString(""))
                    self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_STATUS, statusItem)

                # Resize to contents after we got 20 items
                if (row == 20):
                    self.ui.packageTableWidget.horizontalHeader().setStretchLastSection(False)
                    self.ui.packageTableWidget.resizeColumnsToContents()
                    self.ui.packageTableWidget.resizeRowsToContents()
                    self.ui.packageTableWidget.horizontalHeader().setStretchLastSection(True)

                self.updateStatus("Loading Package, %s %s" % (package[PKG_NAME], package[PKG_VERSION]))

        self.ui.packageTableWidget.horizontalHeader().setStretchLastSection(False)
        self.ui.packageTableWidget.resizeColumnsToContents()
        self.ui.packageTableWidget.resizeRowsToContents()
        self.ui.packageTableWidget.horizontalHeader().setStretchLastSection(True)
        self.updateStatus("%s has been successfully loaded!" % (repo))

    def packageTableWidgetItem_clicked(self, item):
        ''' Show package description '''
        pkg_name = item.data(32).toString()
        pkg_version = item.data(33).toString()
        pkg_desc = item.data(34).toString()

        description = "<html><b>" + pkg_name + " " + pkg_version + "</b>" + "<br><br>" + pkg_desc + "</html>"
        self.ui.packageDescEdit.setText(description)

    def addButton_clicked(self):
        ''' Add selected packages to our install list '''
        rows = self.ui.packageTableWidget.rowCount()

        for row in range(rows):
            chkBoxItem = self.ui.packageTableWidget.item(row, GUI_PACKAGE_CHECKBOX)
            if (chkBoxItem.checkState() == QtCore.Qt.Checked):
                pkgItem = self.ui.packageTableWidget.item(row, GUI_PACKAGE_NAME)
                pkgName = str(pkgItem.data(32).toString())

                statusIconPath = self.resource_dir + '/icons/actions/software-update-available-2.png'
                statusIcon = QtGui.QIcon(statusIconPath)
                statusItem = QtGui.QTableWidgetItem(statusIcon, QtCore.QString(""))
                self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_STATUS, statusItem)

                if (not pkgName in self.setup.installList):
                    print "Adding: %s " % (pkgName)
                    self.updateStatus("Adding package, "+pkgName)
                    self.setup.installList.append(pkgName)
                    self.updateStatus("%s has been added!, " % (pkgName))
                    print self.setup.installList
                
                chkBoxItem.setCheckState(QtCore.Qt.Unchecked)

    def removeButton_clicked(self):
        ''' Remove selected packages from our install list '''
        rows = self.ui.packageTableWidget.rowCount()

        for row in range(rows):
            chkBoxItem = self.ui.packageTableWidget.item(row, GUI_PACKAGE_CHECKBOX)
            if (chkBoxItem.checkState() == QtCore.Qt.Checked):
                pkgItem = self.ui.packageTableWidget.item(row, GUI_PACKAGE_NAME)
                pkgName = str(pkgItem.data(32).toString())

                if (pkgName in self.setup.installList):
                    statusItem = QtGui.QTableWidgetItem(QtCore.QString(""))
                    self.ui.packageTableWidget.setItem(row, GUI_PACKAGE_STATUS, statusItem)
                    
                    print "Removing: %s " % (pkgName)
                    self.updateStatus("Removing package, "+pkgName)
                    self.setup.installList.remove(pkgName)
                    self.updateStatus("%s has been removed!, " % (pkgName))
                    print self.setup.installList

                chkBoxItem.setCheckState(QtCore.Qt.Unchecked)

    def build_package_list(self):
        ''' Parse package database '''
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

        return packageList

    def show(self):
        ''' Show the Dialog window '''
        self.ui.exec_()
