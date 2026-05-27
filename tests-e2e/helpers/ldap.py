"""
LDAP helpers for OpenLDAP operations.
"""

from ldap3 import ALL, ALL_ATTRIBUTES, MODIFY_REPLACE, Connection, Server


class LDAPManager:
    def __init__(self, url, bind_dn, bind_password, base_dn):
        self.url = url
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.base_dn = base_dn

    def _connect(self):
        server = Server(self.url, get_info=ALL)
        conn = Connection(server, self.bind_dn, self.bind_password, auto_bind=True)
        return conn

    def create_group(self, cn, ou=None):
        """Create a posixGroup entry."""
        conn = self._connect()
        dn = f"cn={cn},{ou or self.base_dn}"
        if self._entry_exists(conn, dn):
            conn.unbind()
            return dn

        attrs = {
            "objectClass": ["posixGroup", "top"],
            "cn": cn,
            "gidNumber": str(10000 + hash(cn) % 90000),
        }
        conn.add(dn, attributes=attrs)
        if conn.result["result"] != 0:
            raise RuntimeError(f"Failed to create group {dn}: {conn.result}")
        conn.unbind()
        return dn

    def create_user(self, cn, sn, uid=None, ou=None, password=None):
        """Create an inetOrgPerson entry."""
        conn = self._connect()
        uid = uid or cn
        dn = f"cn={cn},{ou or self.base_dn}"
        if self._entry_exists(conn, dn):
            conn.unbind()
            return dn

        attrs = {
            "objectClass": ["inetOrgPerson", "posixAccount", "top"],
            "cn": cn,
            "sn": sn,
            "uid": uid,
            "uidNumber": str(10000 + hash(cn) % 90000),
            "gidNumber": "500",
            "homeDirectory": f"/home/{uid}",
        }
        if password:
            attrs["userPassword"] = password

        conn.add(dn, attributes=attrs)
        if conn.result["result"] != 0:
            raise RuntimeError(f"Failed to create user {dn}: {conn.result}")
        conn.unbind()
        return dn

    def add_user_to_group(self, user_cn, group_cn, ou=None):
        """Add a user to a posixGroup by modifying the group's memberUid."""
        conn = self._connect()
        group_dn = f"cn={group_cn},{ou or self.base_dn}"
        conn.modify(group_dn, {"memberUid": [(MODIFY_REPLACE, [user_cn])]})
        conn.unbind()

    def get_users(self, ou=None):
        conn = self._connect()
        conn.search(
            self.base_dn, "(objectClass=inetOrgPerson)", attributes=ALL_ATTRIBUTES
        )
        users = [entry.entry_attributes_as_dict for entry in conn.entries]
        conn.unbind()
        return users

    def modify_user(self, cn, attributes, ou=None):
        conn = self._connect()
        dn = f"cn={cn},{ou or self.base_dn}"
        changes = {}
        for attr_name, value in attributes.items():
            if isinstance(value, list):
                changes[attr_name] = [(MODIFY_REPLACE, value)]
            else:
                changes[attr_name] = [(MODIFY_REPLACE, [value])]
        conn.modify(dn, changes)
        conn.unbind()

    def _entry_exists(self, conn, dn):
        return conn.search(dn, "(objectClass=*)", size_limit=1)

    def close(self):
        pass
