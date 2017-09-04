#!/bin/env python
"""
Script to configure the VFATs on a GEM chamber
By: Cameron Bravo c.bravo@cern.ch
Modified by: Eklavya Sarkar eklavya.sarkar@cern.ch
             Brian Dorney brian.l.dorney@cern.ch
"""

from array import array
from gempython.tools.vfat_user_functions_uhal import *
from mapping.chamberInfo import chamber_vfatDACSettings
from qcoptions import parser
from qcutilities import readBackCheck 

parser.add_option("--chConfig", type="string", dest="chConfig", default=None,
                  help="Specify file containing channel settings from anaUltraSCurve", metavar="chConfig")
parser.add_option("--filename", type="string", dest="filename", default=None,
                  help="Specify file containing settings information", metavar="filename")
parser.add_option("--run", action="store_true", dest="run",
                  help="Set VFATs to run mode", metavar="run")
parser.add_option("--verify", action="store_true", dest="verify",
                  help="Performs a readback of registers and compares stored values with written values", metavar="verify")
parser.add_option("--vfatConfig", type="string", dest="vfatConfig", default=None,
                  help="Specify file containing VFAT settings from anaUltraThreshold", metavar="vfatConfig")
parser.add_option("--vt1", type="int", dest="vt1",
                  help="VThreshold1 DAC value for all VFATs", metavar="vt1", default=100)
parser.add_option("--vt1bump", type="int", dest="vt1bump",
                  help="VThreshold1 DAC bump value for all VFATs", metavar="vt1bump", default=0)
#parser.add_option("-w","--write",action="store_true", dest="write",
#                  help="Write the current settings to a file", metavar="write")

(options, args) = parser.parse_args()

if options.debug:
    uhal.setLogLevelTo( uhal.LogLevel.DEBUG )
else:
    uhal.setLogLevelTo( uhal.LogLevel.ERROR )

import ROOT as r
import subprocess,datetime
startTime = datetime.datetime.now().strftime("%Y.%m.%d.%H.%M")
print startTime
Date = startTime

ohboard = getOHObject(options.slot,options.gtx,options.shelf)
print 'opened connection'

if options.gtx in chamber_vfatDACSettings.keys():
    print "Configuring VFATs with chamber_vfatDACSettings dictionary values"
    parameters.defaultValues["IPreampIn"] = chamber_vfatDACSettings[options.gtx]["IPreampIn"]
    parameters.defaultValues["IPreampFeed"] = chamber_vfatDACSettings[options.gtx]["IPreampFeed"]
    parameters.defaultValues["IPreampOut"] = chamber_vfatDACSettings[options.gtx]["IPreampOut"]
    parameters.defaultValues["IShaper"] = chamber_vfatDACSettings[options.gtx]["IShaper"]
    parameters.defaultValues["IShaperFeed"] = chamber_vfatDACSettings[options.gtx]["IShaperFeed"]
    parameters.defaultValues["IComp"] = chamber_vfatDACSettings[options.gtx]["IComp"]

biasAllVFATs(ohboard,options.gtx,0x0,enable=False)
print 'biased VFATs'
writeAllVFATs(ohboard, options.gtx, "VThreshold1", options.vt1, 0)
print 'Set VThreshold1 to %i'%options.vt1

if options.run:
    writeAllVFATs(ohboard, options.gtx, "ContReg0",    0x37,        0)
    print 'VFATs set to run mode'
else:
    writeAllVFATs(ohboard, options.gtx, "ContReg0",    0x36,        0)

if options.filename:
    try:
        print 'Configuring Trims with %s'%options.filename
        inF = r.TFile(options.filename)

        for event in inF.scurveFitTree :
            writeVFAT(ohboard,options.gtx,int(event.vfatN),"VFATChannels.ChanReg%d"%(int(event.vfatCH)),int(event.trimDAC)+32*int(event.mask))
            writeVFAT(ohboard, options.gtx, int(event.vfatN), "ContReg3", int(event.trimRange),0)
        
        if options.verify:
            chTree = inF.Get("scurveFitTree")
            dict_readBack = { "trimDAC":"VFATChannels.ChanReg", "mask":"VFATChannels.ChanReg" }
            readBackCheck(chTree, dict_readBack, ohboard, options.gtx)

    except Exception as e:
        print '%s does not seem to exist'%options.filename
        print e

if options.chConfig:
    try:
        print 'Configuring Channels with %s'%options.chConfig
        chTree = r.TTree('chTree','Tree holding Channel Configuration Parameters')
        chTree.ReadFile(options.chConfig)

        for event in chTree :
            writeVFAT(ohboard,options.gtx,int(event.vfatN),"VFATChannels.ChanReg%d"%(int(event.vfatCH)),int(event.trimDAC)+32*int(event.mask))
        
        if options.verify:
            dict_readBack = { "trimDAC":"VFATChannels.ChanReg", "mask":"VFATChannels.ChanReg" }
            readBackCheck(chTree, dict_readBack, ohboard, options.gtx)

    except Exception as e:
        print '%s does not seem to exist'%options.filename
        print e

if options.vfatConfig:
    try:
        print 'Configuring VFATs with %s'%options.vfatConfig
        vfatTree = r.TTree('vfatTree','Tree holding VFAT Configuration Parameters')
        vfatTree.ReadFile(options.vfatConfig)

        for event in vfatTree :
            print 'Set link %d VFAT%d VThreshold1 to %i'%(options.gtx,event.vfatN,event.vt1+options.vt1bump)
            writeVFAT(ohboard, options.gtx, int(event.vfatN), "VThreshold1", int(event.vt1+options.vt1bump),0)
            writeVFAT(ohboard, options.gtx, int(event.vfatN), "ContReg3", int(event.trimRange),0)

        if options.verify:
            if options.vt1bump != 0:
                print "Mismatches between write & readback valus for VThreshold1 should be exactly %i" %(options.vt1bump)
            dict_readBack = { "vt1":"VThreshold1", "trimRange":"ContReg3" }
            readBackCheck(vfatTree, dict_readBack, ohboard, options.gtx)

    except Exception as e:
        print '%s does not seem to exist'%options.filename
        print e
        
print 'Chamber Configured'
