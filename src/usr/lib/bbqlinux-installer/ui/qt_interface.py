#!/usr/bin/env python
import sys
sys.path.append('/usr/lib/bbqlinux-installer')
sys.path.append('/usr/share/bbqlinux-installer')
import os
import commands
import GeoIP
import gettext
import pango
import parted
import string
import subprocess
import threading
import time
import traceback
import urllib
import urllib2
import xml.dom.minidom
from xml.dom.minidom import parse

from installer import InstallerEngine, Setup, PartitionSetup

from PyQt4 import QtGui, QtCore, uic
import qt_resources_rc

INDEX_PARTITION_PATH = 0
INDEX_PARTITION_SIZE = 1
INDEX_PARTITION_FREE_SPACE = 2
INDEX_PARTITION_DESCRIPTION = 3
INDEX_PARTITION_TYPE = 4
INDEX_PARTITION_FORMAT_AS = 5
INDEX_PARTITION_MOUNT_AS = 6

class InstallerWindow(QtGui.QMainWindow):

    PAGE_WELCOME = 0
    PAGE_LANGUAGE = 1
    PAGE_TIMEZONE = 2
    PAGE_KEYBOARD = 3
    PAGE_HARDDISK = 4
    PAGE_PARTITION = 5
    PAGE_ADVANCED = 6
    PAGE_USER = 7
    PAGE_SUMMARY = 8
    PAGE_INSTALL = 9
    PAGE_COMPLETE = 10

    resource_dir = '/usr/share/bbqlinux-installer/'

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
 
        self.ui = uic.loadUi('/usr/share/bbqlinux-installer/qt_interface.ui')
        self.ui.show()
        
        # Move main window to center
        qr = self.ui.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.ui.move(qr.topLeft())

        # Build the Setup object (where we put all our choices)
        self.setup = Setup()
        
        # Detect and set the bios type (bios, efi)
        self.detect_bios_type()
        
        # Installer engine
        self.installer = InstallerEngine(self.setup)
        self.connect(self.installer, QtCore.SIGNAL("progressUpdate(int, int, QString)"), self.update_progress)

        # Get the distribution name
        self.DISTRIBUTION_NAME = self.installer.get_distribution_name()
        
        # Set window title
        self.ui.setWindowTitle("%s Installer" % self.DISTRIBUTION_NAME)
        self.ui.headLabel.setText(unicode("Welcome to the %s installation" % self.DISTRIBUTION_NAME))
        
        # Connect the buttons
        self.connect(self.ui.exitButton, QtCore.SIGNAL("clicked()"), QtGui.qApp, QtCore.SLOT("quit()"))
        self.connect(self.ui.backButton, QtCore.SIGNAL("clicked()"), self.backButton_clicked)
        self.connect(self.ui.forwardButton, QtCore.SIGNAL("clicked()"), self.forwardButton_clicked)
        
        self.connect(self.ui.refreshPartitionButton, QtCore.SIGNAL("clicked()"), self.refreshPartitionButton_clicked)
        self.connect(self.ui.editPartitionButton, QtCore.SIGNAL("clicked()"), self.editPartitionButton_clicked)
        
        # Set welcome radio button checked
        self.setOverviewRadioButtons(self.PAGE_WELCOME)
        
        # Connect the language list
        self.connect(self.ui.languageListWidget, QtCore.SIGNAL("itemClicked(QListWidgetItem *)"), self.languageListItem_clicked)
        
        # Connect the timezone list
        self.connect(self.ui.timezoneListWidget, QtCore.SIGNAL("itemClicked(QListWidgetItem *)"), self.timezoneListItem_clicked)

        # Connect the keyboard tables
        self.connect(self.ui.keyboardModelComboBox, QtCore.SIGNAL("activated(int)"), self.keyboardModelComboBox_activated)
        self.connect(self.ui.keyboardLayoutTableWidget, QtCore.SIGNAL("itemClicked(QTableWidgetItem *)"), self.keyboardLayoutTableItem_clicked)
        self.connect(self.ui.keyboardVariantTableWidget, QtCore.SIGNAL("itemClicked(QTableWidgetItem *)"), self.keyboardVariantTableItem_clicked)
        
        # Connect the harddisk list
        self.connect(self.ui.harddiskListWidget, QtCore.SIGNAL("itemClicked(QListWidgetItem *)"), self.harddiskListItem_clicked)

        # Connect the bootloader combo boxes
        self.connect(self.ui.bootloaderTypeComboBox, QtCore.SIGNAL("activated(int)"), self.bootloaderTypeComboBox_activated)
        self.connect(self.ui.bootloaderDeviceComboBox, QtCore.SIGNAL("activated(int)"), self.bootloaderDeviceComboBox_activated)

    def backButton_clicked(self):
        ''' Jump one page back '''
        index = self.getCurrentPageIndex()
        self.setCurrentPageIndex(index - 1)
        
    def forwardButton_clicked(self):
        ''' Jump one page forward '''
        noError = True
        index = self.getCurrentPageIndex()

        if (index == self.PAGE_PARTITION):
            noError = self.verify_partitions()
        elif (index == self.PAGE_USER):
            noError = self.verify_user_settings()
        elif (index == self.PAGE_SUMMARY):
            noError = self.check_connectivity()

        if (noError == True):
            self.setCurrentPageIndex(index + 1)

    def refreshPartitionButton_clicked(self):
        ''' Refresh the partition view '''
        self.build_partitions()

    def editPartitionButton_clicked(self):
        ''' Edit the partitions '''
        if (self.setup.target_disk is None):
            os.popen("gparted &")
        else:
            os.popen("gparted %s &" % self.setup.target_disk)
    
    def partitionContextMenu(self, position):
        ''' Right-click partition menu '''
        tableItem = self.ui.partitionTableWidget.itemAt(position)
        if (not tableItem is None):
            row = tableItem.row()
            partitionPathItem = self.ui.partitionTableWidget.item(row, INDEX_PARTITION_PATH)
            partition_path = str(partitionPathItem.data(32).toString())
            filesystem = str(self.ui.partitionTableWidget.item(row, INDEX_PARTITION_TYPE).data(32).toString())
            mount_point = str(self.ui.partitionTableWidget.item(row, INDEX_PARTITION_MOUNT_AS).data(32).toString())
            format_as = str(self.ui.partitionTableWidget.item(row, INDEX_PARTITION_FORMAT_AS).data(32).toString())

            if ("/dev/" in partition_path):
                menu = QtGui.QMenu()

                if (filesystem == "swap"):
                    setSwap = menu.addAction("Assign to linux-swap")
                    action = menu.exec_(self.ui.partitionTableWidget.mapToGlobal(position))
                    if action == setSwap:
                        self.assign_mount_point(partitionPathItem, "swap", "swap")
                else:
                    setSwap = "undefined"
                    editAction = menu.addAction("Edit")
                    menu.addSeparator()
                    setRoot = menu.addAction("Assign to /")
                    setBoot = menu.addAction("Assign to /boot")
                    if (self.setup.bios_type is "efi"):
                        setEfi = menu.addAction("Assign to /boot/efi")
                    else:
                        setEfi = "undefined"
                    setHome = menu.addAction("Assign to /home")
                    setSrv = menu.addAction("Assign to /srv")
                    setUsr = menu.addAction("Assign to /usr")

                    action = menu.exec_(self.ui.partitionTableWidget.mapToGlobal(position))
                
                    if action == editAction:
                        dlg = PartitionEditDialog(self, partition_path, format_as, mount_point)
                        (mount_as, format_as) = dlg.show()
                        self.assign_mount_point(partitionPathItem, mount_as, format_as)
                    elif action == setRoot:
                        self.assign_mount_point(partitionPathItem, "/", "btrfs")
                    elif action == setBoot:
                        self.assign_mount_point(partitionPathItem, "/boot", "btrfs")
                    elif action == setEfi:
                        self.assign_mount_point(partitionPathItem, "/boot/efi", "vfat")
                    elif action == setHome:
                        self.assign_mount_point(partitionPathItem, "/home", "btrfs")
                    elif action == setSrv:
                        self.assign_mount_point(partitionPathItem, "/srv", "btrfs")
                    elif action == setUsr:
                        self.assign_mount_point(partitionPathItem, "/usr", "btrfs")

    def assign_mount_point(self, partitionPathItem, mount_point, filesystem):
        row = partitionPathItem.row()
        partition_path = str(partitionPathItem.data(32).toString())

        # Mountpoint
        item = self.ui.partitionTableWidget.item(row, INDEX_PARTITION_MOUNT_AS)
        item.setText(QtCore.QString(mount_point))
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setData(32, QtCore.QVariant(QtCore.QString(mount_point)))

        # Filesystem
        item = self.ui.partitionTableWidget.item(row, INDEX_PARTITION_FORMAT_AS)
        item.setText(QtCore.QString(filesystem))
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setData(32, QtCore.QVariant(QtCore.QString(filesystem)))
        
        for apartition in self.setup.partitions:
            if (apartition.partition.path == partition_path):
                apartition.mount_as = mount_point
                apartition.format_as = filesystem
            else:                
                if apartition.mount_as == mount_point:
                    apartition.mount_as = None
                    apartition.format_as = None
        self.setup.print_setup()

    def setOverviewRadioButtons(self, page):
        if (page <= self.PAGE_WELCOME):
            self.ui.welcomeRadioButton.setChecked(True)
            self.ui.welcomeRadioButton.setEnabled(True)
        else:
            self.ui.welcomeRadioButton.setChecked(False)
            self.ui.welcomeRadioButton.setEnabled(False)
        if (page is self.PAGE_LANGUAGE):
            self.ui.languageRadioButton.setChecked(True)
            self.ui.languageRadioButton.setEnabled(True)
        else:
            self.ui.languageRadioButton.setChecked(False)
            self.ui.languageRadioButton.setEnabled(False)
        if (page is self.PAGE_TIMEZONE):
            self.ui.timezoneRadioButton.setChecked(True)
            self.ui.timezoneRadioButton.setEnabled(True)
        else:
            self.ui.timezoneRadioButton.setChecked(False)
            self.ui.timezoneRadioButton.setEnabled(False)
        if (page is self.PAGE_KEYBOARD):
            self.ui.keyboardRadioButton.setChecked(True)
            self.ui.keyboardRadioButton.setEnabled(True)
        else:
            self.ui.keyboardRadioButton.setChecked(False)
            self.ui.keyboardRadioButton.setEnabled(False)
        if (page is self.PAGE_HARDDISK):
            self.ui.harddiskRadioButton.setChecked(True)
            self.ui.harddiskRadioButton.setEnabled(True)
        else:
            self.ui.harddiskRadioButton.setChecked(False)
            self.ui.harddiskRadioButton.setEnabled(False)
        if (page is self.PAGE_PARTITION):
            self.ui.partitionRadioButton.setChecked(True)
            self.ui.partitionRadioButton.setEnabled(True)
        else:
            self.ui.partitionRadioButton.setChecked(False)
            self.ui.partitionRadioButton.setEnabled(False)
        if (page is self.PAGE_ADVANCED):
            self.ui.advancedRadioButton.setChecked(True)
            self.ui.advancedRadioButton.setEnabled(True)
        else:
            self.ui.advancedRadioButton.setChecked(False)
            self.ui.advancedRadioButton.setEnabled(False)
        if (page is self.PAGE_USER):
            self.ui.userRadioButton.setChecked(True)
            self.ui.userRadioButton.setEnabled(True)
        else:
            self.ui.userRadioButton.setChecked(False)
            self.ui.userRadioButton.setEnabled(False)
        if (page is self.PAGE_SUMMARY):
            self.ui.summaryRadioButton.setChecked(True)
            self.ui.summaryRadioButton.setEnabled(True)
        else:
            self.ui.summaryRadioButton.setChecked(False)
            self.ui.summaryRadioButton.setEnabled(False)
        if (page is self.PAGE_INSTALL):
            self.ui.installRadioButton.setChecked(True)
            self.ui.installRadioButton.setEnabled(True)
        else:
            self.ui.installRadioButton.setChecked(False)
            self.ui.installRadioButton.setEnabled(False)
        if (page >= self.PAGE_COMPLETE):
            self.ui.completeRadioButton.setChecked(True)
            self.ui.completeRadioButton.setEnabled(True)
        else:
            self.ui.completeRadioButton.setChecked(False)
            self.ui.completeRadioButton.setEnabled(False)
    
    def languageListItem_clicked(self, item):
        ''' Get the clicked locale code '''
        locale_code = str(item.data(32).toString())
        country_code = str(item.data(33).toString())
        if(len(locale_code) < 1 or len(country_code) < 1):
            return

        self.setup.locale_code = locale_code
        self.setup.country_code = country_code
        self.setup.print_setup()
    
    def timezoneListItem_clicked(self, item):
        ''' Get the clicked timezone '''
        country_code = str(item.data(32).toString())
        timezone = str(item.data(33).toString())
        
        if(len(country_code) < 1 or len(timezone) < 1):
            return
        
        self.setup.timezone_code = country_code
        self.setup.timezone = timezone
        self.setup.print_setup()
    
    def keyboardModelComboBox_activated(self, index):
        ''' Get the clicked keyboard model '''
        if (index is None):
            return

        keyboard_model = str(self.ui.keyboardModelComboBox.itemData(index, 32).toString())
        keyboard_model_description = str(self.ui.keyboardModelComboBox.itemData(index, 33).toString())
        
        if(len(keyboard_model) < 1):
            return
        
        self.setup.keyboard_model = keyboard_model
        self.setup.keyboard_model_description = keyboard_model_description
        os.system("setxkbmap -model %s" % keyboard_model)
        self.setup.print_setup()
    
    def keyboardLayoutTableItem_clicked(self, item):
        ''' Get the clicked keyboard layout item '''
        keyboard_layout = str(item.data(32).toString())
        keyboard_layout_description = str(item.data(33).toString())

        if(len(keyboard_layout) < 1):
            return

        print "keyboard_layout: %s" % keyboard_layout
        print "keyboard_layout_description: %s" % keyboard_layout_description

        self.setup.keyboard_layout = keyboard_layout
        self.setup.keyboard_layout_description = keyboard_layout_description
        os.system("setxkbmap -layout %s" % keyboard_layout)
        self.build_keyboard_variant_list()
        self.setup.print_setup()

    def keyboardVariantTableItem_clicked(self, item):
        ''' Get the clicked keyboard variant item '''
        keyboard_variant = str(item.data(32).toString())
        keyboard_variant_description = str(item.data(33).toString())

        if(len(keyboard_variant) < 1):
            return

        self.setup.keyboard_variant = keyboard_variant
        self.setup.keyboard_variant_description = keyboard_variant_description
        os.system("setxkbmap -variant %s" % keyboard_variant)
        self.setup.print_setup()

    def harddiskListItem_clicked(self, item):
        ''' Get the clicked harddisk '''
        harddisk = str(item.data(32).toString())
        
        if(len(harddisk) < 6):
            return

        self.setup.target_disk = harddisk
        self.setup.print_setup()

    def bootloaderTypeComboBox_activated(self, index):
        ''' Get the clicked bootloader type '''
        if (index is None):
            return

        bootloader_type = str(self.ui.bootloaderTypeComboBox.itemData(index, 32).toString())
        
        if(len(bootloader_type) < 1):
            return
        
        self.setup.bootloader_type = bootloader_type
        self.setup.print_setup()

    def bootloaderDeviceComboBox_activated(self, index):
        ''' Get the clicked bootloader device '''
        if (index is None):
            return

        bootloader_device = str(self.ui.bootloaderDeviceComboBox.itemData(index, 32).toString())
        
        if(len(bootloader_device) < 1):
            return
        
        self.setup.bootloader_device = bootloader_device
        self.setup.print_setup()

    def getCurrentPageIndex(self):
        ''' Get the current page index '''
        return self.ui.pageStack.currentIndex()
    
    def setCurrentPageIndex(self, index):
        ''' Jump to a page index '''
        if index != self.getCurrentPageIndex():
            self.ui.pageStack.setCurrentIndex(index)
            if (index <= self.PAGE_WELCOME):
                index = self.PAGE_WELCOME
                self.ui.headLabel.setText(unicode("Welcome to the %s installation" % self.DISTRIBUTION_NAME))
            elif (index is self.PAGE_LANGUAGE):
                self.ui.headLabel.setText(unicode("Choose your language"))
                self.build_language_list()
            elif (index is self.PAGE_TIMEZONE):
                self.ui.headLabel.setText(unicode("Choose your timezone"))
                self.build_timezone_list()
            elif (index is self.PAGE_KEYBOARD):
                self.ui.headLabel.setText(unicode("Choose your keyboard layout"))
                self.build_keyboard_lists()
            elif (index is self.PAGE_HARDDISK):
                self.ui.headLabel.setText(unicode("Select Harddisk"))
                self.build_harddisks()
            elif (index is self.PAGE_PARTITION):
                self.ui.headLabel.setText(unicode("Partition your harddisk"))
                self.build_partitions()
                self.build_bootloader_partitions()
            elif (index is self.PAGE_ADVANCED):
                self.ui.headLabel.setText(unicode("Advanced Settings"))
                self.build_bootloader_list()                
            elif (index is self.PAGE_USER):
                self.ui.headLabel.setText(unicode("Create your user account"))

                # Username validator
                rx = QtCore.QRegExp(QtCore.QString("^[a-z][a-z0-9]*$"))
                self.usernameValidator = QtGui.QRegExpValidator(rx)
                self.ui.usernameLineEdit.setValidator(self.usernameValidator)

                # Hostname validator
                rx = QtCore.QRegExp(QtCore.QString("^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$"))
                self.hostnameValidator = QtGui.QRegExpValidator(rx)
                self.ui.hostnameLineEdit.setValidator(self.hostnameValidator)

            elif (index is self.PAGE_SUMMARY):
                self.ui.headLabel.setText(unicode("Summary"))

                summaryText = "Locale: %s\r\n" % self.setup.locale_code
                summaryText += "Country: %s\r\n" % self.setup.country_code
                summaryText += "Timezone: %s (%s)\r\n" % (self.setup.timezone, self.setup.timezone_code)        
                summaryText += "Keyboard: %s - %s (%s) - %s - %s (%s)\r\n" % (self.setup.keyboard_model, self.setup.keyboard_layout, self.setup.keyboard_variant, self.setup.keyboard_model_description, self.setup.keyboard_layout_description, self.setup.keyboard_variant_description)        
                summaryText += "Username: %s (%s)\r\n" % (self.setup.username, self.setup.real_name)
                summaryText += "Hostname: %s\r\n" % self.setup.hostname
                summaryText += "Bios Type: %s\r\n" % self.setup.bios_type
                summaryText += "Bootloader: %s\r\n" % self.setup.bootloader_type
                summaryText += "Bootloader device: %s\r\n" % self.setup.bootloader_device
                summaryText += "Target disk: %s\r\n" % self.setup.target_disk                      
                summaryText += "Partitions:\r\n"
                summaryText += "----------------------------------------\r\n"
                for partition in self.setup.partitions:
                    summaryText += "Device: %s, format as: %s, mount as: %s\r\n" % (partition.partition.path, partition.format_as, partition.mount_as)              
                
                self.ui.summaryTextEdit.setText(summaryText)
                
                if (self.check_connectivity() == True):
                    self.ui.connectivityIcon.setPixmap(QtGui.QPixmap("/usr/share/bbqlinux-installer/icons/actions/dialog-ok-3.png"))
                else:
                    self.ui.connectivityIcon.setPixmap(QtGui.QPixmap("/usr/share/bbqlinux-installer/icons/actions/dialog-no-2.png"))
            elif (index is self.PAGE_INSTALL):
                self.ui.headLabel.setText(unicode("Installation"))
                self.ui.forwardButton.setEnabled(False)
                # Start the install process
                self.installer.start()
            elif (index >= self.PAGE_COMPLETE):
                index = self.PAGE_COMPLETE
                self.ui.headLabel.setText(unicode("Finished!"))

            # Set overview radio buttons checked and unchecked
            self.setOverviewRadioButtons(index)

    def getText(self, nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

    def detect_bios_type(self):
        if(os.path.exists("/sys/firmware/efi/vars")):
            bios_type = 'efi'
        else:
            bios_type = 'bios'
        
        self.setup.bios_type = bios_type
        self.setup.print_setup()
        return bios_type  

    def build_language_list(self):

        # Try to find out where we're located...
        cur_country_code = None
        try:
            whatismyip = 'http://debian.linuxmint.com/installer/show_my_ip.php'
            ip = urllib.urlopen(whatismyip).readlines()[0]
            gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
            cur_country_code = gi.country_code_by_addr(ip)
        except:
            pass # best effort, we get here if we're not connected to the Internet            

        # Plan B... find out what locale we're in (i.e. USA on the live session)
        cur_lang = os.environ['LANG']
        if("." in cur_lang):
            cur_lang = cur_lang.split(".")[0]

        # Load countries into memory
        countries = {}
        file = open(os.path.join(self.resource_dir, 'countries'), "r")
        for line in file:
            line = line.strip()
            split = line.split("=")
            if len(split) == 2:
                countries[split[0]] = split[1]
        file.close()

        # Load languages into memory
        languages = {}
        file = open(os.path.join(self.resource_dir, 'languages'), "r")
        for line in file:
            line = line.strip()
            split = line.split("=")
            if len(split) == 2:
                languages[split[0]] = split[1]
        file.close()

        path = os.path.join(self.resource_dir, 'locales')
        locales = open(path, "r")
        set_item = None
        # Clear the list
        self.ui.languageListWidget.clear()
        for line in locales:
            if "UTF-8" in line:
                locale_code = line.replace("UTF-8", "")
                locale_code = locale_code.replace(".", "")
                locale_code = locale_code.strip()
                if "_" in locale_code:
                    split = locale_code.split("_")
                    if len(split) == 2:
                        language_code = split[0]
                        if language_code in languages:
                            language = languages[language_code]
                        else:
                            language = language_code

                        country_code = split[1].lower()
                        if country_code in countries:
                            country = countries[country_code]
                        else:
                            country = country_code

                        language_label = "%s (%s)" % (language, country)

                        flag_path = self.resource_dir + '/flags/16/' + country_code + '.png'
                        if not os.path.exists(flag_path):
                            flag_path = self.resource_dir + '/flags/16/generic.png'                         

                        flag_icon = QtGui.QIcon(flag_path)

                        # Append to list
                        item = QtGui.QListWidgetItem(flag_icon, language_label)
                        item.setData(32, QtCore.QVariant(QtCore.QString(locale_code)))
                        item.setData(33, QtCore.QVariant(QtCore.QString(country_code)))
                        self.ui.languageListWidget.addItem(item)

                        # If it's matching our country code, that's our language right there.. 
                        if ((cur_country_code is not None) and (cur_country_code.lower() == country_code)):
                            if (set_item is None):
                                set_item = item
                                self.setup.locale_code = locale_code
                                self.setup.country_code = country_code
                            else:
                                # If we find more than one language for a particular country, one of them being English, go for English by default.
                                if (language_code == "en"):
                                    set_item = item
                                    self.setup.locale_code = locale_code
                                    self.setup.country_code = country_code
                                # Guesswork... handy for countries which have their own language (fr_FR, de_DE, es_ES.. etc. )
                                elif (country_code == language_code):
                                    set_item = item
                                    self.setup.locale_code = locale_code
                                    self.setup.country_code = country_code
                                    
                        # as a plan B... use the locale (USA)
                        if((set_item is None) and (locale_code == cur_lang)):
                            set_item = item
                            self.setup.locale_code = locale_code
                            self.setup.country_code = country_code

        # Select users current language
        self.ui.languageListWidget.setCurrentItem(set_item)

    def build_timezone_list(self):
        path = os.path.join(self.resource_dir, 'timezones')
        timezones = open(path, "r")
        set_item = None
        # Clear the list
        self.ui.timezoneListWidget.clear()
        for line in timezones:
            content = line.strip().split()
            if len(content) == 2:
                country_code = content[0]
                timezone = content[1]

            item = QtGui.QListWidgetItem(timezone)
            item.setData(32, QtCore.QVariant(QtCore.QString(country_code)))
            item.setData(33, QtCore.QVariant(QtCore.QString(timezone)))
            self.ui.timezoneListWidget.addItem(item)
            
            # If user selected country matches timezone, choose it by default
            if (country_code.lower() == self.setup.country_code):
                set_item = item
                self.setup.timezone_code = country_code
                self.setup.timezone = timezone

        if (not set_item is None):
            self.ui.timezoneListWidget.setCurrentItem(set_item)

    def build_keyboard_lists(self):
        ''' Do some xml kung-fu and load the keyboard stuffs '''

        # firstly we'll determine the layouts in use
        p = subprocess.Popen("setxkbmap -print",shell=True,stdout=subprocess.PIPE)
        for line in p.stdout:
            # strip it
            line = line.rstrip("\r\n")
            line = line.replace("{","")
            line = line.replace("}","")
            line = line.replace(";","")
            if("xkb_symbols" in line):
                # decipher the layout in use
                section = line.split("\"")[1] # split by the " mark
                layout = section.split("+")[1]
                if "(" in layout:
                    self.setup.keyboard_layout = layout.split("(")[0]
                else:
                    self.setup.keyboard_layout = layout
            if("xkb_geometry" in line):
                first_bracket = line.index("(") +1
                substr = line[first_bracket:]
                last_bracket = substr.index(")")
                substr = substr[0:last_bracket]
                keyboard_geom = substr
        p.poll()

        xml_file = '/usr/share/X11/xkb/rules/xorg.xml'     
        dom = parse(xml_file)

        # grab the root element
        root = dom.getElementsByTagName('xkbConfigRegistry')[0]
        # build the list of models
        root_models = root.getElementsByTagName('modelList')[0]
        # Clear the combo box
        self.ui.keyboardModelComboBox.clear()
        cur_index = -1
        set_index = None
        for element in root_models.getElementsByTagName('model'):
            cur_index += 1
            conf = element.getElementsByTagName('configItem')[0]
            name = conf.getElementsByTagName('name')[0]
            desc = conf.getElementsByTagName('description')[0]

            self.ui.keyboardModelComboBox.addItem(QtCore.QString(self.getText(desc.childNodes)))
            self.ui.keyboardModelComboBox.setItemData(cur_index, QtCore.QVariant(QtCore.QString(self.getText(name.childNodes))), 32)
            self.ui.keyboardModelComboBox.setItemData(cur_index, QtCore.QVariant(QtCore.QString(self.getText(desc.childNodes))), 33)
            
            item = self.getText(name.childNodes)
            if(item == keyboard_geom):
                set_index = cur_index
                self.setup.keyboard_model = self.getText(name.childNodes)
                self.setup.keyboard_model_description = self.getText(desc.childNodes)
                
        # If we found the current model, select it
        if (not set_index is None):
            self.ui.keyboardModelComboBox.setCurrentIndex(set_index)

        root_layouts = root.getElementsByTagName('layoutList')[0]
        row = -1
        set_item = None
        # Clear the table
        self.ui.keyboardLayoutTableWidget.clearContents()
        self.ui.keyboardLayoutTableWidget.setRowCount(0)
        for element in root_layouts.getElementsByTagName('layout'):
            row += 1
            conf = element.getElementsByTagName('configItem')[0]
            name = conf.getElementsByTagName('name')[0]
            desc = conf.getElementsByTagName('description')[0]
            self.ui.keyboardLayoutTableWidget.verticalHeader().setVisible(False)
            self.ui.keyboardLayoutTableWidget.sortItems(0, 0)
            self.ui.keyboardLayoutTableWidget.insertRow(row)
            tableItem = QtGui.QTableWidgetItem(QtCore.QString(self.getText(desc.childNodes)))            
            tableItem.setData(32, QtCore.QVariant(QtCore.QString(self.getText(name.childNodes))))
            tableItem.setData(33, QtCore.QVariant(QtCore.QString(self.getText(desc.childNodes))))
            self.ui.keyboardLayoutTableWidget.setItem(row, 0, tableItem)
            item = self.getText(name.childNodes)
            if(item == self.setup.keyboard_layout):
                set_item = tableItem
                self.setup.keyboard_layout_description = self.getText(desc.childNodes)

        if (not set_item is None):
            self.ui.keyboardLayoutTableWidget.scrollToItem(set_item, QtGui.QAbstractItemView.PositionAtCenter)
            set_item.setSelected(True)
            # Since the first scrollToItem doesn't work, do it again
            self.ui.keyboardLayoutTableWidget.scrollToItem(set_item, QtGui.QAbstractItemView.PositionAtCenter)

        self.build_keyboard_variant_list()

    def build_keyboard_variant_list(self):
        # firstly we'll determine the layouts in use
        p = subprocess.Popen("setxkbmap -print",shell=True,stdout=subprocess.PIPE)
        for line in p.stdout:
            # strip it
            line = line.rstrip("\r\n")
            line = line.replace("{","")
            line = line.replace("}","")
            line = line.replace(";","")
            if("xkb_symbols" in line):
                # decipher the layout in use
                section = line.split("\"")[1] # split by the " mark
                layout = section.split("+")[1]
                if "(" in layout:
                    self.setup.keyboard_layout = layout.split("(")[0]
                else:
                    self.setup.keyboard_layout = layout
        p.poll()

        xml_file = '/usr/share/X11/xkb/rules/xorg.xml'            
        dom = parse(xml_file)
        
        # grab the root element
        root = dom.getElementsByTagName('xkbConfigRegistry')[0]
        # build the list of variants       
        root_layouts = root.getElementsByTagName('layoutList')[0]
        row = -1
        # Clear the table
        self.ui.keyboardVariantTableWidget.clearContents()
        self.ui.keyboardVariantTableWidget.setRowCount(0)
        self.ui.keyboardVariantTableWidget.verticalHeader().setVisible(False)
        self.ui.keyboardVariantTableWidget.sortItems(0, 0)
        for layout in root_layouts.getElementsByTagName('layout'):
            conf = layout.getElementsByTagName('configItem')[0]
            layout_name = self.getText(conf.getElementsByTagName('name')[0].childNodes)            
            layout_description = self.getText(conf.getElementsByTagName('description')[0].childNodes)            
            if (layout_name == self.setup.keyboard_layout):
                row += 1           
                self.ui.keyboardVariantTableWidget.insertRow(row)
                tableItem = QtGui.QTableWidgetItem(QtCore.QString(layout_description))
                tableItem.setData(32, QtCore.QVariant(QtCore.QString("")))
                tableItem.setData(33, QtCore.QVariant(QtCore.QString(layout_description)))
                self.ui.keyboardVariantTableWidget.setItem(row, 0, tableItem)
                tableItem.setSelected(True)

                self.setup.keyboard_variant = ""
                self.setup.keyboard_variant_description = layout_description

                variants_list = layout.getElementsByTagName('variantList')
                if len(variants_list) > 0:
                    root_variants = layout.getElementsByTagName('variantList')[0]   
                    for variant in root_variants.getElementsByTagName('variant'):
                        row += 1                
                        variant_conf = variant.getElementsByTagName('configItem')[0]
                        variant_name = self.getText(variant_conf.getElementsByTagName('name')[0].childNodes)
                        variant_description = "%s - %s" % (layout_description, self.getText(variant_conf.getElementsByTagName('description')[0].childNodes))

                        self.ui.keyboardVariantTableWidget.insertRow(row)
                        tableItem = QtGui.QTableWidgetItem(QtCore.QString(variant_description))
                        tableItem.setData(32, QtCore.QVariant(QtCore.QString(variant_name)))
                        tableItem.setData(33, QtCore.QVariant(QtCore.QString(variant_description)))
                        self.ui.keyboardVariantTableWidget.setItem(row, 0, tableItem)
                break

    def build_harddisks(self):
        self.setup.disks = []          
        inxi = subprocess.Popen("inxi -c0 -D", shell=True, stdout=subprocess.PIPE)
        set_item = None
        # Clear the list
        self.ui.harddiskListWidget.clear()
        for line in inxi.stdout:
            line = line.rstrip("\r\n")
            if(line.startswith("Drives:")):
                line = line.replace("Drives:", "")
            if "model:" in line: 
                line = line.replace("model:", "")
            if "size:" in line: 
                line = line.replace("size:", "")
            sections = line.split(":")
            for section in sections:
                section = section.strip()
                if("/dev/" in section):                    
                    elements = section.split()
                    for element in elements:
                        if "/dev/" in element: 
                            description = elements[+1]
                            size = elements[+2]
                            self.setup.disks.append(element)
                            item = QtGui.QListWidgetItem("%s (%s, %s)" % (element, size, description))
                            item.setData(32, QtCore.QVariant(QtCore.QString(element)))
                            self.ui.harddiskListWidget.addItem(item)
                            if (set_item is None):
                                self.setup.target_disk = element
                                set_item = item

        if(len(self.setup.disks) > 0):
            if (not set_item is None):
                self.ui.harddiskListWidget.setCurrentItem(set_item)

    def getMaxFreeSpaceRegion(self, disk):
        ''' get the biggest free space region ... '''
        regions = disk.getFreeSpaceRegions()
        free_max = regions[0]
        for _range in regions:
            if (_range.getSize() > free_max.getSize()):
                free_max = _range
        print "Max free space region %d-%d (%dMB)" % (free_max.start, free_max.end, free_max.getSize())
        return free_max

    def getBestFreeSpaceRegion(self, disk, req_size):
        regions = disk.getFreeSpaceRegions()
        free_qualified = []
        for _range in regions:
            if (_range.getSize() >= req_size):
                free_qualified.append(_range)

        if len(free_qualified) > 0:
            best_free = free_qualified[0]
            for _range in free_qualified:
                if (_range.getSize() < best_free.getSize()):
                    best_free = _range

            print "Best free space region %d-%d (%dMB)" % (best_free.start, best_free.end, best_free.getSize())
            return best_free
        else:
            print "There's no suitable free space region"
            return None

    def build_partitions(self):           
        os.popen('mkdir -p /tmp/bbqlinux-installer/tmpmount')
        
        try:                                                                                            
            self.setup.partitions = []
            html_partitions = ""                    
            swap_found = False
            
            if self.setup.target_disk is not None:
                path = self.setup.target_disk # i.e. /dev/sda
                device = parted.getDevice(path)                
                try:
                    disk = parted.Disk(device)
                except Exception:
                    dialog = QuestionDialog("BBQLinux Installer", "No partition table was found on the hard drive. Do you want the installer to create a set of partitions for you? Note: This will erase any data present on the disk.")
                    if (dialog.show()):
                        # Create a default partition set up
                        if(self.setup.bios_type is 'efi'):
                            # EFI
                            disk = parted.freshDisk(device, 'gpt')
                            disk.commit()

                            # /boot/efi
                            regions = disk.getFreeSpaceRegions()
                            if len(regions) > 0:
                                region = regions[-1]
                                post_mbr_gap = parted.sizeToSectors(2, "MiB", device.sectorSize) # Grub2 requires a post-MBR gap
                                start = post_mbr_gap
                                num_sectors = parted.sizeToSectors(131072, "KiB", device.sectorSize) # 128MB
                                end = start + num_sectors
                                cylinder = device.endSectorToCylinder(end)
                                end = device.endCylinderToSector(cylinder)
                                geometry = parted.Geometry(device=device, start=start, end=end)
                                if end < region.length:
                                    partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, geometry=geometry)
                                    constraint = parted.Constraint(exactGeom=geometry)
                                    disk.addPartition(partition=partition, constraint=constraint)
                                    disk.commit()
                                    os.system("mkfs.vfat -F32 -n \"EFI System Partition\" %s" % partition.path)

                            # /boot
                            regions = disk.getFreeSpaceRegions()
                            if len(regions) > 0:
                                region = regions[-1]
                                start = end + 1
                                num_sectors = parted.sizeToSectors(262144, "KiB", device.sectorSize) # 256MB
                                end = start + num_sectors
                                cylinder = device.endSectorToCylinder(end)
                                end = device.endCylinderToSector(cylinder)
                                geometry = parted.Geometry(device=device, start=start, end=end)
                                if end < region.length:
                                    partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, geometry=geometry)
                                    constraint = parted.Constraint(exactGeom=geometry)
                                    disk.addPartition(partition=partition, constraint=constraint)
                                    disk.commit()
                                    os.system("mkfs.ext4 -L boot %s" % partition.path)

                        else:
                            # BIOS
                            disk = parted.freshDisk(device, 'msdos')
                            disk.commit()

                            # /boot
                            regions = disk.getFreeSpaceRegions()
                            if len(regions) > 0:
                                region = regions[-1]    
                                post_mbr_gap = parted.sizeToSectors(1, "MiB", device.sectorSize) # Grub2 requires a post-MBR gap
                                start = post_mbr_gap
                                num_sectors = parted.sizeToSectors(262144, "KiB", device.sectorSize) # 256MB
                                end = start + num_sectors
                                cylinder = device.endSectorToCylinder(end)
                                end = device.endCylinderToSector(cylinder)
                                geometry = parted.Geometry(device=device, start=start, end=end)
                                if end < region.length:
                                    partition = parted.Partition(disk=disk, type=parted.PARTITION_BOOT, geometry=geometry)
                                    constraint = parted.Constraint(exactGeom=geometry)
                                    disk.addPartition(partition=partition, constraint=constraint)
                                    disk.commit()
                                    os.system("mkfs.ext4 -L boot %s" % partition.path) 

                        # Swap
                        regions = disk.getFreeSpaceRegions()
                        if len(regions) > 0:
                            region = regions[-1]  
                            start = end + 1
                            ram_size = int(commands.getoutput("cat /proc/meminfo | grep MemTotal | awk {'print $2'}")) # in KiB
                            if(ram_size > 2097152):
                                ram_size = 2097152
                            num_sectors = parted.sizeToSectors(ram_size, "KiB", device.sectorSize)
                            num_sectors = int(float(num_sectors) * 1.5) # Swap is 1.5 times bigger than RAM but never bigger than 3GB
                            end = start + num_sectors
                            cylinder = device.endSectorToCylinder(end)
                            end = device.endCylinderToSector(cylinder)
                            geometry = parted.Geometry(device=device, start=start, end=end)
                            if end < region.length:
                                partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, geometry=geometry)
                                constraint = parted.Constraint(exactGeom=geometry)
                                disk.addPartition(partition=partition, constraint=constraint)
                                disk.commit()
                                os.system("mkswap %s" % partition.path)                                

                        # Min size for the root partition
                        PARTITION_ROOT_SIZE = 8192
                        partition_root_size = PARTITION_ROOT_SIZE
                        # Min size for creating a home partition
                        PARTITION_HOME_SIZE = 1024
                        partition_home_size = PARTITION_HOME_SIZE
                        
                        create_home_partition = True
                        region = self.getMaxFreeSpaceRegion(disk=disk)

                        # Calculate root partition size based on free space (ugly)
                        if (region.getSize() < PARTITION_ROOT_SIZE):
                            MessageDialog("Installation Tool", "There's not enough space left for the root partition.").show()
                            raise
                        elif (region.getSize() <= (PARTITION_ROOT_SIZE + PARTITION_HOME_SIZE)):
                            # if there's not enough space to create root and home with it's minimum sizes,
                            # don't create home and extend root to max available size
                            create_home_partition = False
                            partition_root_size = region.getSize()
                        elif (region.getSize() >= (PARTITION_ROOT_SIZE * 2) and region.getSize() < (PARTITION_ROOT_SIZE * 4)):
                            partition_root_size = 10240
                        elif (region.getSize() >= (PARTITION_ROOT_SIZE * 4) and region.getSize() < (PARTITION_ROOT_SIZE * 6)):
                            partition_root_size = 16384
                        elif (region.getSize() >= (PARTITION_ROOT_SIZE * 6) and region.getSize() < (PARTITION_ROOT_SIZE * 8)):
                            partition_root_size = 24576
                        elif (region.getSize() >= (PARTITION_ROOT_SIZE * 8)):
                            partition_root_size = 32768

                        # Root
                        region = self.getBestFreeSpaceRegion(disk=disk, req_size=partition_root_size)
                        if not region is None:
                            end = region.start + parted.sizeToSectors(partition_root_size, "MiB", device.sectorSize)
                            geometry = parted.Geometry(device=device, start=region.start, end=end)
                            if end < region.length:
                                partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, geometry=geometry)
                                constraint = parted.Constraint(exactGeom=geometry)
                                disk.addPartition(partition=partition, constraint=constraint)
                                disk.commit()
                                os.system("mkfs.ext4 -L root %s" % partition.path)

                        # /home
                        if (create_home_partition == True):
                            region = self.getBestFreeSpaceRegion(disk=disk, req_size=partition_home_size)
                            if not region is None:
                                geometry = parted.Geometry(device=device, start=region.start, end=region.end)
                                partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, geometry=region)
                                constraint = parted.Constraint(exactGeom=region)
                                disk.addPartition(partition=partition, constraint=constraint)
                                disk.commit()                            
                                os.system("mkfs.ext4 -L home %s" % partition.path)
                       
                        self.build_partitions()
                        return
                    else:
                        # Do nothing... just get out of here..
                        print "No partition table created!"
                        raise
                partition = disk.getFirstPartition()
                last_added_partition = PartitionSetup(partition)
                partition = partition.nextPartition()
                html_partitions = html_partitions + "<table width='100%'><tr>"
                row = -1
                # Clear the table
                self.ui.partitionTableWidget.clearContents()
                self.ui.partitionTableWidget.setRowCount(0)
                if (not self.partitionContextMenu is True):
                    self.ui.partitionTableWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                    self.ui.partitionTableWidget.customContextMenuRequested.connect(self.partitionContextMenu)
                    self.partitionContextMenu = True
                while (partition is not None):
                    if last_added_partition.partition.number == -1 and partition.number == -1:
                        last_added_partition.add_partition(partition)
                    else:                        
                        last_added_partition = PartitionSetup(partition)
                                        
                        if "swap" in last_added_partition.type:
                            last_added_partition.type = "swap"                                                            

                        if partition.number != -1 and "swap" not in last_added_partition.type and partition.type != parted.PARTITION_EXTENDED:
                            # Umount temp folder
                            if ('/tmp/bbqlinux-installer/tmpmount' in commands.getoutput('mount')):
                                os.popen('umount /tmp/bbqlinux-installer/tmpmount')

                            # Mount partition if not mounted
                            if (partition.path not in commands.getoutput('mount')):                                
                                os.system("mount %s /tmp/bbqlinux-installer/tmpmount" % partition.path)

                            # Identify partition's description and used space
                            if (partition.path in commands.getoutput('mount')):
                                df_lines = commands.getoutput("df 2>/dev/null | grep %s" % partition.path).split('\n')
                                for df_line in df_lines:
                                    df_elements = df_line.split()
                                    if df_elements[0] == partition.path:
                                        last_added_partition.used_space = df_elements[4]  
                                        mount_point = df_elements[5]                              
                                        if "%" in last_added_partition.used_space:
                                            used_space_pct = int(last_added_partition.used_space.replace("%", "").strip())
                                            last_added_partition.free_space = int(float(last_added_partition.size) * (float(100) - float(used_space_pct)) / float(100))
                                                                            
                                        if os.path.exists(os.path.join(mount_point, 'etc/lsb-release')):
                                            last_added_partition.description = commands.getoutput("cat " + os.path.join(mount_point, 'etc/lsb-release') + " | grep DISTRIB_DESCRIPTION").replace('DISTRIB_DESCRIPTION', '').replace('=', '').replace('"', '').strip()                                    
                                        if os.path.exists(os.path.join(mount_point, 'etc/issue')):
                                            last_added_partition.description = commands.getoutput("cat " + os.path.join(mount_point, 'etc/issue')).replace('\\n', '').replace('\l', '').strip()                                    
                                        if os.path.exists(os.path.join(mount_point, 'Windows/servicing/Version')):
                                            version = commands.getoutput("ls %s" % os.path.join(mount_point, 'Windows/servicing/Version'))                                    
                                            if version.startswith("6.1"):
                                                last_added_partition.description = "Windows 7"
                                            elif version.startswith("6.0"):
                                                last_added_partition.description = "Windows Vista"
                                            elif version.startswith("5.1") or version.startswith("5.2"):
                                                last_added_partition.description = "Windows XP"
                                            elif version.startswith("5.0"):
                                                last_added_partition.description = "Windows 2000"
                                            elif version.startswith("4.90"):
                                                last_added_partition.description = "Windows Me"
                                            elif version.startswith("4.1"):
                                                last_added_partition.description = "Windows 98"
                                            elif version.startswith("4.0.1381"):
                                                last_added_partition.description = "Windows NT"
                                            elif version.startswith("4.0.950"):
                                                last_added_partition.description = "Windows 95"
                                        elif os.path.exists(os.path.join(mount_point, 'Boot/BCD')):
                                            if os.system("grep -qs \"V.i.s.t.a\" " + os.path.join(mount_point, 'Boot/BCD')) == 0:
                                                last_added_partition.description = "Windows Vista bootloader"
                                            elif os.system("grep -qs \"W.i.n.d.o.w.s. .7\" " + os.path.join(mount_point, 'Boot/BCD')) == 0:
                                                last_added_partition.description = "Windows 7 bootloader"
                                            elif os.system("grep -qs \"W.i.n.d.o.w.s. .R.e.c.o.v.e.r.y. .E.n.v.i.r.o.n.m.e.n.t\" " + os.path.join(mount_point, 'Boot/BCD')) == 0:
                                                last_added_partition.description = "Windows recovery"
                                            elif os.system("grep -qs \"W.i.n.d.o.w.s. .S.e.r.v.e.r. .2.0.0.8\" " + os.path.join(mount_point, 'Boot/BCD')) == 0:
                                                last_added_partition.description = "Windows Server 2008 bootloader"
                                            else:
                                                last_added_partition.description = "Windows bootloader"
                                        elif os.path.exists(os.path.join(mount_point, 'Windows/System32')):
                                            last_added_partition.description = "Windows"
                                        break
                            else:
                                print "Failed to mount %s" % partition.path

                            # Umount temp folder
                            if ('/tmp/bbqlinux-installer/tmpmount' in commands.getoutput('mount')):
                                os.popen('umount /tmp/bbqlinux-installer/tmpmount')
                                
                    if last_added_partition.size > 1.0:
                        if last_added_partition.partition.type == parted.PARTITION_LOGICAL:
                            display_name = "  " + last_added_partition.name
                        else:
                            display_name = last_added_partition.name

                        row += 1
                        self.ui.partitionTableWidget.verticalHeader().setVisible(False)
                        self.ui.partitionTableWidget.sortItems(0, 0)
                        self.ui.partitionTableWidget.insertRow(row)

                        # Display name
                        tableItem = QtGui.QTableWidgetItem(QtCore.QString(display_name))
                        tableItem.setData(32, QtCore.QVariant(QtCore.QString(display_name)))
                        self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_PATH, tableItem)

                        # Size
                        if (last_added_partition.size >= 1024):
                            size = "%.2f GB" % round(last_added_partition.size / 1024, 2)
                        else:
                            size = "%.0f MB" % round(last_added_partition.size, 0)

                        tableItem = QtGui.QTableWidgetItem(QtCore.QString(size))
                        tableItem.setTextAlignment(QtCore.Qt.AlignRight)
                        self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_SIZE, tableItem)      

                        # Free space
                        if isinstance(last_added_partition.free_space, int) or isinstance(last_added_partition.free_space, float):
                            last_added_partition.free_space = float(last_added_partition.free_space)
                            if (last_added_partition.free_space >= 1024):
                                free = "%.2f GB" % round(last_added_partition.free_space / 1024, 2)
                            else:
                                free = "%.0f MB" % round(last_added_partition.free_space, 0)
                        
                            tableItem = QtGui.QTableWidgetItem(QtCore.QString(free))
                            tableItem.setTextAlignment(QtCore.Qt.AlignRight)
                            self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_FREE_SPACE, tableItem)

                        # Type
                        if last_added_partition.partition.number == -1:                     
                            tableItem = QtGui.QTableWidgetItem(QtCore.QString(last_added_partition.type))
                            tableItem.setTextAlignment(QtCore.Qt.AlignCenter)
                            tableItem.setData(32, QtCore.QVariant(QtCore.QString(last_added_partition.type)))
                            self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_TYPE, tableItem)                          
                        elif last_added_partition.partition.type == parted.PARTITION_EXTENDED:                    
                            tableItem = QtGui.QTableWidgetItem(QtCore.QString("Extended"))
                            tableItem.setTextAlignment(QtCore.Qt.AlignCenter)
                            tableItem.setData(32, QtCore.QVariant(QtCore.QString("Extended")))
                            self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_TYPE, tableItem)                          
                        else:                                        
                            if last_added_partition.type == "ntfs":
                                color = "#42e5ac"
                            elif last_added_partition.type == "fat32":
                                color = "#18d918"
                            elif last_added_partition.type == "ext4":
                                color = "#4b6983"
                            elif last_added_partition.type == "ext3":
                                color = "#7590ae"
                            elif last_added_partition.type in ["linux-swap", "swap"]:
                                color = "#c1665a"
                                last_added_partition.mount_as = "swap"
                                tableItem = QtGui.QTableWidgetItem(QtCore.QString("swap"))
                                tableItem.setTextAlignment(QtCore.Qt.AlignCenter)
                                tableItem.setData(32, QtCore.QVariant(QtCore.QString("swap")))
                                self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_MOUNT_AS, tableItem)
                            else:
                                color = "#a9a9a9"

                            tableItem = QtGui.QTableWidgetItem(QtCore.QString(last_added_partition.type))
                            tableItem.setTextAlignment(QtCore.Qt.AlignCenter)
                            tableItem.setTextColor(QtGui.QColor(color))
                            tableItem.setData(32, QtCore.QVariant(QtCore.QString(last_added_partition.type)))
                            self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_TYPE, tableItem)   

                        # Format as
                        tableItem = QtGui.QTableWidgetItem(QtCore.QString("--"))
                        tableItem.setTextAlignment(QtCore.Qt.AlignCenter)
                        self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_FORMAT_AS, tableItem)

                        # Operating system
                        tableItem = QtGui.QTableWidgetItem(QtCore.QString(last_added_partition.description))
                        self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_DESCRIPTION, tableItem)

                        # Mountpoint
                        if last_added_partition.type in ["linux-swap", "swap"]:
                            tableItem = QtGui.QTableWidgetItem(QtCore.QString("swap"))
                        else:
                            tableItem = QtGui.QTableWidgetItem(QtCore.QString("--"))
                            tableItem.setTextAlignment(QtCore.Qt.AlignCenter)
                            self.ui.partitionTableWidget.setItem(row, INDEX_PARTITION_MOUNT_AS, tableItem)

                        # Resize table headers
                        self.ui.partitionTableWidget.resizeColumnsToContents()
                        self.ui.partitionTableWidget.horizontalHeader().setStretchLastSection(True)

                        self.setup.partitions.append(last_added_partition)
                        last_added_partition.print_partition()

                    partition = partition.nextPartition()

        except Exception:
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60

    def verify_partitions(self):
        # check for /boot/efi on efi systems
            if(self.setup.bios_type == 'efi'):
                error_efi = True
                errorMessage = "Please select a efi (/boot/efi) system partition before proceeding"
                for partition in self.setup.partitions:
                    if(partition.mount_as == '/boot/efi'):
                        error_efi = False                  
                        if(partition.format_as != "fat32" and partition.format_as != "vfat"):
                            error_efi = True
                            errorMessage = "Please indicate a vfat filesystem to format the efi (/boot/efi) system partition before proceeding"
                        break
                    else:
                        error_efi = True
                        errorMessage = "Please select a efi (/boot/efi) system partition before proceeding"
                if(error_efi):
                    MessageDialog("Partitioning error", errorMessage).show()
            else:
                error_efi = False

            error_root = True
            errorMessage = "Please indicate a filesystem to format the root (/) partition before proceeding"
            for partition in self.setup.partitions:
                if(partition.mount_as == "/"):
                    error_root = False
                    if partition.format_as is None or partition.format_as == "":
                        error_root = True
                        errorMessage = "Please indicate a filesystem to format the root (/) partition before proceeding"
                    break
                else:
                    error_root = True
                    errorMessage = "Please select a root (/) partition before proceeding"
            if(error_root):
                MessageDialog("Partitioning error", errorMessage).show()

            if(error_efi == False and error_root == False):
                return True
            else:
                return False

    def build_bootloader_list(self):
        self.ui.bootloaderTypeComboBox.clear()
        cur_index = -1
        if (self.setup.bios_type == "efi"):
            bootloader_type = "grub-efi-x86_64"
        else:
            bootloader_type = "grub-bios"
        cur_index += 1
        self.ui.bootloaderTypeComboBox.addItem(QtCore.QString(bootloader_type))
        self.ui.bootloaderTypeComboBox.setItemData(cur_index, QtCore.QVariant(QtCore.QString(bootloader_type)), 32)
        self.setup.bootloader_type = bootloader_type
        self.setup.print_setup()
        
    def build_bootloader_partitions(self):
        self.ui.bootloaderDeviceComboBox.clear()
        cur_index = -1
        set_index = None
        if (self.setup.bios_type == "efi"):
            cur_index += 1
            self.ui.bootloaderDeviceComboBox.addItem(QtCore.QString("/boot/efi"))
            self.ui.bootloaderDeviceComboBox.setItemData(cur_index, QtCore.QVariant(QtCore.QString("/boot/efi")), 32)
            self.setup.bootloader_device = "/boot/efi"
        else:
            # Add disks
            for disk in self.setup.disks:
                cur_index += 1
                self.ui.bootloaderDeviceComboBox.addItem(QtCore.QString(disk))
                self.ui.bootloaderDeviceComboBox.setItemData(cur_index, QtCore.QVariant(QtCore.QString(disk)), 32)
                if (disk == self.setup.target_disk):
                    set_index = cur_index
                    self.setup.bootloader_device = disk
            # Add partitions
            partitions = commands.getoutput("fdisk -l | grep ^/dev/").split("\n")
            for partition in partitions:
                try:
                    partition = partition.split()[0].strip()
                    if partition.startswith("/dev/"):
                        cur_index += 1
                        self.ui.bootloaderDeviceComboBox.addItem(QtCore.QString(partition))
                        self.ui.bootloaderDeviceComboBox.setItemData(cur_index, QtCore.QVariant(QtCore.QString(partition)), 32)
                except Exception, detail:
                    print detail
            # If we found the target disk, select it
            if (not set_index is None):
                self.ui.bootloaderDeviceComboBox.setCurrentIndex(set_index)
        self.setup.print_setup()

    def verify_user_settings(self):
        pos = 0

        realname_error = True
        realname = str(self.ui.realnameLineEdit.text())
        if (len(realname) < 1):
            realname_error = True
            self.ui.realnameLineEdit.setStyleSheet("border: 1px solid red")
            MessageDialog("Realname error", "Please enter a valid realname").show()
        else:
            realname_error = False
            self.ui.realnameLineEdit.setStyleSheet("border: 1px solid green")

        username_error = True
        username = str(self.ui.usernameLineEdit.text())
        if (self.usernameValidator.validate(QtCore.QString(username), pos) != (QtGui.QValidator.Acceptable, pos) or len(username) < 1):
            username_error = True
            self.ui.usernameLineEdit.setStyleSheet("border: 1px solid red");
            MessageDialog("Username error", "Please enter a valid username").show()
        else:
            username_error = False
            self.ui.usernameLineEdit.setStyleSheet("border: 1px solid green")

        password1_error = True
        password1 = str(self.ui.passwordLineEdit1.text())
        if (len(password1) < 1):
            password1_error = True
            self.ui.passwordLineEdit1.setStyleSheet("border: 1px solid red")
            MessageDialog("Password error", "Please enter a valid password").show()
        else:
            password1_error = False
            self.ui.passwordLineEdit1.setStyleSheet("border: 1px solid green")

        password2_error = True
        password2 = str(self.ui.passwordLineEdit2.text())
        if (password2 != password1):
            password2_error = True
            self.ui.passwordLineEdit2.setStyleSheet("border: 1px solid red")
            MessageDialog("Password error", "Passwords do not match").show()
        else:
            password2_error = False
            self.ui.passwordLineEdit2.setStyleSheet("border: 1px solid green")

        hostname_error = True
        hostname = str(self.ui.hostnameLineEdit.text())
        if (self.hostnameValidator.validate(QtCore.QString(hostname), pos) != (QtGui.QValidator.Acceptable, pos) or len(hostname) < 1):
            hostname_error = True
            self.ui.hostnameLineEdit.setStyleSheet("border: 1px solid red")
            MessageDialog("Hostname error", "Please enter a valid hostname").show()
        else:
            hostname_error = False
            self.ui.hostnameLineEdit.setStyleSheet("border: 1px solid green")
        
        if (realname_error == False and username_error == False and password1_error == False and password2_error == False and hostname_error == False):
            self.setup.real_name = realname
            self.setup.username = username
            self.setup.password1 = password1
            self.setup.password2 = password2
            self.setup.hostname = hostname
            self.setup.print_setup()
            return True
        else:
            return False

    def check_connectivity(self):
        # check for internet connectivity
        try:
            con = urllib2.urlopen("http://www.bbqlinux.org")
            data = con.read()
            return True
        except:
            try:
                con = urllib2.urlopen("http://www.archlinux.org")
                data = con.read()
                return True
            except:
                return False

    def update_progress(self, total=0, current=0, message=QtCore.QString("")):
        self.ui.installProgressBar.setMaximum(total)
        self.ui.installProgressBar.setValue(current)
        self.ui.installFootLabel.setText(message)

