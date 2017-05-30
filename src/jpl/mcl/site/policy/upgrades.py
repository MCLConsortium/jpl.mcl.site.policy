# encoding: utf-8

u'''MCL — custom upgrade steps.'''


from plone.app.ldap.engine.interfaces import ILDAPConfiguration
from plone.app.ldap.engine.schema import LDAPProperty
from plone.app.ldap.ploneldap.util import guaranteePluginExists
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import INavigationSchema
from Products.PluggableAuthService.interfaces.plugins import (
    IAuthenticationPlugin, IPropertiesPlugin, IUserAdderPlugin, IUserEnumerationPlugin, IRolesPlugin,
    IRoleEnumerationPlugin, IGroupsPlugin, IGroupEnumerationPlugin, ICredentialsResetPlugin
)
from Products.PlonePAS.interfaces.plugins import IUserManagement
from Products.PlonePAS.interfaces.group import IGroupManagement, IGroupIntrospection
from zope.component import getUtility
import plone.api, socket, logging, os


_logger = logging.getLogger(__name__)


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


def installJPLMCLSiteKnowledge(context):
    u'''Install jpl.mcl.site.knowledge.'''
    qi = plone.api.portal.get_tool('portal_quickinstaller')
    qi.installProduct('jpl.mcl.site.knowledge')


def installJPLMCLSiteSciencedata(context):
    u'''Install jpl.mcl.site.sciencedata.'''
    qi = plone.api.portal.get_tool('portal_quickinstaller')
    qi.installProduct('jpl.mcl.site.sciencedata')


def orderFolderTabs(context):
    u'''order folder tabs in logical order'''
    portal = _getPortal(context)

    # Expose the correct folder tabs
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


def _setPluginOrder(plugins, interface, desiredOrder):
    _logger.debug('Setting plugin order for %r to %r', interface, desiredOrder)
    current = plugins[interface]
    toOrder = []
    for i in desiredOrder:
        if i in current:
            toOrder.append(i)
    plugins[interface] = tuple(toOrder)


def installLDAP(context):
    _logger.warn('Deleting local site users')
    membership = plone.api.portal.get_tool('portal_membership')
    membership.deleteMembers(membership.listMemberIds())
    _logger.debug('Installling plone.app.ldap')
    qi = plone.api.portal.get_tool('portal_quickinstaller')
    qi.installProduct('plone.app.ldap')
    _logger.debug('Deleting any existing LDAP plugins')
    portal = _getPortal(context)
    acl_users = getattr(portal, 'acl_users')
    ids = [o.id for o in [acl_users[i] for i in acl_users.objectIds()] if o.meta_type == 'Plone LDAP plugin']
    if ids: acl_users.manage_delObjects(ids)
    ldapConfig = getUtility(ILDAPConfiguration)
    _logger.debug('Setting up labels for existing schemata')
    p = ldapConfig.schema['uid']
    p.ldap_name, p.plone_name, p.description, p.multi_valued = 'uid', '', u'User ID', False
    p = ldapConfig.schema['mail']
    p.ldap_name, p.plone_name, p.description, p.multi_valued = 'mail', 'email', u'Email Address', False
    p = ldapConfig.schema['cn']
    p.ldap_name, p.plone_name, p.description, p.multi_valued = 'cn', 'fullname', u'Full Name', False
    p = ldapConfig.schema['sn']
    p.ldap_name, p.plone_name, p.description, p.multi_valued = 'sn', '', u'Surname', False
    _logger.debug('Adding mapping for "description" schema')
    ldapConfig.schema['description'] = LDAPProperty('description', 'description', u'Description', False)
    _logger.debug('Setting up basic LDAP attributes')
    ldapConfig.userid_attribute    = 'uid'
    ldapConfig.user_object_classes = 'inetOrgPerson'
    ldapConfig.password_encryption = 'SSHA'
    ldapConfig.ldap_type           = u'LDAP'
    ldapConfig.user_scope          = 1  # one level
    ldapConfig.user_base           = 'ou=users,o=MCL'
    ldapConfig.rdn_attribute       = 'uid'
    ldapConfig.login_attribute     = 'uid'
    ldapConfig.group_scope         = 1  # one level
    ldapConfig.group_base          = 'ou=groups,o=MCL'
    ldapConfig.bind_dn             = 'uid=admin,ou=system'
    password = os.getenv('LDAP_PASSWORD')
    if password is not None:
        ldapConfig.bind_password = password
    else:
        _logger.critical('Leaving LDAP admin password blank because the LDAP_PASSWORD envvar is un-set')
    guaranteePluginExists()
    host, port = os.getenv('LDAP_HOST', 'edrn.jpl.nasa.gov'), os.getenv('LDAP_PORT', '636')
    secure = int(os.getenv('LDAP_SECURE', '1'))
    _logger.debug('Adding LDAP server')
    inner = portal.acl_users['ldap-plugin'].acl_users
    inner.manage_addServer(host, port, use_ssl=secure, conn_timeout=5, op_timeout=30)
    inner.manage_addGroupMapping('Super User', 'Manager')
    _logger.debug('Re-ordering PAS plugins')
    plugins = acl_users.plugins._plugins
    _setPluginOrder(plugins, IAuthenticationPlugin, ('ldap-plugin', 'source_users', 'session'))
    _setPluginOrder(plugins, ICredentialsResetPlugin, ('ldap-plugin', 'session'))
    _setPluginOrder(plugins, IGroupEnumerationPlugin, ('ldap-plugin', 'source_groups', 'auto_group'))
    _setPluginOrder(plugins, IGroupIntrospection, ('ldap-plugin', 'source_groups', 'auto_group'))
    _setPluginOrder(plugins, IGroupManagement, ('ldap-plugin', 'source_groups'))
    _setPluginOrder(plugins, IGroupsPlugin, ('ldap-plugin', 'source_groups', 'auto_group', 'recursive_groups'))
    _setPluginOrder(plugins, IPropertiesPlugin, ('ldap-plugin', 'mutable_properties'))
    _setPluginOrder(plugins, IRoleEnumerationPlugin, ('ldap-plugin', 'portal_role_manager'))
    _setPluginOrder(plugins, IRolesPlugin, ('ldap-plugin', 'portal_role_manager'))
    _setPluginOrder(plugins, IUserAdderPlugin, ('ldap-plugin', 'source_users'))
    _setPluginOrder(plugins, IUserEnumerationPlugin, ('ldap-plugin', 'source_users', 'mutable_properties'))
    _setPluginOrder(plugins, IUserManagement, ('ldap-plugun', 'source_users'))
