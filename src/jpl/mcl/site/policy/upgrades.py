# encoding: utf-8

u'''MCL — custom upgrade steps.'''

import plone.api
from Products.CMFCore.utils import getToolByName
from plone.dexterity.utils import createContentInContainer
import socket

# There has to be a better way of doing this:
if socket.gethostname() == 'tumor.jpl.nasa.gov' or socket.gethostname().endswith('.local'):
    _rdfBaseURL = u'https://edrn-dev.jpl.nasa.gov/ksdb/publishrdf/?rdftype='
else:
    _rdfBaseURL = u'https://mcl.jpl.nasa.gov/ksdb/publishrdf/?rdftype='

def nullUpgradeStep(context):
    u'''Null upgrade step does nothing for when no custom behavior is needed.'''
    pass

def _getPortal(context):
    return getToolByName(context, 'portal_url').getPortalObject()

def installJPLMCLSiteKnowledge(context):
    u'''Install jpl.mcl.site.knowledge.'''
    qi = plone.api.portal.get_tool('portal_quickinstaller')
    qi.installProduct('jpl.mcl.site.knowledge')
    

def installJPLMCLSiteSciencedata(context):
    u'''Install jpl.mcl.site.sciencedata.'''
    qi = plone.api.portal.get_tool('portal_quickinstaller')
    qi.installProduct('jpl.mcl.site.sciencedata')
