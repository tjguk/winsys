from winsys import dialogs, security

[filename] = dialogs.dialog ("Choose file", ("Filename", ""))
security.security (filename).dump ()
