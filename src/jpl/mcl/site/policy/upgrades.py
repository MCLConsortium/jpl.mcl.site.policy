# encoding: utf-8

u'''MCL — custom upgrade steps.'''

import plone.api
from Products.CMFCore.utils import getToolByName
from plone.dexterity.utils import createContentInContainer
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from Products.CMFPlone.interfaces import INavigationSchema

import socket

# There has to be a better way of doing this:
if socket.gethostname() == 'tumor.jpl.nasa.gov' or socket.gethostname().endswith('.local'):
    _rdfBaseURL = u'https://edrn-dev.jpl.nasa.gov/ksdb/publishrdf/?rdftype='
else:
    _rdfBaseURL = u'https://mcl.jpl.nasa.gov/ksdb/publishrdf/?rdftype='

def _getPortal(context):
    return getToolByName(context, 'portal_url').getPortalObject()

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

#order folder tabs in logical order
def orderFolderTabs(context):
    portal = _getPortal(context)

    #Expose the correct folder tabs
    registry = getUtility(IRegistry)
    navigation_settings = registry.forInterface(INavigationSchema, prefix='plone')
    navigation_settings.displayed_types = ('Folder', 'jpl.mcl.site.knowledge.groupfolder', 'jpl.mcl.site.knowledge.participatingsitefolder', 'jpl.mcl.site.sciencedata.sciencedatafolder')

    # Members < Working Groups < Resources < News & Meetings < Science Data
    idx = 1
    for i in ('members', 'working-groups-new', 'resources', 'news-meetings', 'science-data'):
        portal.moveObject(i, idx)
        idx += 1
    ploneUtils = getToolByName(portal, 'plone_utils')
    ploneUtils.reindexOnReorder(portal)
