import os
import subprocess
from subprocess import Popen
import time
import shutil
import gettext
import stat
import commands
import sys
import parted
from configobj import ConfigObj

class InstallerEngine:
    print "InstallerEngine init"

class Setup(object):
    locale_code = None
    country_code = None
    timezone = None
    timezone_code = None
    keyboard_model = None    
    keyboard_layout = None    
    keyboard_variant = None    
    partitions = [] # Array of PartitionSetup objects
    username = None
    hostname = None
    password1 = None
    password2 = None
    real_name = None
    bios_type = 'bios'
    bootloader_type = None
    bootloader_device = None
    disks = []
    target_disk = None
    
    # Descriptions (used by the summary screen)    
    keyboard_model_description = None
    keyboard_layout_description = None
    keyboard_variant_description = None
    
    def print_setup(self):
        if "--debug" in sys.argv:  
            print "-------------------------------------------------------------------------"
            print "locale: %s" % self.locale_code
            print "country: %s" % self.country_code
            print "timezone: %s (%s)" % (self.timezone, self.timezone_code)        
            print "keyboard: %s - %s (%s) - %s - %s (%s)" % (self.keyboard_model, self.keyboard_layout, self.keyboard_variant, self.keyboard_model_description, self.keyboard_layout_description, self.keyboard_variant_description)        
            print "user: %s (%s)" % (self.username, self.real_name)
            print "hostname: %s " % self.hostname
            print "passwords: %s - %s" % (self.password1, self.password2)
            print "bios_type: %s" % self.bios_type
            print "bootloader_type: %s " % self.bootloader_type
            print "bootloader_device: %s " % self.bootloader_device
            print "target_disk: %s " % self.target_disk
            print "disks: %s " % self.disks                       
            print "partitions:"
            for partition in self.partitions:
                partition.print_partition()
            print "-------------------------------------------------------------------------"

class PartitionSetup(object):
    name = ""    
    type = ""
    format_as = None
    mount_as = None    
    partition = None
    aggregatedPartitions = []

    def __init__(self, partition):
        self.partition = partition
        self.size = partition.getSize()
        self.start = partition.geometry.start
        self.end = partition.geometry.end
        self.description = ""
        self.used_space = ""
        self.free_space = ""

        if partition.number != -1:
            self.name = partition.path            
            if partition.fileSystem is None:
                # no filesystem, check flags
                if partition.type == parted.PARTITION_SWAP:
                    self.type = ("Linux swap")
                elif partition.type == parted.PARTITION_RAID:
                    self.type = ("RAID")
                elif partition.type == parted.PARTITION_LVM:
                    self.type = ("Linux LVM")
                elif partition.type == parted.PARTITION_HPSERVICE:
                    self.type = ("HP Service")
                elif partition.type == parted.PARTITION_PALO:
                    self.type = ("PALO")
                elif partition.type == parted.PARTITION_PREP:
                    self.type = ("PReP")
                elif partition.type == parted.PARTITION_MSFT_RESERVED:
                    self.type = ("MSFT Reserved")
                elif partition.type == parted.PARTITION_EXTENDED:
                    self.type = ("Extended Partition")
                elif partition.type == parted.PARTITION_LOGICAL:
                    self.type = ("Logical Partition")
                elif partition.type == parted.PARTITION_FREESPACE:
                    self.type = ("Free Space")
                else:
                    self.type =("Unknown")
            else:
                self.type = partition.fileSystem.type
        else:
            self.type = ""
            self.name = "unallocated"

    def add_partition(self, partition):
        self.aggregatedPartitions.append(partition)
        self.size = self.size + partition.getSize()
        self.end = partition.geometry.end
    
    def print_partition(self):
        print "Device: %s, format as: %s, mount as: %s" % (self.partition.path, self.format_as, self.mount_as)