class QuestionDialog(object):
    def __init__(self, title, message):
        self.title = QtCore.QString(title)
        self.message = QtCore.QString(message)

    ''' Show me on screen '''
    def show(self):
        reply = QtGui.QMessageBox(self.title, self.message, 4, QtGui.QMessageBox.Yes, QtGui.QMessageBox.NoButton, QtGui.QMessageBox.No)

        if reply.exec_() == QtGui.QMessageBox.Yes:
            return True
        else:
            return False

class MessageDialog(object):
    def __init__(self, title, message):
        self.title = QtCore.QString(title)
        self.message = QtCore.QString(message)

    ''' Show me on screen '''
    def show(self):
        messageBox = QtGui.QMessageBox(self.title, self.message, 4, QtGui.QMessageBox.NoButton, QtGui.QMessageBox.Ok, QtGui.QMessageBox.NoButton)
        messageBox.exec_()

class PartitionEditDialog(object):
    def __init__(self, base, partition_path, format_as, mount_point):       
        self.partitionEditBox = uic.loadUi('/usr/share/bbqlinux-installer/qt_partition_edit_dialog.ui')
        self.partitionEditBox.partitionLabel.setText(QtCore.QString(partition_path))

        # Mountpoint
        if (len(mount_point) > 0):
            self.partitionEditBox.mountpointLineEdit.setText(QtCore.QString(mount_point))

        # Check if real linux path
        rx = QtCore.QRegExp(QtCore.QString("^/{1}(((/{1}\.{1})?[a-zA-Z0-9 ]+/?)+(\.{1}[a-zA-Z0-9]{2,4})?)$"))
        self.validator = QtGui.QRegExpValidator(rx)
        self.partitionEditBox.mountpointLineEdit.setValidator(self.validator)

        # Format as
        cur_index = -1
        set_index = None
        ''' Build supported filesystems list '''
        if "swap" in format_as:        
            self.partitionEditBox.filesystemComboBox.addItem(QtCore.QString("swap"))
            self.partitionEditBox.filesystemComboBox.setItemData(0, QtCore.QVariant(QtCore.QString("swap")), 32)
        else:
            try:
                for item in os.listdir("/sbin"):
                    if(item.startswith("mkfs.")):
                        cur_index += 1
                        fstype = item.split(".")[1]
                        self.partitionEditBox.filesystemComboBox.addItem(QtCore.QString(fstype))
                        self.partitionEditBox.filesystemComboBox.setItemData(cur_index, QtCore.QVariant(QtCore.QString(fstype)), 32)
                        if(format_as == fstype):
                            set_index = cur_index
            except Exception:
                print '-'*60
                traceback.print_exc(file=sys.stdout)
                print '-'*60
                print "Could not build supported filesystems list!"
        
        # If we've found the current fstype, select it
        if (not set_index is None):
            self.partitionEditBox.filesystemComboBox.setCurrentIndex(set_index)
        
        # Connect the buttons
        QtCore.QObject.connect(self.partitionEditBox.cancelPushButton, QtCore.SIGNAL("clicked()"), self.cancelButton_clicked)        
        QtCore.QObject.connect(self.partitionEditBox.okPushButton, QtCore.SIGNAL("clicked()"), self.okButton_clicked)

        # ok button is pressed on enter key
        self.partitionEditBox.okPushButton.setDefault(True)
        self.partitionEditBox.okPushButton.setAutoDefault(True)

    def show(self):
        # Execute the dialog window
        self.partitionEditBox.exec_()
        return (self.mount_as, self.format_as)

    def cancelButton_clicked(self):
        self.partitionEditBox.done(1)
        
    def okButton_clicked(self):
        # Mount as
        mount_as = str(self.partitionEditBox.mountpointLineEdit.text())
        
        # Format as
        index = self.partitionEditBox.filesystemComboBox.currentIndex()
        format_as = str(self.partitionEditBox.filesystemComboBox.itemData(index, 32).toString())

        if (len(mount_as) > 0 and len(format_as) > 0):
            pos = 0
            if (self.validator.validate(QtCore.QString(mount_as), pos) == (QtGui.QValidator.Acceptable, pos)):
                self.mount_as = mount_as
                self.format_as = format_as
                self.partitionEditBox.done(0)
            else:
                # Draw mount_as red if not a valid linux path
                pal = QtGui.QPalette()
                pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#FF0000"))
                self.partitionEditBox.mountpointLineEdit.setPalette(pal)
