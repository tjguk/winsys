from winsys import dialogs, security

[filename] = dialogs.dialog ("Choose file", ("Filename", ""))
security.Security.read (filename).dump ()
raw_input ("Press enter")
