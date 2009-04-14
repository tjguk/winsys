from winsys import dialogs, registry

root, term = dialogs.dialog (
  "Search the Registry",
  ("Root", registry.REGISTRY_HIVE.keys ()),
  ("Term", "")
)

root = registry.registry (root)
term = term.lower ()
for key, subkeys, values in root.walk (ignore_access_errors=True):
  for name, value, type in values:
    if term in str (value).lower ():
      print key.moniker.encode ("utf8")
      print name.encode ("utf8") or "(Default)"
      print unicode (value).encode ("utf8")
      print
